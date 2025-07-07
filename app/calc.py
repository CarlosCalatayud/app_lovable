# app/calc.py
import datetime
import math

# --- Constantes de Texto ---
TEXTO_SIN_ACUMULACION = "La instalación no dispone de sistema de acumulación."
TEXTO_CON_ACUMULACION = "La instalación dispone de sistema de acumulación."
TEXTO_UN_STRING = "La instalación fotovoltaica está compuesta por un único string."
TEXTO_VARIOS_STRINGS = "La instalación fotovoltaica está compuesta por varios strings."
RHO_COBRE = 0.0172 # Ohm * mm^2 / m (Resistividad del cobre a 20°C)

def get_input(source_dict, key, default=None, data_type=str):
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

def calculate_all_derived_data(context, db_conn):
    """
    Calcula todos los campos derivados a partir del contexto aplanado.
    'context' es el diccionario que ya contiene los datos de la instalación,
    promotor, instalador, panel, inversor, etc.
    """
    # El diccionario 'context' ya es nuestra fuente de la verdad.
    # No necesitamos más llamadas a la base de datos desde aquí.
    
    calculated_data = {}

    # --- Cálculos basados en datos del Panel ---
    cantidad_paneles = get_input(context, 'numero_paneles', default=0, data_type=int)
    potencia_pico_panel = get_input(context, 'potencia_pico_w', default=0, data_type=int)
    largo_panel = get_input(context, 'largo_mm', default=0, data_type=int)
    ancho_panel = get_input(context, 'ancho_mm', default=0, data_type=int)
    peso_panel = get_input(context, 'peso_kg', default=0, data_type=float)

    calculated_data['cantidadTotalPaneles'] = cantidad_paneles
    
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
    nombre_bateria = get_input(context, 'bateria', default='')
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
    long_cc = get_input(context, 'longitud_cable_cc_string1', default=0, data_type=float)
    seccion_ca_rec = get_input(context, 'secciones_ca_recomendado_mm2', default=2.5, data_type=float)
    corriente_max_panel = get_input(context, 'corriente_maxima_funcionamiento_a', default=0, data_type=float)
    tension_max_panel = get_input(context, 'tension_maximo_funcionamiento_v', default=0, data_type=float)

    if seccion_ca_rec > 0:
        caida_tension_cc = ((2 * long_cc * RHO_COBRE * corriente_max_panel) / seccion_ca_rec)
        if tension_max_panel > 0:
            calculated_data['caidaTensionCCString1'] = round((caida_tension_cc / tension_max_panel) * 100, 2)
        else:
            calculated_data['caidaTensionCCString1'] = 0
    else:
        calculated_data['caidaTensionCCString1'] = 0
        
    long_ac = get_input(context, 'longitud_cable_ac_m', default=0, data_type=float)
    seccion_ac = get_input(context, 'seccion_cable_ac_mm2', default=0, data_type=float)
    corriente_max_inversor = get_input(context, 'corriente_maxima_salida_a', default=0, data_type=float)
    
    if seccion_ac > 0:
        # Asumimos 230V para monofásico. Esto debería ser más inteligente.
        caida_tension_ca = ((2 * long_ac * RHO_COBRE * corriente_max_inversor) / seccion_ac)
        calculated_data['caidaTensionCA'] = round((caida_tension_ca / 230) * 100, 2)
    else:
        calculated_data['caidaTensionCA'] = 0

    # Polos para protecciones
    tipo_conexion_inversor = get_input(context, 'monofasico_trifasico', default='Monofásico')
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

    return calculated_data