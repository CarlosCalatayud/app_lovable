# src/generation/doc_generator.py
from docxtpl import DocxTemplate
import os
import datetime # Puede que no sea necesario si la fecha ya está en el context_dict
# --- Constantes de Texto (movidas desde calc.py) ---
TEXTO_SIN_ACUMULACION = "La instalación no dispone de sistema de acumulación."
TEXTO_CON_ACUMULACION = "La instalación dispone de sistema de acumulación."
TEXTO_UN_STRING = "La instalación fotovoltaica está compuesta por un único string."
RHO_COBRE = 0.0172  # Ohm * mm^2 / m

# La nombramos con un guion bajo para indicar que es una función "privada" de este módulo.
def _get_input(source_dict, key, default=None, data_type=str):
    """
    Función de ayuda para obtener y convertir valores de un diccionario de forma segura.
    """
    val = source_dict.get(key)
    if val is None or (isinstance(val, str) and val.strip() == ''):
        return default
    try:
        if data_type == float:
            return float(str(val).replace(',', '.'))
        if data_type == int:
            return int(float(str(val).replace(',', '.')))
        return data_type(val)
    except (ValueError, TypeError):
        return default

def prepare_document_context(context: dict) -> dict:
    """
    Toma el contexto de datos de la instalación y añade todos los campos calculados
    necesarios para las plantillas de documentos.
    Esta función contiene toda la lógica del antiguo calc.py.
    """
    ctx = context.copy()
    calculated_data = {}

    # --- Cálculos basados en datos del Panel ---
    cantidad_paneles = _get_input(ctx, 'numero_paneles', 0, int)
    potencia_pico_panel = _get_input(ctx, 'potencia_pico_w', 0, int)
    largo_panel = _get_input(ctx, 'largo_mm', 0, int)
    ancho_panel = _get_input(ctx, 'ancho_mm', 0, int)
    peso_panel = _get_input(ctx, 'peso_kg', 0, float)

    potencia_pico_total_w = cantidad_paneles * potencia_pico_panel
    calculated_data['potenciaPicoW'] = potencia_pico_total_w
    
    if largo_panel > 0 and ancho_panel > 0:
        superficie_panel_m2 = (largo_panel / 1000) * (ancho_panel / 1000)
        calculated_data['superficieConstruidaM2'] = round(cantidad_paneles * superficie_panel_m2, 2)
    else:
        calculated_data['superficieConstruidaM2'] = 0

    # --- Cálculos de Peso y Carga ---
    # Asumimos un peso de estructura de 2 kg por panel como ejemplo.
    # Podrías añadir 'peso_estructura_panel' como un campo en el formulario.
    peso_total_paneles = cantidad_paneles * peso_panel
    peso_total_estructura = cantidad_paneles * 2 
    calculated_data['pesoEstructuraKg'] = round(peso_total_paneles + peso_total_estructura, 2)
    
    if calculated_data['superficieConstruidaM2'] > 0:
        calculated_data['densidadDeCarga'] = round(calculated_data['pesoEstructuraKg'] / calculated_data['superficieConstruidaM2'], 2)
    else:
        calculated_data['densidadDeCarga'] = 0

    # --- Textos Descriptivos ---
    nombre_bateria = _get_input(context, 'bateria', default='')
    if nombre_bateria and nombre_bateria.lower() != 'no hay almacenamiento':
        calculated_data['textoBaterias'] = TEXTO_CON_ACUMULACION
    else:
        calculated_data['textoBaterias'] = TEXTO_SIN_ACUMULACION

    # Ejemplo para disposición de módulos. Necesitarías un campo en el form para el número de strings.
    # numero_strings = get_input(context, 'numero_strings', default=1, data_type=int)
    # if numero_strings > 1:
    #     calculated_data['textoDisposiciónModulos'] = TEXTO_VARIOS_STRINGS
    # else:
    #     calculated_data['textoDisposiciónModulos'] = TEXTO_UN_STRING
    calculated_data['textoDisposiciónModulos'] = TEXTO_UN_STRING # Valor por defecto

    # --- Cálculos de Cableado y Protecciones ---
    long_cc = _get_input(context, 'longitud_cable_cc_string1', default=0, data_type=float)
    seccion_ca_rec = _get_input(context, 'secciones_ca_recomendado_mm2', default=2.5, data_type=float)
    corriente_max_panel = _get_input(context, 'corriente_maxima_funcionamiento_a', default=0, data_type=float)
    tension_max_panel = _get_input(context, 'tension_maximo_funcionamiento_v', default=0, data_type=float)

    if seccion_ca_rec > 0:
        caida_tension_cc = ((2 * long_cc * RHO_COBRE * corriente_max_panel) / seccion_ca_rec)
        if tension_max_panel > 0:
            calculated_data['caidaTensionCCString1'] = round((caida_tension_cc / tension_max_panel) * 100, 2)
        else:
            calculated_data['caidaTensionCCString1'] = 0
    else:
        calculated_data['caidaTensionCCString1'] = 0
        
    long_ac = _get_input(context, 'longitud_cable_ac_m', default=0, data_type=float)
    seccion_ac = _get_input(context, 'seccion_cable_ac_mm2', default=0, data_type=float)
    corriente_max_inversor = _get_input(context, 'corriente_maxima_salida_a', default=0, data_type=float)
    
    if seccion_ac > 0:
        # Asumimos 230V para monofásico. Esto debería ser más inteligente.
        caida_tension_ca = ((2 * long_ac * RHO_COBRE * corriente_max_inversor) / seccion_ac)
        calculated_data['caidaTensionCA'] = round((caida_tension_ca / 230) * 100, 2)
    else:
        calculated_data['caidaTensionCA'] = 0

    # Polos para protecciones
    tipo_conexion_inversor = _get_input(context, 'monofasico_trifasico', default='Monofásico')
    if tipo_conexion_inversor == 'Trifásico':
        calculated_data['polosCA'] = '4'
    else:
        calculated_data['polosCA'] = '2'

    # --- Producción Estimada (PVGIS) - Placeholder ---
    # Esto requeriría una llamada real a la API de PVGIS, lo cual es complejo.
    # Por ahora, usamos valores de ejemplo.
    calculated_data['Enero'] = round(potencia_pico_total_w * 0.06, 2)
    calculated_data['Febrero'] = round(potencia_pico_total_w * 0.07, 2)
    calculated_data['Marzo'] = round(potencia_pico_total_w * 0.1, 2)
    calculated_data['Abril'] = round(potencia_pico_total_w * 0.12, 2)
    calculated_data['Mayo'] = round(potencia_pico_total_w * 0.14, 2)
    calculated_data['Junio'] = round(potencia_pico_total_w * 0.15, 2)
    calculated_data['Julio'] = round(potencia_pico_total_w * 0.16, 2)
    calculated_data['Agosto'] = round(potencia_pico_total_w * 0.15, 2)
    calculated_data['Septiembre'] = round(potencia_pico_total_w * 0.11, 2)
    calculated_data['Octubre'] = round(potencia_pico_total_w * 0.09, 2)
    calculated_data['Noviembre'] = round(potencia_pico_total_w * 0.07, 2)
    calculated_data['Diciembre'] = round(potencia_pico_total_w * 0.05, 2)
    
    produccion_anual_total = sum([calculated_data[mes] for mes in ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']])
    calculated_data['produccionAnual'] = round(produccion_anual_total, 2)
    
    # Al final, fusionamos los datos calculados con el contexto original
    ctx.update(calculated_data)
    return ctx
