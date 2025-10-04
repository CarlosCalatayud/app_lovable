import logging
from typing import Dict, Any, Optional

def _to_float(x) -> Optional[float]:
    try:
        if x is None or x == "":
            return None
        s = str(x).strip().replace(",", ".")
        return float(s)
    except Exception:
        return None

def calculate_structural_data(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcula superficieConstruidaM2, pesoEstructuraKg (paneles + estructura) y
    densidades (kg/m2 y kN/m2) de forma tolerante a None/cadenas.
    """
    calculated: Dict[str, Any] = {}

    # nº paneles
    n_pan = _to_float(ctx.get("numero_paneles")) or 0.0
    n_pan = int(n_pan) if n_pan > 0 else 0

    # fuente de datos de panel: ctx['paneles'][0] o campos planos
    p0 = (ctx.get("paneles") or [{}])[0] or {}
    largo_mm  = _to_float(p0.get("largo_mm")  or ctx.get("largo_mm"))    or 0.0
    ancho_mm  = _to_float(p0.get("ancho_mm")  or ctx.get("ancho_mm"))    or 0.0
    peso_kg   = _to_float(p0.get("peso_kg")   or ctx.get("peso_kg"))     or 0.0
    ppk_w     = _to_float(p0.get("potencia_pico_w") or ctx.get("potencia_pico_w")) or 0.0

    logging.info("--- INICIO CÁLCULOS ESTRUCTURALES ---")
    logging.info("Entrada: n_paneles=%s, largo_mm=%s, ancho_mm=%s, peso_panel_kg=%s, ppk_w=%s",
                 n_pan, largo_mm, ancho_mm, peso_kg, ppk_w)

    # Superficie total (m2)
    superficieConstruidaM2 = 0.0
    if n_pan > 0 and largo_mm > 0 and ancho_mm > 0:
        superficie_panel_m2 = (largo_mm / 1000.0) * (ancho_mm / 1000.0)
        superficieConstruidaM2 = round(n_pan * superficie_panel_m2, 2)
    calculated["superficieConstruidaM2"] = superficieConstruidaM2
    logging.info("Superficie: %s m^2", superficieConstruidaM2)

    # Peso total = paneles + estructura (2 kg/panel por defecto)
    extra_kg = _to_float(ctx.get("extra_kg_por_panel")) or 2.0
    peso_total_paneles = n_pan * peso_kg
    peso_total_estructura = n_pan * extra_kg
    pesoEstructuraKg = round(peso_total_paneles + peso_total_estructura, 2)
    calculated["pesoEstructuraKg"] = pesoEstructuraKg

    # Densidades
    densidadDeCarga = 0.0
    densidadDeCargaKNm2 = 0.0
    if superficieConstruidaM2 > 0:
        densidadDeCarga = round(pesoEstructuraKg / superficieConstruidaM2, 2)
        if densidadDeCarga > 0:
            densidadDeCargaKNm2 = round((densidadDeCarga * 9.807) / 1000.0, 2)

    calculated["densidadDeCarga"] = densidadDeCarga
    calculated["densidadDeCargaKNm2"] = densidadDeCargaKNm2 if densidadDeCargaKNm2 > 0 else ""

    logging.info("Carga: pesoEstructuraKg=%s kg, densidad=%s kg/m2, densidad_kNm2=%s kN/m2",
                 pesoEstructuraKg, densidadDeCarga, densidadDeCargaKNm2)
    logging.info("--- FIN CÁLCULOS ESTRUCTURALES ---")

    return calculated
