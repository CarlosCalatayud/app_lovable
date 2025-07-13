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

        # --- NUEVA ESTRUCTURA DE DATOS PARA LA TABLA UNE ---
    IZ_TABLE_UNE = {
        # Formato: { 'metodo': { 'aislamiento': { num_conductores: { seccion: Iz } } } }
        'A1': {
            'PVC': {
                2: {1.5: 11, 2.5: 15, 4: 20, 6: 25, 10: 33},
                3: {1.5: 11.5, 2.5: 15.5, 4: 20, 6: 26, 10: 36}
            },
            'XLPE/EPR': {
                2: {1.5: 14.5, 2.5: 20, 4: 26, 6: 34, 10: 45},
                3: {1.5: 15.5, 2.5: 21, 4: 27, 6: 35, 10: 47}
            }
        },
        'A2': {
            'PVC': {
                2: {1.5: 12.5, 2.5: 17, 4: 22, 6: 29},
                3: {1.5: 13.5, 2.5: 18, 4: 24, 6: 31}
            },
            'XLPE/EPR': {
                2: {1.5: 16, 2.5: 22, 4: 29, 6: 37},
                3: {1.5: 17.5, 2.5: 23, 4: 30, 6: 39}
            }
        },
        'B1': {
            'PVC': {
                2: {1.5: 16.5, 2.5: 23, 4: 31, 6: 40, 10: 54, 16: 72, 25: 91, 35: 109, 50: 133, 70: 170, 95: 204, 120: 228},
                3: {1.5: 14.5, 2.5: 20, 4: 27, 6: 34, 10: 46, 16: 60, 25: 75, 35: 90, 50: 110, 70: 139, 95: 164, 120: 184}
            }
        },
        'B2': {
            'PVC': {
                2: {1.5: 15.5, 2.5: 21, 4: 28, 6: 36, 10: 49, 16: 65, 25: 80, 35: 96, 50: 114, 70: 143},
                3: {1.5: 13.5, 2.5: 18, 4: 24, 6: 31, 10: 42, 16: 55, 25: 68, 35: 81, 50: 96, 70: 121}
            },
            'XLPE/EPR': {
                2: {1.5: 21, 2.5: 28, 4: 36, 6: 46, 10: 63, 16: 85},
                3: {1.5: 18.5, 2.5: 25, 4: 32, 6: 41, 10: 55, 16: 73}
            }
        },
        'C': {
            'PVC': {
                2: {1.5: 17.5, 2.5: 24, 4: 32, 6: 41, 10: 57, 16: 75, 25: 94, 35: 113, 50: 134, 70: 171, 95: 207, 120: 234, 150: 269, 185: 308, 240: 364},
                3: {1.5: 15.5, 2.5: 21, 4: 28, 6: 36, 10: 50, 16: 66, 25: 82, 35: 100, 50: 119, 70: 151, 95: 182, 120: 207, 150: 239, 185: 275, 240: 328}
            },
            'XLPE/EPR': {
                2: {1.5: 23, 2.5: 32, 4: 42, 6: 54, 10: 73, 16: 98, 25: 122, 35: 147, 50: 174, 70: 222, 95: 268, 120: 304, 150: 348, 185: 399, 240: 471},
                3: {1.5: 20, 2.5: 28, 4: 37, 6: 47, 10: 64, 16: 85, 25: 106, 35: 128, 50: 153, 70: 195, 95: 235, 120: 266, 150: 305, 185: 350, 240: 419}
            }
        },
        'E': {
            'PVC': {
                2: {1.5: 19.5, 2.5: 27, 4: 36, 6: 46, 10: 63, 16: 85, 25: 108, 35: 130, 50: 151, 70: 192, 95: 232, 120: 262, 150: 299, 185: 340, 240: 401},
                3: {1.5: 17.5, 2.5: 24, 4: 32, 6: 41, 10: 56, 16: 75, 25: 95, 35: 114, 50: 132, 70: 167, 95: 201, 120: 227, 150: 258, 185: 293, 240: 345}
            },
            'XLPE/EPR': {
                2: {1.5: 26, 2.5: 36, 4: 48, 6: 61, 10: 83, 16: 110, 25: 139, 35: 167, 50: 195, 70: 249, 95: 299, 120: 337, 150: 384, 185: 436, 240: 513},
                3: {1.5: 23, 2.5: 32, 4: 42, 6: 53, 10: 72, 16: 97, 25: 122, 35: 147, 50: 172, 70: 218, 95: 261, 120: 294, 150: 334, 185: 379, 240: 445}
            }
        },
        'F': {
            'PVC': {
                3: {25: 110, 35: 135, 50: 153, 70: 188, 95: 220, 120: 243, 150: 276, 185: 312, 240: 367}
            }
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
            # Seleccionamos la sub-tabla correcta
            metodo_data = self.IZ_TABLE_UNE[metodo_instalacion]
            aislamiento_data = metodo_data[aislamiento]
            iz_cobre_map = aislamiento_data[num_conductores]
            
            # Buscamos la sección. Si no existe la exacta, cogemos la inmediatamente inferior.
            secciones_disponibles = sorted([s for s in iz_cobre_map.keys() if s <= seccion], reverse=True)
            if not secciones_disponibles:
                raise ValueError(f"Sección {seccion}mm² demasiado pequeña para el método seleccionado.")
            
            seccion_a_usar = secciones_disponibles[0]
            iz_base_cobre = iz_cobre_map[seccion_a_usar]

        except KeyError:
            raise ValueError("Combinación de método, aislamiento o número de conductores no válida o no implementada en la tabla.")

        # 2. Aplicar factor de corrección para el material
        if material == 'cobre':
            return iz_base_cobre
        elif material == 'aluminio':
            # El aluminio tiene aprox. el 78% de la capacidad del cobre para la misma sección
            # Este es un factor de corrección común.
            return iz_base_cobre * 0.78
        else:
            raise ValueError("Material no válido.")



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
