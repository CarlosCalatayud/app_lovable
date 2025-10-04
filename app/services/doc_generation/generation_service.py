# app/services/doc_generation/generation_service.py
from __future__ import annotations

import io, os, re, json
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from flask import current_app

import yaml
from jinja2 import Environment, StrictUndefined
from docxtpl import DocxTemplate, InlineImage  # inline if someday needed
from datetime import datetime
from decimal import Decimal
from app.services.doc_generation.generation.calculators.structural_calculations import calculate_structural_data

import logging
LOGGER = logging.getLogger("docgen")
DOCGEN_DEBUG = os.getenv("DOCGEN_DEBUG", "").lower() in ("1", "true", "yes", "on")
DOCGEN_LOG_PII = os.getenv("DOCGEN_LOG_PII", "").lower() in ("1", "true", "yes", "on")


import  logging
# ============
# Utilidades
# ============

TEMPLATES_ROOT = Path(os.environ.get("TEMPLATES_ROOT", "app/services/doc_generation/templates")).resolve()
DOCS_INDEX_FILENAME = os.environ.get("DOCS_INDEX_FILENAME", "documents.yml")

# -------------------------
# Helpers de logging seguro
# -------------------------
_SUSPECT_KEYS = ("dni", "nif", "cif", "email", "correo", "telefono", "teléfono", "phone", "movil", "móvil", "address", "direccion", "dirección")
_EMAIL_RE = re.compile(r'([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})')
_DIGITS_RE = re.compile(r'\d')

def _mask_value(k: str, v: Any) -> Any:
    if DOCGEN_LOG_PII:
        return v
    key = (k or "").lower()
    if any(s in key for s in _SUSPECT_KEYS):
        s = str(v)
        if "email" in key or _EMAIL_RE.search(s):
            return _EMAIL_RE.sub(r'***@\2', s)
        # enmascara dígitos dejando últimos 2
        digits = _DIGITS_RE.findall(s)
        if len(digits) >= 4:
            return re.sub(r'\d', "*", s[:-2]) + s[-2:]
        return "***"
    return v

def _serialize(v: Any) -> Any:
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, bytes):
        return f"<bytes:{len(v)}>"
    return v

def _log_context(title: str, ctx: Dict[str, Any]):
    if not DOCGEN_DEBUG:
        return
    try:
        safe = {k: _serialize(_mask_value(k, v)) for k, v in (ctx or {}).items()}
        dump = json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2)
        LOGGER.info("DOCGEN %s\n%s", title, dump)
    except Exception as e:
        LOGGER.warning("DOCGEN no pudo volcar contexto (%s)", e)


def _safe_join(base: Path, *parts: str) -> Path:
    p = (base.joinpath(*parts)).resolve()
    if not str(p).startswith(str(base)):
        raise ValueError("Ruta de plantilla fuera de TEMPLATES_ROOT")
    return p

def _load_yaml(p: Path) -> dict:
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def _to_float(x: Any) -> Optional[float]:
    try:
        if x is None: return None
        if isinstance(x, (int, float)): return float(x)
        if isinstance(x, Decimal): return float(x)
        s = str(x).replace(",", ".").strip()
        return float(s)
    except Exception:
        return None

# ===================
# Modelo de documento
# ===================

@dataclass
class DocDef:
    id: str              # identificador interno (no usado por el frontend)
    filename: str        # nombre real del fichero de plantilla (usado como id en el front)
    name: str            # nombre descriptivo
    description: str     # texto opcional
    type: str            # 'docx' (futuro: 'xlsx', 'pdf')
    requires: List[str]  # claves requeridas
    optional: List[str]  # claves opcionales (rellenadas con "" si faltan)
    computed: Dict[str, str]  # reglas de cálculo (date:..., formula:...)


class DocIndex:
    def __init__(self, community_slug: str):
        self.community_slug = community_slug
        self.base_dir = _safe_join(TEMPLATES_ROOT, community_slug)
        self.index_path = _safe_join(self.base_dir, DOCS_INDEX_FILENAME)
        self.docs: Dict[str, DocDef] = {}
        self._load()

    def _load(self):
        data = _load_yaml(self.index_path)
        docs = data.get("documents", [])
        for d in docs:
            doc = DocDef(
                id=d.get("id") or d.get("filename"),
                filename=d["filename"],
                name=d.get("name", d["filename"]),
                description=d.get("description", ""),
                type=d.get("type", "docx"),
                requires=d.get("requires", []),
                optional=d.get("optional", []),
                computed=d.get("computed", {}),
            )
            self.docs[doc.filename] = doc

    def list_available(self) -> List[Dict[str, str]]:
        # IMPORTANTE: 'id' debe ser el filename para que el front y tu backend coincidan
        return [
            {"id": d.filename, "name": d.name, "description": d.description}
            for d in self.docs.values()
        ]

    def get_doc(self, filename: str) -> DocDef:
        if filename not in self.docs:
            raise ValueError(f"Documento no declarado en {self.index_path.name}: {filename}")
        return self.docs[filename]

