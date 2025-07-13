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

    # CTO: Nueva estructura de datos completa basada en la tabla UNE de la imagen.
    # Formato: { material: { metodo: { aislamiento: { num_conductores: { seccion: Iz } } } } }
    IZ_TABLE_UNE_2020 = {
        'cobre': {
            'A1': {'PVC': {2: {1.5: 15.5, 2.5: 21, 4: 28, 6: 36, 10: 50}, 3: {1.5: 13.5, 2.5: 18, 4: 24, 6: 31, 10: 42}}},
            'A2': {'PVC': {2: {1.5: 14.5, 2.5: 19.5, 4: 26, 6: 34, 10: 46}, 3: {1.5: 13, 2.5: 17.5, 4: 23, 6: 30, 10: 41}}, 'XLPE/EPR': {2: {1.5: 19.5, 2.5: 26, 4: 34, 6: 44, 10: 61}, 3: {1.5: 17, 2.5: 23, 4: 30, 6: 38, 10: 52}}},
            'B1': {'PVC': {2: {1.5: 17.5, 2.5: 24, 4: 32, 6: 41, 10: 57, 16: 76, 25: 96, 35: 119, 50: 144, 70: 184, 95: 223, 120: 256, 150: 294, 185: 337, 240: 395}, 3: {1.5: 15, 2.5: 21, 4: 28, 6: 36, 10: 50, 16: 68, 25: 89, 35: 110, 50: 134, 70: 171, 95: 207, 120: 239, 150: 275, 185: 316, 240: 373}}, 'XLPE/EPR': {2: {1.5: 22, 2.5: 30, 4: 40, 6: 51, 10: 70, 16: 94, 25: 119, 35: 147, 50: 178, 70: 227, 95: 275, 120: 314, 150: 361, 185: 413, 240: 485}, 3: {1.5: 19.5, 2.5: 27, 4: 36, 6: 46, 10: 63, 16: 85, 25: 110, 35: 136, 50: 165, 70: 210, 95: 254, 120: 292, 150: 336, 185: 386, 240: 456}}},
            'B2': {'PVC': {2: {1.5: 16.5, 2.5: 23, 4: 30, 6: 38, 10: 52, 16: 69, 25: 85, 35: 103, 50: 125, 70: 160, 95: 194, 120: 222, 150: 255, 185: 290, 240: 341}, 3: {1.5: 14.5, 2.5: 20, 4: 26, 6: 33, 10: 46, 16: 61, 25: 76, 35: 92, 50: 112, 70: 141, 95: 171, 120: 196, 150: 225, 185: 258, 240: 304}}, 'XLPE/EPR': {2: {1.5: 21, 2.5: 29, 4: 38, 6: 48, 10: 66, 16: 88, 25: 110, 35: 135, 50: 160, 70: 202, 95: 245, 120: 278, 150: 319, 185: 364, 240: 428}, 3: {1.5: 19, 2.5: 26, 4: 34, 6: 43, 10: 59, 16: 78, 25: 98, 35: 120, 50: 144, 70: 182, 95: 220, 120: 250, 150: 288, 185: 328, 240: 387}}},
            'C': {'PVC': {2: {1.5: 18.5, 2.5: 25, 4: 34, 6: 43, 10: 60, 16: 80, 25: 101, 35: 125, 50: 151, 70: 192, 95: 232, 120: 269, 150: 309, 185: 353, 240: 415}, 3: {1.5: 16.5, 2.5: 23, 4: 30, 6: 39, 10: 54, 16: 73, 25: 92, 35: 113, 50: 136, 70: 172, 95: 208, 120: 239, 150: 275, 185: 314, 240: 370}}, 'XLPE/EPR': {2: {1.5: 24, 2.5: 33, 4: 44, 6: 56, 10: 76, 16: 101, 25: 129, 35: 158, 50: 190, 70: 243, 95: 294, 120: 337, 150: 387, 185: 442, 240: 520}, 3: {1.5: 21, 2.5: 29, 4: 39, 6: 50, 10: 68, 16: 91, 25: 115, 35: 141, 50: 168, 70: 213, 95: 258, 120: 296, 150: 340, 185: 388, 240: 457}}},
            'E': {'PVC': {3: {1.5: 18.5, 2.5: 25, 4: 33, 6: 42, 10: 58, 16: 76, 25: 96, 35: 117, 50: 139, 70: 177, 95: 212, 120: 242, 150: 275, 185: 312, 240: 367}}, 'XLPE/EPR': {3: {1.5: 24, 2.5: 33, 4: 43, 6: 55, 10: 75, 16: 100, 25: 125, 35: 151, 50: 178, 70: 228, 95: 273, 120: 310, 150: 353, 185: 401, 240: 471}}},
            'F': {'PVC': {3: {25: 116, 35: 141, 50: 168, 70: 213, 95: 256, 120: 292, 150: 335, 185: 382, 240: 451}}, 'XLPE/EPR': {3: {25: 149, 35: 180, 50: 214, 70: 270, 95: 324, 120: 368, 150: 421, 185: 480, 240: 565}}}
        },
        'aluminio': {
            'A1': {'PVC': {2: {2.5: 12, 4: 16, 6: 21, 10: 28, 16: 38, 25: 50, 35: 62}, 3: {2.5: 11, 4: 14.5, 6: 19, 10: 26, 16: 35, 25: 46, 35: 57}}},
            'A2': {'PVC': {2: {2.5: 11.5, 4: 15.5, 6: 20, 10: 27, 16: 36, 25: 47, 35: 58}, 3: {2.5: 10, 4: 13.5, 6: 18, 10: 24, 16: 32, 25: 41, 35: 51}}, 'XLPE/EPR': {2: {2.5: 15, 4: 20, 6: 26, 10: 36, 16: 48, 25: 61, 35: 75}, 3: {2.5: 13, 4: 18, 6: 23, 10: 31, 16: 41, 25: 53, 35: 65}}},
            'B1': {'PVC': {2: {16: 59, 25: 75, 35: 92, 50: 112, 70: 143, 95: 173, 120: 198, 150: 228, 185: 261, 240: 306}, 3: {16: 52, 25: 68, 35: 85, 50: 103, 70: 132, 95: 160, 120: 185, 150: 213, 185: 245, 240: 289}}, 'XLPE/EPR': {2: {16: 73, 25: 92, 35: 114, 50: 138, 70: 176, 95: 213, 120: 243, 150: 279, 185: 319, 240: 375}, 3: {16: 66, 25: 85, 35: 105, 50: 128, 70: 163, 95: 197, 120: 226, 150: 259, 185: 298, 240: 352}}},
            'B2': {'PVC': {2: {16: 54, 25: 66, 35: 79, 50: 96, 70: 124, 95: 150, 120: 172, 150: 198, 185: 225, 240: 264}, 3: {16: 47, 25: 60, 35: 73, 50: 89, 70: 112, 95: 135, 120: 155, 150: 178, 185: 203, 240: 238}}, 'XLPE/EPR': {2: {16: 68, 25: 85, 35: 104, 50: 125, 70: 158, 95: 190, 120: 217, 150: 247, 185: 281, 240: 329}, 3: {16: 60, 25: 76, 35: 93, 50: 112, 70: 141, 95: 170, 120: 194, 150: 222, 185: 254, 240: 298}}},
            'C': {'PVC': {2: {16: 62, 25: 78, 35: 96, 50: 118, 70: 150, 95: 180, 120: 208, 150: 239, 185: 273, 240: 321}, 3: {16: 55, 25: 70, 35: 86, 50: 105, 70: 134, 95: 161, 120: 185, 150: 213, 185: 243, 240: 286}}, 'XLPE/EPR': {2: {16: 78, 25: 99, 35: 122, 50: 148, 70: 188, 95: 228, 120: 260, 150: 299, 185: 342, 240: 401}, 3: {16: 69, 25: 88, 35: 109, 50: 131, 70: 166, 95: 200, 120: 229, 150: 264, 185: 301, 240: 355}}},
            'E': {'PVC': {3: {16: 59, 25: 74, 35: 90, 50: 107, 70: 137, 95: 164, 120: 187, 150: 213, 185: 241, 240: 283}}, 'XLPE/EPR': {3: {16: 76, 25: 96, 35: 117, 50: 139, 70: 177, 95: 211, 120: 240, 150: 273, 185: 310, 240: 364}}},
            'F': {'PVC': {3: {25: 90, 35: 109, 50: 130, 70: 165, 95: 198, 120: 226, 150: 258, 185: 294, 240: 345}}, 'XLPE/EPR': {3: {25: 115, 35: 139, 50: 166, 70: 210, 95: 251, 120: 285, 150: 325, 185: 370, 240: 434}}}
        }
    }

        # --- TABLAS PARA FACTORES DE CORRECCIÓN ---
    KT_TABLE_TEMP = { # Tabla 52-C1 de la UNE
        # 'aislamiento': { temperatura: Kt }
        'PVC': {10: 1.22, 15: 1.17, 20: 1.12, 25: 1.06, 30: 1.00, 35: 0.94, 40: 0.87, 45: 0.79, 50: 0.71, 55: 0.61, 60: 0.50},
        'XLPE/EPR': {10: 1.15, 15: 1.12, 20: 1.08, 25: 1.04, 30: 1.00, 35: 0.96, 40: 0.91, 45: 0.87, 50: 0.82, 55: 0.76, 60: 0.71, 65: 0.65, 70: 0.58, 75: 0.50, 80: 0.41}
    }
    
    KA_TABLE_AGRUPACION = { # Tabla 52-C1 de la UNE (Ejemplo para Método C)
        # num_circuitos: Ka
        1: 1.00, 2: 0.80, 3: 0.70, 4: 0.65, 5: 0.60, 6: 0.57, 7: 0.54, 8: 0.52, 9: 0.50
    }


        # --- NUEVA FUNCIÓN DE BÚSQUEDA Iz ---
    def get_iz_from_table(
        self,
        seccion: float,
        material: Literal['cobre', 'aluminio'],
        metodo_instalacion: str,
        aislamiento: Literal['PVC', 'XLPE/EPR'],
        num_conductores: int
    ) -> float:
        """Busca la Intensidad Máxima Admisible (Iz) en la tabla UNE."""
        
        # 1. Buscar el valor base para Cobre en la tabla
        try:
            # La ruta de búsqueda ahora es más directa y completa
            material_data = self.IZ_TABLE_UNE_2020[material.lower()]
            metodo_data = material_data[metodo_instalacion.upper()]
            aislamiento_data = metodo_data[aislamiento.upper()]
            iz_map = aislamiento_data[num_conductores]

            secciones_disponibles = sorted([s for s in iz_map.keys() if s <= seccion], reverse=True)
            if not secciones_disponibles:
                raise ValueError(f"Sección {seccion}mm² demasiado pequeña para el método/material seleccionado.")
            
            seccion_a_usar = secciones_disponibles[0]
            iz_base = iz_map[seccion_a_usar]
            return iz_base

        except KeyError:
            raise ValueError(f"Combinación inválida: {material}/{metodo_instalacion}/{aislamiento}/{num_conductores} conductores.")



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

    def calculate_voltage(self, method: str, params: Dict) -> Dict:
        """Calcula la tensión (U) en Voltios, basado en diferentes métodos."""
        
        def get_param(key, default=0.0):
            val = params.get(key)
            if val is None or str(val).strip() == '':
                return default
            return float(str(val).replace(',', '.'))

        # CTO: Extraemos los parámetros que esta función sí utiliza.
        P = get_param('power_p')
        I = get_param('current_i')
        cos_phi = get_param('cos_phi', 1.0)
        Z = get_param('impedance_z')
        
        U = 0.0

        try:
            # CTO: Estos son los únicos dos métodos válidos para esta función.
            if method == "Potencia (P), Corriente (I), cos φ":
                if I * cos_phi == 0: raise ZeroDivisionError("La corriente o el cos(φ) no pueden ser cero.")
                U = P / (I * cos_phi)
            elif method == "Corriente (I) y Impedancia (Z)":
                U = I * Z
            else:
                # Si el frontend envía cualquier otra cosa, falla de forma controlada.
                raise ValueError(f"Método de cálculo de tensión no reconocido: '{method}'")

            return {
                "calculated_voltage": {
                    "value": round(U, 2),
                    "unit": "V",
                    "info": f"Tensión calculada según el método seleccionado."
                }
            }
        except (ValueError, ZeroDivisionError) as e:
            raise ValueError(f"Error en el cálculo de tensión: {e}")
    
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
        """Calcula la corriente (I) en Amperios, basado en diferentes métodos."""
        
        # Función de ayuda interna para obtener valores numéricos de forma segura
        def get_param(key, default=0.0):
            val = params.get(key)
            if val is None or str(val).strip() == '':
                return default
            return float(str(val).replace(',', '.'))

        # Valores comunes que se pueden usar en varias fórmulas
        P = get_param('power_p') # Potencia Activa (W)
        U = get_param('voltage_u') # Tensión (V)
        cos_phi = get_param('cos_phi', 1.0)
        R = get_param('resistance_r') # Resistencia (Ω)
        Z = get_param('impedance_z') # Impedancia (Ω)
        S = get_param('apparent_power_s') # Potencia Aparente (VA)
        Q = get_param('reactive_power_q') # Potencia Reactiva (VAR)
        sin_phi = get_param('sin_phi')
        
        I = 0.0 # Valor por defecto

        try:
            if method == "Potencia (P), Tensión L-N (U), cos φ":
                if U * cos_phi == 0: raise ZeroDivisionError("La tensión o el cos(φ) no pueden ser cero.")
                I = P / (U * cos_phi)
            elif method == "Potencia (P) y Resistencia (R)":
                if R == 0: raise ZeroDivisionError("La resistencia no puede ser cero.")
                I = math.sqrt(P / R)
            elif method == "Tensión L-N (U) y Impedancia (Z)":
                if Z == 0: raise ZeroDivisionError("La impedancia no puede ser cero.")
                I = U / Z
            elif method == "Potencia Aparente (S) y Tensión L-N (U)":
                if U == 0: raise ZeroDivisionError("La tensión no puede ser cero.")
                I = S / U
            elif method == "Potencia Reactiva (Q), Tensión L-N (U), sen φ":
                if U * sin_phi == 0: raise ZeroDivisionError("La tensión o el sen(φ) no pueden ser cero.")
                I = Q / (U * sin_phi)
            else:
                raise ValueError(f"Método de cálculo de corriente no reconocido: {method}")

            return {
                "calculated_current": {
                    "value": round(I, 2),
                    "unit": "A",
                    "info": f"Corriente calculada según Ley de Ohm/Potencia para el método seleccionado."
                }
            }
        except (ValueError, ZeroDivisionError) as e:
            raise ValueError(f"Error en el cálculo de corriente: {e}")

    # --- REEMPLAZO DE LA FUNCIÓN calculate_voltage ---
    def calculate_voltage(self, method: str, params: Dict) -> Dict:
        """Calcula la tensión (U) en Voltios, basado en diferentes métodos."""
        
        def get_param(key, default=0.0):
            val = params.get(key)
            if val is None or str(val).strip() == '':
                return default
            return float(str(val).replace(',', '.'))

        P = get_param('power_p')
        I = get_param('current_i')
        cos_phi = get_param('cos_phi', 1.0)
        Z = get_param('impedance_z')
        
        U = 0.0 # Valor por defecto

        try:
            if method == "Potencia (P), Corriente (I), cos φ":
                if I * cos_phi == 0: raise ZeroDivisionError("La corriente o el cos(φ) no pueden ser cero.")
                U = P / (I * cos_phi)
            elif method == "Corriente (I) y Impedancia (Z)":
                U = I * Z
            else:
                raise ValueError(f"Método de cálculo de tensión no reconocido: {method}")

            return {
                "calculated_voltage": {
                    "value": round(U, 2),
                    "unit": "V",
                    "info": f"Tensión calculada según Ley de Ohm/Potencia para el método seleccionado."
                }
            }
        except (ValueError, ZeroDivisionError) as e:
            raise ValueError(f"Error en el cálculo de tensión: {e}")

    def calculate_protections(self, params: Dict) -> Dict:
        """
        Calcula las protecciones eléctricas adecuadas basándose en Iz y factores de corrección.
        """
        try:
            ib = float(params.get('corriente_empleo_ib'))
            seccion = float(params.get('seccion_fase_cable'))
            material = params.get('conductor')
            aislamiento = params.get('aislamiento')
            metodo_instalacion = params.get('metodo_instalacion')
            temp_ambiente = int(params.get('temp_ambiente', 30))
            num_circuitos_agrupados = int(params.get('circuitos_agrupados', 1))
            num_conductores_cargados = int(params.get('conductores_cargados', 2))

            ### CTO: AÑADIDA VALIDACIÓN DE ENTRADA CRÍTICA ###
            if num_circuitos_agrupados < 1:
                raise ValueError("El número de circuitos agrupados debe ser 1 o mayor.")

            # 2. Obtener factores de corrección (Kt y Ka)
            # Búsqueda de Kt (Temperatura)
            kt_map = self.KT_TABLE_TEMP.get(aislamiento, {})
            temp_a_usar = max([t for t in kt_map.keys() if t <= temp_ambiente], default=None)
            kt = kt_map.get(temp_a_usar, 1.0) 
            ka = self.KA_TABLE_AGRUPACION.get(num_circuitos_agrupados, 0.50)

            # 3. Calcular Iz' (Iz corregida)
            iz_tabla = self.get_iz_from_table(seccion, material, metodo_instalacion, aislamiento, num_conductores_cargados)
            iz_corregida = iz_tabla * kt * ka
            
            # 4. Criterios de selección del magnetotérmico (In)
            calibres_comerciales = [6, 10, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125]
            magnetotermico_in = None
            for calibre in calibres_comerciales:
                if calibre >= ib and calibre <= iz_corregida:
                    if (calibre * 1.45) <= (iz_corregida * 1.45):
                        magnetotermico_in = calibre
                        break
            
            if magnetotermico_in is None:
                resultado_magnetotermico = "No se encontró calibre adecuado. Aumente la sección o revise las condiciones."
            else:
                curva = params.get('curva_magnetotermico', 'C')
                resultado_magnetotermico = f"{curva}{magnetotermico_in}"
                
            # 5. Selección del diferencial
            tipo_diferencial = params.get('tipo_diferencial', 'A')
            resultado_diferencial = f"Tipo {tipo_diferencial}, 30mA (recomendado)"

            return {
                "magnetotermico": {"value": resultado_magnetotermico, "unit": "A", "info": f"Magnetotérmico recomendado. Iz'={round(iz_corregida,2)}A (Kt={kt}, Ka={ka})."},
                "diferencial": {"value": resultado_diferencial, "unit": "mA", "info": "Tipo y sensibilidad del diferencial recomendados."}
            }

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            raise ValueError(f"Error en los datos de entrada para el cálculo de protecciones: {e}")

    # --- CÁLCULO 6: SEPARACIÓN DE PANELES (NUEVO) ---
    def calculate_panel_separation(
        self,
        # CTO: Estos son los nombres de parámetros que la función SIEMPRE ha esperado.
        panel_vertical_side_m: float,
        panel_inclination_deg: float,
        latitude_deg: float
    ) -> Dict:
        """
        Calcula la distancia mínima entre filas de paneles para evitar sombras.
        """
        if panel_vertical_side_m <= 0:
            raise ValueError("El lado vertical del panel debe ser mayor que cero.")

        beta = math.radians(panel_inclination_deg)
        phi = math.radians(latitude_deg)
        declinacion_invierno = math.radians(-23.45)
        
        altura_solar_mediodia_rad = math.asin(
            math.sin(declinacion_invierno) * math.sin(phi) + 
            math.cos(declinacion_invierno) * math.cos(phi)
        )
        
        if altura_solar_mediodia_rad <= 0:
            return { "d1_distance_m": {"value": float('inf')}, "d2_distance_m": {"value": float('inf')} }

        h_panel = panel_vertical_side_m * math.sin(beta)
        x_panel = panel_vertical_side_m * math.cos(beta)
        longitud_sombra = h_panel / math.tan(altura_solar_mediodia_rad)
        d1 = longitud_sombra - x_panel
        if d1 < 0: d1 = 0 
        d2 = d1 + x_panel
        
        return {
            "d1_distance_m": { "value": round(d1, 2), "unit": "m" },
            "d2_distance_m": { "value": round(d2, 2), "unit": "m" }
        }
    
    def calculate_voltage_drop(self, current: dict, length: dict, wire_cross_section: dict, material: str, system_type: str, source_voltage: dict, power_factor: float = 1.0) -> dict:
        """
        Calcula la caída de tensión y devuelve la estructura de respuesta COMPLETA
        que el frontend espera.
        """
        I = self._normalize_current(current)
        L = self._normalize_length(length)
        S = self._normalize_cross_section(wire_cross_section)
        V_source = self._normalize_voltage(source_voltage)

        if S == 0: raise ValueError("La sección del cable no puede ser cero.")
        
        rho = self.RESISTIVIDAD_COBRE if material.lower() == 'cobre' else self.RESISTIVIDAD_ALUMINIO

        if system_type.lower() == 'monofasico':
            voltage_drop_v = (2 * L * rho * I) / S
        else:
            voltage_drop_v = (math.sqrt(3) * L * rho * I * power_factor) / S
        
        voltage_at_load_v = V_source - voltage_drop_v
        voltage_drop_pct = (voltage_drop_v / V_source) * 100 if V_source > 0 else float('inf')

        ### CTO: CORRECCIÓN - Devolvemos la estructura COMPLETA con los 3 campos.
        return {
            "voltage_drop_volts": {
                "value": round(voltage_drop_v, 2),
                "unit": "V",
                "info": "Tensión total perdida."
            },
            "voltage_drop_percent": {
                "value": round(voltage_drop_pct, 2),
                "unit": "%",
                "info": "Porcentaje de la tensión de origen perdida."
            },
            "voltage_at_load": {
                "value": round(voltage_at_load_v, 2),
                "unit": "V",
                "info": "Tensión efectiva en la carga."
            }
        }

