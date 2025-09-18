import logging
from typing import Dict, Any

RHO_COBRE = 0.0172  # Ohm * mm^2 / m
RHO_ALUMINIO = 0.0282 # Ohm * mm^2 / m

def calculate_electrical_data(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Calcula caídas de tensión y datos de protecciones."""
    calculated_data = {}
    
    cableado = ctx.get('cableado', {})
    protecciones = ctx.get('protecciones', {})
    inversor = ctx.get('inversor', {})
    paneles_data = ctx.get('paneles', [{}])
    panel = paneles_data[0] if paneles_data else {}

    # Alias para campos directos de protecciones
    calculated_data['fusible_cc_a'] = protecciones.get('fusible_cc_a')
    calculated_data['protector_sobretensiones_v'] = protecciones.get('protector_sobretensiones_v')
    calculated_data['magnetotermico_a'] = protecciones.get('magnetotermico_ac_a')
    calculated_data['diferencialA'] = protecciones.get('diferencial_a')
    calculated_data['sensibilidadMa'] = protecciones.get('sensibilidad_ma')

    # Alias para campos directos de cableado
    calculated_data['cable_dc_material'] = cableado.get('material_cable_dc')
    calculated_data['cable_dc_seccion'] = cableado.get('seccion_cable_dc_mm2')
    calculated_data['cable_dc_longitud'] = cableado.get('longitud_cable_dc_m')
    calculated_data['cable_ac_material'] = cableado.get('material_cable_ac')
    calculated_data['cable_ac_seccion'] = cableado.get('seccion_cable_ac_mm2')
    calculated_data['cable_ac_longitud'] = cableado.get('longitud_cable_ac_m')

    # --- Cálculos de Caída de Tensión CC ---
    long_cc = cableado.get('longitud_cable_cc_string1', 0.0)
    seccion_cc = cableado.get('seccion_cable_dc_mm2', 0.0) # Usar la sección real del cable DC
    corriente_max_panel = panel.get('corriente_maxima_funcionamiento_a', 0.0)
    tension_max_panel = panel.get('tension_maximo_funcionamiento_v', 0.0)
    material_dc = cableado.get('material_cable_dc', 'Cobre')
    rho_dc = RHO_COBRE if material_dc == 'Cobre' else RHO_ALUMINIO

    caida_tension_cc = 0
    if seccion_cc > 0:
        caida_tension_cc = (2 * long_cc * rho_dc * corriente_max_panel) / seccion_cc
        if tension_max_panel > 0:
            calculated_data['caidaTensionCCString1'] = round((caida_tension_cc / tension_max_panel) * 100, 2)
        else:
            calculated_data['caidaTensionCCString1'] = 0
    else:
        calculated_data['caidaTensionCCString1'] = 0
        
    # --- Cálculos de Caída de Tensión CA ---
    long_ac = cableado.get('longitud_cable_ac_m', 0.0)
    seccion_ac = cableado.get('seccion_cable_ac_mm2', 0.0)
    corriente_max_inversor = inversor.get('corriente_maxima_salida_a', 0.0)
    material_ac = cableado.get('material_cable_ac', 'Cobre')
    rho_ac = RHO_COBRE if material_ac == 'Cobre' else RHO_ALUMINIO

    # Asumimos 230V para monofásico, 400V para trifásico.
    # Esto puede ser más complejo si hay diferentes configuraciones de red.
    tension_nominal_ac = 230
    if inversor.get('monofasico_trifasico') == 'Trifásico':
        tension_nominal_ac = 400 # Tensión de línea para trifásica

    caida_tension_ca = 0
    if seccion_ac > 0:
        # Para trifásica, el factor es sqrt(3), para monofásica 2
        factor = 2 
        if inversor.get('monofasico_trifasico') == 'Trifásico':
            factor = 1.732 # sqrt(3)
            
        caida_tension_ca = (factor * long_ac * rho_ac * corriente_max_inversor) / seccion_ac
        calculated_data['caidaTensionCA'] = round((caida_tension_ca / tension_nominal_ac) * 100, 2)
    else:
        calculated_data['caidaTensionCA'] = 0

    # Polos para protecciones
    tipo_conexion_inversor = inversor.get('monofasico_trifasico', 'Monofásico')
    calculated_data['polosCA'] = '4' if tipo_conexion_inversor == 'Trifásico' else '2'

    return calculated_data