# =========================
# Motor de generación DOCX
# =========================

class _DocxEngine:
    def __init__(self):
        # StrictUndefined: si falta una variable en el contexto, se lanza excepción
        self.env = Environment(autoescape=False, undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)

    def render(self, tpl_path: Path, context: Dict[str, Any]) -> bytes:
        if DOCGEN_DEBUG:
            LOGGER.info("DOCGEN render: tpl_rel='%s' tpl_abs='%s' TEMPLATES_ROOT='%s' ctx_keys=%d",
                        str(tpl_path.relative_to(TEMPLATES_ROOT)) if str(tpl_path).startswith(str(TEMPLATES_ROOT)) else str(tpl_path),
                        str(tpl_path), str(TEMPLATES_ROOT), len(context or {}))

        doc = DocxTemplate(str(tpl_path))
        # Si algún valor es Decimal, conviene serializar a str/float
        normalized = {}
        for k, v in context.items():
            if isinstance(v, Decimal):
                normalized[k] = float(v)
            else:
                normalized[k] = v
        doc.render(normalized, jinja_env=self.env)
        buff = io.BytesIO()
        doc.save(buff)
        return buff.getvalue()

# =========================
# Servicio principal (API)
# =========================

class DocGeneratorService:

    def __init__(self):
        self.docx_engine = _DocxEngine()

    # ---- API visible desde tus rutas (mantén la firma) ----

    def get_available_docs_for_community(self, community_slug: str) -> List[Dict[str, str]]:

        idx = DocIndex(community_slug)
        if DOCGEN_DEBUG:
            LOGGER.info("DOCGEN list_available: community='%s' base='%s' index='%s' docs=%d",
                        community_slug, idx.base_dir, idx.index_path, len(idx.docs))
        return idx.list_available()

    def prepare_document_context(self, contexto_base: Dict[str, Any], community_province: str, selected_template_filename: str) -> Dict[str, Any]:
        """
        Lee el índice YAML de la comunidad, encuentra el doc de filename 'selected_template_filename',
        valida 'requires', calcula 'computed' y devuelve un contexto listo para render.
        """
        # El YAML se busca con la comunidad que llega en la API (community_slug en la ruta),
        # no con la provincia en minúsculas. La provincia la conservamos por si quieres reglas regionales.
        # Como esta función la llamas con el nombre del primer doc, obtenemos la comunidad a partir del propio path.
        # En nuestro caso, core_routes ya construye templates_base_path con community_slug y luego pasa el filename.
        # Aquí sólo validamos contra el índice de esa comunidad la próxima vez que llamen generate_document.
        # Por compatibilidad, no resolvemos el slug aquí: validaremos campos contra *todos* posibles docs
        # y dejaremos la comprobación final a generate_document. Aun así, haremos un intento con 'madrid' si existe.
        # Para robustez, si hay variable de entorno DEFAULT_COMMUNITY, úsala como fallback.
        default_slug = os.environ.get("DEFAULT_COMMUNITY", "madrid")
        if DOCGEN_DEBUG:
            LOGGER.info("DOCGEN prepare: default_slug='%s' province='%s' selected_tpl='%s' TEMPLATES_ROOT='%s'",
                        default_slug, community_province, selected_template_filename, str(TEMPLATES_ROOT))
            _log_context("contexto_base (in)", contexto_base)
        try:
            idx = DocIndex(default_slug)
            # Si existe el doc pedido en ese índice, úsalo. Si no, igualmente validaremos después al generar.
            docdef = idx.docs.get(selected_template_filename, None)
        except Exception:
            docdef = None

        # Base
        ctx = dict(contexto_base or {})
        # ===== CÁLCULOS ESTRUCTURALES INTEGRADOS =====
        try:
            # Construye un 'panel' sintético si no vino ctx['paneles']
            if not ctx.get('paneles'):
                synthetic_panel = {
                    'potencia_pico_w': ctx.get('potencia_pico_w', 0),
                    'largo_mm': ctx.get('largo_mm', 0),
                    'ancho_mm': ctx.get('ancho_mm', 0),
                    'peso_kg': ctx.get('peso_kg', 0.0),
                }
                ctx['paneles'] = [synthetic_panel]

            # Calcula
            struct_calc = calculate_structural_data(ctx)  # {'superficieConstruidaM2', 'densidadDeCarga', 'densidadDeCargaKNm2'}

            # Fusión con prioridad controlada por env var
            def _should_overwrite(k, v):
                cur = ctx.get(k)
                # Considera vacío: None, "", 0, "0"
                return (cur is None) or (cur == "") or (cur == 0) or (cur == "0")

            for k, v in struct_calc.items():
                if _should_overwrite(k, v):
                    ctx[k] = v

            logging.getLogger("docgen").info(
                "DOCGEN struct_calc merged: %s",
                {k: ctx.get(k) for k in ('superficieConstruidaM2', 'densidadDeCarga', 'densidadDeCargaKNm2')}
            )
        except Exception as e:
            logging.getLogger("docgen").warning("DOCGEN cálculo estructural falló: %s", e)

        # ---------- Cálculos genéricos (siempre disponibles) ----------
        now = datetime.now()
        ctx.setdefault("dia_actual", f"{now.day:02d}")
        # Mes en español
        meses_es = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]
        ctx.setdefault("mes_actual", meses_es[now.month - 1].capitalize())
        ctx.setdefault("anio_actual", str(now.year))
        ctx.setdefault("fechaCreacion", now.strftime("%d/%m/%Y"))

        # Densidad de carga si hay datos
        peso = _to_float(ctx.get("pesoEstructuraKg"))
        sup = _to_float(ctx.get("superficieConstruidaM2"))
        if ctx.get("densidadDeCarga") in (None, "", "0") and peso and sup and sup > 0:
            dens = peso / sup
            ctx["densidadDeCarga"] = f"{dens:.2f}"

        current_app.logger.info("DOCGEN densidadDeCarga=%s (peso=%s, sup=%s)", ctx.get("densidadDeCarga"), peso, sup)

        # Homogeneización de algunas claves (alias frecuentes)
        # p.ej., longitudes con distinto nombre en diferentes tablas
        current_app.logger.info("DOCGEN alias longitudCableAcM <- cable_ac_longitud if aplica")

        if ctx.get("longitudCableAcM") is None and ctx.get("cable_ac_longitud") is not None:
            ctx["longitudCableAcM"] = ctx["cable_ac_longitud"]
        

        # Si tenemos definición de doc, validamos campos requeridos declarados en YAML
        if docdef:
            LOGGER.info("DOCGEN docdef: requires=%s optional=%s computed=%s",
                            docdef.requires, docdef.optional, list((docdef.computed or {}).keys()))

            missing = []
            for k in docdef.requires:
                v = ctx.get(k, None)
                if v is None or (isinstance(v, str) and v.strip() == ""):
                    missing.append(k)
            if missing:
                raise ValueError(
                    "Faltan datos requeridos para completar el documento: "
                    + ", ".join(missing)
                )
            # Rellena opcionales con vacío si faltan
            for k in docdef.optional:
                if ctx.get(k) is None:
                    ctx[k] = ""

            # Calculados específicos declarados
            for key, rule in (docdef.computed or {}).items():
                if rule.startswith("date:"):
                    fmt = rule.removeprefix("date:")
                    if fmt == "day":
                        ctx[key] = f"{now.day:02d}"
                    elif fmt == "month_name_es":
                        ctx[key] = meses_es[now.month - 1].capitalize()
                    elif fmt == "year":
                        ctx[key] = str(now.year)
                    else:
                        # formato strftime
                        ctx[key] = now.strftime(fmt)
                elif rule.startswith("formula:"):
                    expr = rule.removeprefix("formula:")
                    # fórmula muy simple, solo soportamos division a/b
                    if "/" in expr:
                        a, b = [s.strip() for s in expr.split("/", 1)]
                        av, bv = _to_float(ctx.get(a)), _to_float(ctx.get(b))
                        if av is not None and bv not in (None, 0):
                            ctx[key] = f"{(av/bv):.2f}"

        # Devolvemos el contexto final: core_routes lo reutiliza para todos los docs seleccionados
        _log_context("contexto_final (out)", ctx)
        return ctx

    def generate_document(self, template_path: str, context: Dict[str, Any]) -> bytes:
        """
        Renderiza una plantilla DOCX con docxtpl y devuelve bytes del archivo resultante.
        """
        # Validación de ruta segura (dentro de TEMPLATES_ROOT)
        p = _safe_join(TEMPLATES_ROOT, template_path)
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"Plantilla no encontrada: {p}")

        # Solo admitimos .docx en este servicio inicial
        if p.suffix.lower() != ".docx":
            raise ValueError("Tipo de plantilla no soportado (sólo .docx)")

        try:
            if DOCGEN_DEBUG:
                LOGGER.info("DOCGEN generate_document: rel='%s' abs='%s' size_ctx=%d",
                            template_path, str(p), len(context or {}))
            return self.docx_engine.render(p, context)
        except Exception as e:
            # Mejoramos el mensaje si era por variable ausente
            msg = str(e)
            if "is undefined" in msg or "UndefinedError" in msg:
                raise ValueError(f"Faltan variables en el contexto para la plantilla: {msg}")
            raise

# instancia global esperada por tus rutas
doc_generator_service = DocGeneratorService()
