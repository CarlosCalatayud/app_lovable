import datetime
import logging
from typing import Dict, Any

def _fmt_dir(nombre_via, numero_via, piso_puerta, localidad, provincia) -> str:
    dir_parts = [nombre_via or '', numero_via or '', piso_puerta or '']
    direccion_str = ' '.join(filter(None, dir_parts)).strip()
    if direccion_str and localidad:
        return f"{direccion_str}, {localidad} ({provincia or ''})".strip()
    if localidad:
        return f"{localidad} ({provincia or ''})".strip()
    return provincia or "No especificada"


def calculate_format_addresses(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Formatea direcciones completas para emplazamiento, promotor e instalador."""
    logging.debug(f"........[format_addresses] Calculando direcciones con contexto: {ctx}")
    calculated_data = {}

    # Formato de Fecha Actual
    hoy = datetime.date.today()
    calculated_data['dia_actual'] = hoy.strftime('%d')
    calculated_data['mes_actual'] = hoy.strftime('%m')
    calculated_data['anio_actual'] = hoy.strftime('%Y')

    # Formato de Fecha de Finalización
    fecha_fin_str = ctx.get('fecha_finalizacion') # Asumimos que ya es un datetime.date de Pydantic
    fecha_fin = fecha_fin_str if isinstance(fecha_fin_str, datetime.date) else datetime.date.today()
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    calculated_data['fecha_finalizacion_formateada'] = f"{fecha_fin.day} de {meses[fecha_fin.month - 1]} de {fecha_fin.year}"

    # Emplazamiento
    emplazamiento = ctx.get('emplazamiento', {})
    dir_parts = [
        emplazamiento.get('nombre_via', ''),
        emplazamiento.get('numero_via', ''),
        emplazamiento.get('piso_puerta', '')
    ]
    direccion_str = ' '.join(filter(None, dir_parts)).strip()
    localidad = emplazamiento.get('localidad', '')
    provincia = emplazamiento.get('provincia', '')
    if direccion_str and localidad:
        calculated_data['direccion_emplazamiento_completa'] = f"{direccion_str}, {localidad} ({provincia})"
    elif localidad:
        calculated_data['direccion_emplazamiento_completa'] = f"{localidad} ({provincia})"
    else:
        calculated_data['direccion_emplazamiento_completa'] = provincia or "No especificada"

    # Promotor
    promotor = ctx.get('promotor', {})
    dir_prom_parts = [promotor.get('nombre_via', ''), promotor.get('numero_via', ''), promotor.get('piso_puerta', '')]
    dir_prom_str = ' '.join(filter(None, dir_prom_parts)).strip()
    loc_prom = promotor.get('localidad', '')
    prov_prom = promotor.get('provincia', '')
    if dir_prom_str and loc_prom:
        calculated_data['promotor_direccion_completa'] = f"{dir_prom_str}, {loc_prom} ({prov_prom})"
    else:
        calculated_data['promotor_direccion_completa'] = "No especificada"

    # Instalador
    instalador = ctx.get('instalador', {})
    dir_inst_parts = [instalador.get('nombre_via', ''), instalador.get('numero_via', ''), instalador.get('piso_puerta', '')]
    dir_inst_str = ' '.join(filter(None, dir_inst_parts)).strip()
    loc_inst = instalador.get('localidad', '')
    prov_inst = instalador.get('provincia', '')
    if dir_inst_str and loc_inst:
        calculated_data['instalador_direccion_completa'] = f"{dir_inst_str}, {loc_inst} ({prov_inst})"
    elif loc_inst:
        calculated_data['instalador_direccion_completa'] = f"{loc_inst} ({prov_inst})"
    else:
        calculated_data['instalador_direccion_completa'] = "No especificada"
    
    # Datos de técnico instalador
    calculated_data['instalador_tecnico_nombre'] = instalador.get('nombre_completo_tecnico', 'Técnico no especificado')
    calculated_data['instalador_tecnico_dni'] = instalador.get('cif_nif', 'DNI no especificado') # Asumo que es el DNI/CIF de la empresa o técnico
    calculated_data['instalador_tecnico_competencia'] = instalador.get('competencia', '')
    calculated_data['instalador_cif_empresa'] = instalador.get('cif_nif', '')
    calculated_data['instalador_numero_colegiado'] = instalador.get('numero_colegiado_o_instalador', '')

    # Hospital Cercano
    hospital = ctx.get('hospital_cercano')
    if hospital:
        dir_hosp_parts = [
            hospital.get('nombre_via', ''),
            hospital.get('numero_via', ''),
            hospital.get('piso_puerta', '')
        ]
        dir_hosp_str = ' '.join(filter(None, dir_hosp_parts)).strip()
        loc_hosp = hospital.get('localidad', '')
        prov_hosp = hospital.get('provincia', '')
        
        if dir_hosp_str and loc_hosp:
            calculated_data['hospital_direccion_completa'] = f"{dir_hosp_str}, {loc_hosp} ({prov_hosp})"
        elif loc_hosp:
             calculated_data['hospital_direccion_completa'] = f"{loc_hosp} ({prov_hosp})"
        else:
            calculated_data['hospital_direccion_completa'] = prov_hosp or "Dirección no especificada"
    else:
        calculated_data['hospital_direccion_completa'] = "No aplicable"

    # Textos Descriptivos
    bateria = ctx.get('bateria')
    calculated_data['textoBaterias'] = "La instalación dispone de sistema de acumulación." if bateria else "La instalación no dispone de sistema de acumulación."
    calculated_data['textoDisposiciónModulos'] = "La instalación fotovoltaica está compuesta por un único string." # Asumo por defecto

    return calculated_data

def calculate_pvgis_production(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Calcula la producción estimada (placeholder para PVGIS)."""
    logging.debug(f"........[calculate_pvgis_production] Calculando direcciones con contexto: {ctx}")

    calculated_data = {}
    total_panels = ctx.get('numero_paneles', 0)
    if total_panels > 0 and ctx.get('paneles') and len(ctx['paneles']) > 0:
        potencia_pico_panel = ctx['paneles'][0].get('potencia_pico_w', 0)
        potencia_pico_total_w = total_panels * potencia_pico_panel
    else:
        potencia_pico_total_w = 0

    calculated_data['potenciaPicoW'] = potencia_pico_total_w
    
    # Placeholder: En una implementación real, esto llamaría a la API de PVGIS
    # o usaría datos precalculados por provincia/localidad/orientación.
    calculated_data['Enero'] = round(potencia_pico_total_w * 0.06, 2)
    calculated_data['Febrero'] = round(potencia_pico_total_w * 0.07, 2)
    calculated_data['Marzo'] = round(potencia_pico_total_w * 0.10, 2)
    calculated_data['Abril'] = round(potencia_pico_total_w * 0.12, 2)
    calculated_data['Mayo'] = round(potencia_pico_total_w * 0.14, 2)
    calculated_data['Junio'] = round(potencia_pico_total_w * 0.15, 2)
    calculated_data['Julio'] = round(potencia_pico_total_w * 0.16, 2)
    calculated_data['Agosto'] = round(potencia_pico_total_w * 0.15, 2)
    calculated_data['Septiembre'] = round(potencia_pico_total_w * 0.11, 2)
    calculated_data['Octubre'] = round(potencia_pico_total_w * 0.09, 2)
    calculated_data['Noviembre'] = round(potencia_pico_total_w * 0.07, 2)
    calculated_data['Diciembre'] = round(potencia_pico_total_w * 0.05, 2)
    
    produccion_anual_total = sum(calculated_data[mes] for mes in ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'])
    calculated_data['produccionAnual'] = round(produccion_anual_total, 2)

    return calculated_data