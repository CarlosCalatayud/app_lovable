from pydantic import BaseModel, Field, constr, condecimal
from typing import Optional
from datetime import date

# --- Aliases para tipos con restricciones ---
LocalidadType = constr(min_length=1, max_length=50)
ProvinciaType = constr(min_length=1, max_length=50)
CifNifType = constr(min_length=1, max_length=20)
NombreCortoType = constr(min_length=1, max_length=100)
NombreLargoType = constr(min_length=1, max_length=150)
ModeloType = constr(min_length=1, max_length=100)
ViaType = Optional[str]  # usando Field para validar longitud
CodigoPostalType = Optional[str]

DecimalPositivo2 = condecimal(decimal_places=2, gt=0)

ProtectorSobretensionesType = constr(min_length=1, max_length=20)
FasicoType = constr(pattern="^(Monofásico|Trifásico)$")
MaterialCableType = constr(pattern="^(Cobre|Aluminio)$")

# --- Modelos ---
class Emplazamiento(BaseModel):
    nombre_via: ViaType = Field(None, max_length=100)
    numero_via: ViaType = Field(None, max_length=10)
    piso_puerta: ViaType = Field(None, max_length=20)
    localidad: LocalidadType
    provincia: ProvinciaType
    codigo_postal: CodigoPostalType = Field(None, max_length=10)


class Promotor(BaseModel):
    nombre_razon_social: NombreLargoType
    cif_nif: CifNifType
    nombre_via: ViaType = Field(None, max_length=100)
    numero_via: ViaType = Field(None, max_length=10)
    piso_puerta: ViaType = Field(None, max_length=20)
    localidad: LocalidadType
    provincia: ProvinciaType
    codigo_postal: CodigoPostalType = Field(None, max_length=10)


class Instalador(BaseModel):
    nombre_empresa: NombreLargoType
    cif_nif: CifNifType
    nombre_completo_tecnico: NombreLargoType
    numero_colegiado_o_instalador: ViaType = Field(None, max_length=50)
    competencia: ViaType = Field(None, max_length=100)  # Ej: "electricista", "ingeniero"
    nombre_via: ViaType = Field(None, max_length=100)
    numero_via: ViaType = Field(None, max_length=10)
    piso_puerta: ViaType = Field(None, max_length=20)
    localidad: LocalidadType
    provincia: ProvinciaType
    codigo_postal: CodigoPostalType = Field(None, max_length=10)


class PanelSolar(BaseModel):
    fabricante: NombreCortoType
    modelo: ModeloType
    potencia_pico_w: int = Field(..., gt=0)
    largo_mm: int = Field(..., gt=0)
    ancho_mm: int = Field(..., gt=0)
    peso_kg: DecimalPositivo2
    corriente_maxima_funcionamiento_a: DecimalPositivo2
    tension_maximo_funcionamiento_v: DecimalPositivo2


class Inversor(BaseModel):
    fabricante: NombreCortoType
    modelo: ModeloType
    potencia_nominal_ac_w: int = Field(..., gt=0)
    corriente_maxima_salida_a: DecimalPositivo2
    monofasico_trifasico: FasicoType


class Bateria(BaseModel):
    nombre: NombreCortoType
    capacidad_kwh: DecimalPositivo2


class Hospital(BaseModel):
    nombre: NombreCortoType
    nombre_via: ViaType = Field(None, max_length=100)
    numero_via: ViaType = Field(None, max_length=10)
    piso_puerta: ViaType = Field(None, max_length=20)
    localidad: LocalidadType
    provincia: ProvinciaType
    codigo_postal: CodigoPostalType = Field(None, max_length=10)


class Protecciones(BaseModel):
    fusible_cc_a: int = Field(..., gt=0)
    protector_sobretensiones_v: ProtectorSobretensionesType  # Ej: "1000V"
    magnetotermico_ac_a: int = Field(..., gt=0)
    diferencial_a: int = Field(..., gt=0)
    sensibilidad_ma: int = Field(..., gt=0)


class Cableado(BaseModel):
    material_cable_dc: MaterialCableType
    seccion_cable_dc_mm2: DecimalPositivo2
    longitud_cable_dc_m: DecimalPositivo2
    longitud_cable_cc_string1: DecimalPositivo2  # Para el cálculo de caída de tensión

    material_cable_ac: MaterialCableType
    seccion_cable_ac_mm2: DecimalPositivo2
    longitud_cable_ac_m: DecimalPositivo2
    secciones_ca_recomendado_mm2: Optional[DecimalPositivo2] = None  # Para el cálculo de caída de tensión


class ProjectContext(BaseModel):
    """Modelo base para todos los datos de un proyecto."""
    id: str = Field(..., max_length=50)
    nombre_proyecto: NombreCortoType
    fecha_finalizacion: date
    provincia_proyecto: ProvinciaType

    emplazamiento: Emplazamiento
    promotor: Promotor
    instalador: Instalador

    # Lista de paneles si hay varios o simplemente uno
    paneles: list[PanelSolar] = Field(..., min_items=1)
    numero_paneles: int = Field(..., gt=0)  # Para compatibilidad con tu código actual

    inversor: Inversor
    bateria: Optional[Bateria] = None
    hospital_cercano: Optional[Hospital] = None
    protecciones: Protecciones
    cableado: Cableado

    # Campos que el usuario puede introducir y que se pasan directamente a la plantilla
    referencia_catastral: ViaType = Field(None, max_length=50)
    descripcion_adicional: Optional[str] = None
    # etc.

# --- Modelos específicos para cada documento ---
# Estos heredarán de ProjectContext y añadirán validaciones o campos específicos.
# Ejemplo: src/config/document_schemas/andalucia_doc_informe.py
# from ...generation.models import ProjectContext

# class AndaluciaDocInformeContext(ProjectContext):
#     # Quizás este documento requiere que la referencia catastral sea obligatoria
#     referencia_catastral: constr(min_length=1, max_length=50)
#     # O necesita un campo específico que no es general para ProjectContext
#     # tipo_cubierta: Literal["Plana", "Inclinada"]

# Ejemplo de cómo cargar estos dinámicamente:
# from importlib import import_module
# schema_module = import_module(f"src.config.document_schemas.{doc_definition['context_schema']}")
# SpecificDocContext = getattr(schema_module, "SpecificDocContextClassName")