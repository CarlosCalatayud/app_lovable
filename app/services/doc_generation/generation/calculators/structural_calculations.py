import logging
from typing import Dict, Any

def calculate_structural_data(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Calcula la superficie y densidad de carga de la instalación."""
    calculated_data = {}
    
    cantidad_paneles = ctx.get('numero_paneles', 0)
    paneles_data = ctx.get('paneles', [{}])
    panel = paneles_data[0] if paneles_data else {} # Asumo que todos los paneles son iguales
    
    potencia_pico_panel = panel.get('potencia_pico_w', 0)
    largo_panel = panel.get('largo_mm', 0)
    ancho_panel = panel.get('ancho_mm', 0)
    peso_panel = panel.get('peso_kg', 0.0)

    logging.info(f"--- INICIO CÁLCULOS ESTRUCTURALES ---")
    logging.info(f"Datos de entrada: Cantidad Paneles={cantidad_paneles}, Largo Panel={largo_panel}mm, Ancho Panel={ancho_panel}mm, Peso Panel={peso_panel}kg")

    # Cálculo de Superficie
    superficieConstruidaM2 = 0
    if largo_panel > 0 and ancho_panel > 0:
        superficie_panel_m2 = (largo_panel / 1000) * (ancho_panel / 1000)
        superficieConstruidaM2 = round(cantidad_paneles * superficie_panel_m2, 2)
    calculated_data['superficieConstruidaM2'] = superficieConstruidaM2
    logging.info(f"Cálculo de Superficie: superficieConstruidaM2 = {superficieConstruidaM2} m^2")

    # Cálculo de Carga
    peso_total_paneles = cantidad_paneles * peso_panel
    peso_total_estructura = cantidad_paneles * 2 # Asumimos 2kg por panel por ahora
    pesoEstructuraKg = round(peso_total_paneles + peso_total_estructura, 2)
    
    densidadDeCarga = 0
    densidadDeCargaKNm2 = 0

    if superficieConstruidaM2 > 0:
        densidadDeCarga = round(pesoEstructuraKg / superficieConstruidaM2, 2)
        if densidadDeCarga > 0:
            densidadDeCargaKNm2 = round((densidadDeCarga * 9.807) / 1000, 2)
            
    calculated_data['densidadDeCarga'] = densidadDeCarga
    calculated_data['densidadDeCargaKNm2'] = densidadDeCargaKNm2 if densidadDeCargaKNm2 > 0 else ''

    logging.info(f"Cálculo de Carga: Peso Total={pesoEstructuraKg}kg, densidadDeCarga = {densidadDeCarga} kg/m^2, densidadDeCargaKNm2 = {densidadDeCargaKNm2} kN/m^2")
    logging.info(f"--- FIN CÁLCULOS ESTRUCTURALES ---")
    
    return calculated_data