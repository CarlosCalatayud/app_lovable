# app/calculator.py

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