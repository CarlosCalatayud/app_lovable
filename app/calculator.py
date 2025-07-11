# app/calculator.py
# app/calculator.py

import math
from typing import Dict, Union, Literal

class ElectricalCalculator:
    """
    Una clase que encapsula varios cálculos eléctricos.
    """

    # --- CONSTANTES INTERNAS ---
    RESISTIVIDAD_COBRE = 0.0172  # Ω·mm²/m
    RESISTIVIDAD_ALUMINIO = 0.0282 # Ω·mm²/m
    AWG_TO_MM2_MAP = {
        '0000': 107.2, '4/0': 107.2,
        '000': 85.03, '3/0': 85.03,
        '00': 67.43, '2/0': 67.43,
        '0': 53.48, '1/0': 53.48,
        '1': 42.41, '2': 33.62, '3': 26.67, '4': 21.15,
        '5': 16.77, '6': 13.30, '7': 10.55, '8': 8.367,
        '9': 6.63, '10': 5.26, '11': 4.17, '12': 3.31,
        '13': 2.62, '14': 2.08, '15': 1.65, '16': 1.31,
        '17': 1.04, '18': 0.823, '19': 0.653, '20': 0.518
    }

    def _normalize_current(self, current: Dict[str, Union[float, str]]) -> float:
        """Normaliza la corriente a Amperios."""
        value = float(current['value'])
        unit = str(current['unit']).lower()
        if unit == 'a':
            return value
        elif unit == 'ma':
            return value / 1000
        else:
            raise ValueError(f"Unidad de corriente no válida: {current['unit']}")

    def _normalize_length(self, length: Dict[str, Union[float, str]]) -> float:
        """Normaliza la longitud a Metros."""
        value = float(length['value'])
        unit = str(length['unit']).lower()
        if unit == 'm':
            return value
        elif unit == 'ft':
            return value * 0.3048
        else:
            raise ValueError(f"Unidad de longitud no válida: {length['unit']}")
            
    def _normalize_cross_section(self, section: Dict[str, Union[float, str]]) -> float:
        """Normaliza la sección transversal a mm²."""
        value = section['value']
        unit = str(section['unit']).lower()
        if unit == 'mm²':
            return float(value)
        elif unit == 'awg':
            awg_key = str(value).upper()
            if awg_key in self.AWG_TO_MM2_MAP:
                return self.AWG_TO_MM2_MAP[awg_key]
            else:
                raise ValueError(f"Calibre AWG no soportado: {awg_key}")
        else:
            raise ValueError(f"Unidad de sección no válida: {section['unit']}")

    def _normalize_voltage(self, voltage: Dict[str, Union[float, str]]) -> float:
        """Normaliza la tensión a Voltios."""
        value = float(voltage['value'])
        unit = str(voltage['unit']).lower()
        if unit == 'v':
            return value
        elif unit == 'kv':
            return value * 1000
        else:
            raise ValueError(f"Unidad de tensión no válida: {voltage['unit']}")

    def calculate_voltage_drop(
        self,
        current: Dict[str, Union[float, str]],
        length: Dict[str, Union[float, str]],
        wire_cross_section: Dict[str, Union[float, str]],
        material: Literal['cobre', 'aluminio'],
        system_type: Literal['monofasico', 'trifasico'],
        source_voltage: Dict[str, Union[float, str]],
        power_factor: float = 1.0
    ) -> Dict[str, Dict[str, Union[float, str]]]:
        """
        Calcula la caída de tensión en un conductor.

        Args:
            current: Corriente que fluye por el conductor.
            length: Longitud unidireccional del conductor.
            wire_cross_section: Sección transversal del cable.
            material: Material del conductor ('cobre' o 'aluminio').
            system_type: Tipo de sistema ('monofasico' o 'trifasico').
            source_voltage: Tensión en la fuente.
            power_factor: Factor de potencia (cos φ), por defecto 1.0.

        Returns:
            Un diccionario con la caída de tensión en voltios y porcentaje,
            y la tensión final en la carga.
        
        Raises:
            ValueError: Si falta un parámetro obligatorio o un valor es inválido.
        """
        # --- 1. Validación y Normalización ---
        if not all([current, length, wire_cross_section, material, system_type, source_voltage]):
            raise ValueError("Faltan parámetros obligatorios.")

        I = self._normalize_current(current)
        L = self._normalize_length(length)
        S = self._normalize_cross_section(wire_cross_section)
        V_source = self._normalize_voltage(source_voltage)
        
        if S == 0:
            raise ValueError("La sección del cable no puede ser cero.")

        if material.lower() == 'cobre':
            rho = self.RESISTIVIDAD_COBRE
        elif material.lower() == 'aluminio':
            rho = self.RESISTIVIDAD_ALUMINIO
        else:
            raise ValueError(f"Material no válido: {material}")

        # --- 2. Cálculo ---
        voltage_drop_v = 0.0
        if system_type.lower() == 'monofasico':
            voltage_drop_v = (2 * L * rho * I) / S
        elif system_type.lower() == 'trifasico':
            import math # Importamos math solo si es necesario
            voltage_drop_v = (math.sqrt(3) * L * rho * I * power_factor) / S
        else:
            raise ValueError(f"Tipo de sistema no válido: {system_type}")
        
        # --- 3. Resultados Adicionales ---
        voltage_at_load_v = V_source - voltage_drop_v
        
        if V_source == 0:
            voltage_drop_pct = float('inf') # Evitar división por cero
        else:
            voltage_drop_pct = (voltage_drop_v / V_source) * 100
        
        # --- 4. Formateo de Salida ---
        return {
            "voltage_drop_volts": {
                "value": round(voltage_drop_v, 2),
                "unit": "V",
                "info": "Tensión total perdida a lo largo del conductor."
            },
            "voltage_drop_percent": {
                "value": round(voltage_drop_pct, 2),
                "unit": "%",
                "info": "Porcentaje de la tensión de origen que se pierde en el cable."
            },
            "voltage_at_load": {
                "value": round(voltage_at_load_v, 2),
                "unit": "V",
                "info": "Tensión efectiva que llega a la carga al final del conductor."
            }
        }
    
        # --- CÁLCULO 2: SECCIÓN DE CABLE (NUEVO) ---
    def calculate_wire_section(
        self,
        system_type: Literal['monofasico', 'trifasico'],
        voltage: float,
        power: float,
        cos_phi: float,
        length: float,
        max_voltage_drop_percent: float,
        material: Literal['cobre', 'aluminio']
    ) -> Dict:
        """
        Calcula la sección mínima de cable requerida.
        NOTA: Esto es un cálculo teórico. La sección final debe elegirse de valores comerciales
        y verificarse con la Intensidad Máxima Admisible (Iz).
        """
        if max_voltage_drop_percent <= 0:
            raise ValueError("El porcentaje de caída de tensión máxima debe ser mayor que cero.")
            
        max_voltage_drop_volts = voltage * (max_voltage_drop_percent / 100)
        
        if voltage <= 0:
            raise ValueError("La tensión debe ser mayor que cero.")
            
        if system_type == 'monofasico':
            current = power / (voltage * cos_phi)
            rho = self.RESISTIVIDAD_COBRE if material == 'cobre' else self.RESISTIVIDAD_ALUMINIO
            section_mm2 = (2 * length * rho * current) / max_voltage_drop_volts
        elif system_type == 'trifasico':
            current = power / (math.sqrt(3) * voltage * cos_phi)
            rho = self.RESISTIVIDAD_COBRE if material == 'cobre' else self.RESISTIVIDAD_ALUMINIO
            section_mm2 = (math.sqrt(3) * length * rho * current) / max_voltage_drop_volts
        else:
            raise ValueError("Tipo de sistema no válido.")

        # Aquí iría la lógica para encontrar la sección comercial superior
        # Por ahora, devolvemos el valor teórico.
        
        return {
            "required_section": {
                "value": round(section_mm2, 2),
                "unit": "mm²",
                "info": "Sección teórica mínima requerida para cumplir con la caída de tensión."
            },
            "calculated_current": {
                "value": round(current, 2),
                "unit": "A",
                "info": "Corriente de cálculo para la potencia especificada."
            }
        }
        
    # --- CÁLCULO 3, 4, 5 (Corriente, Tensión, Protecciones) - Placeholder ---
    # Estos cálculos son más complejos y dependen de tablas normativas (Iz, Kt, Ka).
    # Por ahora, creamos funciones placeholder que devuelven resultados de ejemplo.
    
    def calculate_current(self, method: str, params: Dict) -> Dict:
        """Calcula la corriente basado en diferentes métodos. (Placeholder)"""
        # La implementación real requeriría un switch/case para 'method'
        return {"calculated_current": {"value": 13.04, "unit": "A", "info": f"Corriente calculada usando {method} (resultado de ejemplo)."}}

    def calculate_voltage(self, method: str, params: Dict) -> Dict:
        """Calcula la tensión basado en diferentes métodos. (Placeholder)"""
        return {"calculated_voltage": {"value": 230.0, "unit": "V", "info": f"Tensión calculada usando {method} (resultado de ejemplo)."}}

    def calculate_protections(self, params: Dict) -> Dict:
        """Calcula las protecciones eléctricas adecuadas. (Placeholder)"""
        # La lógica real aquí es muy compleja (tablas UNE, etc.)
        return {
            "magnetotermico": {"value": "C16", "unit": "A", "info": "Magnetotérmico recomendado (ejemplo)."},
            "diferencial": {"value": "30", "unit": "mA", "info": "Sensibilidad del diferencial recomendada (ejemplo)."}
        }

    # --- CÁLCULO 6: SEPARACIÓN DE PANELES (NUEVO) ---
    def calculate_panel_separation(
        self,
        panel_vertical_side_m: float,
        panel_inclination_deg: float,
        latitude_deg: float
    ) -> Dict:
        """
        Calcula la distancia mínima entre filas de paneles para evitar sombras.
        """
        if panel_vertical_side_m <= 0:
            raise ValueError("El lado vertical del panel debe ser mayor que cero.")

        # Convertir ángulos a radianes para los cálculos trigonométricos
        beta = math.radians(panel_inclination_deg)
        phi = math.radians(latitude_deg)
        
        # Ángulo solar en el solsticio de invierno (día más desfavorable)
        # alpha = 90 - phi - 23.45 (fórmula simplificada)
        # Fórmula más precisa de la altura solar (h) a mediodía solar
        # h = arcsin(sin(δ)sin(φ) + cos(δ)cos(φ)cos(HRA))
        # Para el mediodía HRA=0, para el solsticio de invierno δ=-23.45°
        declinacion_invierno = math.radians(-23.45)
        altura_solar_mediodia_rad = math.asin(
            math.sin(declinacion_invierno) * math.sin(phi) + 
            math.cos(declinacion_invierno) * math.cos(phi)
        )
        
        if altura_solar_mediodia_rad <= 0:
            return {
                "d1_distance_m": {"value": float('inf'), "info": "En esta latitud, el sol no se eleva lo suficiente en invierno."},
                "d2_distance_m": {"value": float('inf'), "info": "Sombra permanente en invierno."}
            }

        # Altura del panel (h)
        h_panel = panel_vertical_side_m * math.sin(beta)
        
        # Distancia horizontal cubierta por el panel (x)
        x_panel = panel_vertical_side_m * math.cos(beta)
        
        # Longitud de la sombra (L)
        longitud_sombra = h_panel / math.tan(altura_solar_mediodia_rad)
        
        # Distancia D1 (desde el final de una fila al inicio de la siguiente)
        d1 = longitud_sombra - x_panel
        if d1 < 0: 
            d1 = 0 # No hay separación necesaria si la sombra no supera al propio panel
            
        # Distancia D2 (entre los puntos más bajos de las filas)
        d2 = d1 + x_panel
        
        return {
            "d1_distance_m": {
                "value": round(d1, 2),
                "unit": "m",
                "info": "Distancia mínima entre el borde superior de una fila y el borde inferior de la siguiente."
            },
            "d2_distance_m": {
                "value": round(d2, 2),
                "unit": "m",
                "info": "Distancia mínima entre los ejes o bordes inferiores de las filas de paneles."
            }
        }
