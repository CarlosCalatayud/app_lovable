# calculations.py
import datetime
import random
import math # Para cálculos más complejos si son necesarios

# --- Constantes (ej. de Textos!) ---
TEXTO_SIN_ACUMULACION = "La instalación no dispone de sistema de acumulación."
TEXTO_CON_ACUMULACION = "La instalación dispone de sistema de acumulación."
TEXTO_UN_STRING = "La instalación fotovoltaica está compuesta por un único string."
TEXTO_VARIOS_STRINGS = "La instalación fotovoltaica está compuesta por varios strings."
RHO_COBRE = 0.0172 # Ohm * mm^2 / m (Resistividad del cobre a 20°C)


# Resistividad del cobre (Ohm * mm^2 / m)
RHO_COBRE = 1 / 58 

def get_lookup_data(cursor, table_name, lookup_value, lookup_column_name, target_column_name):
    if lookup_value is None or lookup_value == '':
        return None
    try:
        query = f"SELECT {target_column_name} FROM {table_name} WHERE {lookup_column_name} = ?"
        cursor.execute(query, (lookup_value,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception as e:
        print(f"Error en get_lookup_data para tabla {table_name}, columna {lookup_column_name} con valor {lookup_value}: {e}")
        return None

def get_full_product_data(cursor, table_name, product_name_value, name_column="nombre_producto"):
    """Obtiene todos los datos de un producto como un diccionario."""
    if not product_name_value:
        return {}
    try:
        query = f"SELECT * FROM {table_name} WHERE {name_column} = ?"
        cursor.execute(query, (product_name_value,))
        row = cursor.fetchone()
        return dict(row) if row else {}
    except Exception as e:
        print(f"Error en get_full_product_data para tabla {table_name}, columna {name_column} con valor {product_name_value}: {e}")
        return {}


def calculate_all_derived_data(user_inputs, db_conn):
    """
    Calcula todos los campos derivados.
    user_inputs: un diccionario con los datos introducidos por el usuario y los de la BD.
                 Se espera que este diccionario ya contenga los datos aplanados
                 (ej. 'nombre_cliente' en lugar de user_inputs['cliente']['nombre']).
                 Y que los campos de datos_tecnicos también estén al nivel superior de user_inputs.
    db_conn: una conexión a la base de datos SQLite.
    Retorna un diccionario con todos los campos calculados.
    """
    calculated_data = {}
    cursor = db_conn.cursor()

    # --- Helper para obtener valores de user_inputs de forma segura ---
    # Modificado para no depender de 'user_inputs' globalmente, sino del 'source_dict' pasado.
    def get_input(key, default=None, data_type=str, source_dict=None): # Se añade source_dict como parámetro
        if source_dict is None: # Si no se pasa source_dict, se usa user_inputs (el argumento de la función principal)
            source_dict_to_use = user_inputs
        else:
            source_dict_to_use = source_dict

        val_str = source_dict_to_use.get(key) # Usar .get() en el diccionario correcto

        # Si el valor es None o un string vacío, devolver el default
        if val_str is None or (isinstance(val_str, str) and val_str.strip() == ''):
            return default
        
        try:
            # Convertir a string primero para manejar números y otros tipos que vienen como string
            val_as_str = str(val_str)
            if data_type == int:
                return int(float(val_as_str.replace(',', '.'))) # Convertir a float primero para manejar decimales como "10,0"
            elif data_type == float:
                return float(val_as_str.replace(',', '.'))
            elif data_type == bool:
                 return val_as_str.lower() in ['true', '1', 't', 'y', 'yes', 'si', 'sí']
            # Para str y otros tipos directos
            return data_type(val_str) # Aquí val_str es el valor original, no el str(val_str)
        except (ValueError, TypeError):
            # print(f"Advertencia: No se pudo convertir '{val_str}' para la clave '{key}' al tipo {data_type}. Usando default: {default}")
            return default

    # --- DATOS DIRECTOS Y LOOKUPS BÁSICOS ---
    dia = get_input('dia_fecha_instalacion', default=datetime.date.today().day, data_type=int) # Asumimos que estos vienen de user_inputs
    mes = get_input('mes_fecha_instalacion', default=datetime.date.today().month, data_type=int)
    anio = get_input('anio_fecha_instalacion', default=datetime.date.today().year, data_type=int)
    calculated_data['fecha_completa'] = f"{dia:02d}/{mes:02d}/{anio}" # Formato con ceros

    # Datos del Panel Seleccionado
    # 'panel_solar_id' vendrá de user_inputs (que es el context_dict en api_routes)
    # user_inputs['panel_solar_id'] es el ID. Necesitamos el nombre para buscar o los datos completos del panel.
    # Asumimos que user_inputs ya tiene los datos del panel si se seleccionó
    # o que `nombre_del_panel` es una clave en user_inputs que contiene el nombre del panel.
    # Si guardaste el ID en datos_tecnicos.panel_solar_id, necesitarías un lookup por ID.
    # Por ahora, asumo que 'nombre_del_panel' está en user_inputs y es el nombre del panel.

    # panel_data = get_full_product_data(cursor, "PanelesSolares", get_input('nombre_del_panel'), "nombre_panel")
    # Mejorado: Si guardas panel_solar_id en user_inputs (que es el context_dict)
    panel_id_seleccionado = get_input('panel_solar_id', data_type=int) # Viene de datos_tecnicos
    panel_data = {}
    if panel_id_seleccionado is not None:
        panel_row = cursor.execute("SELECT * FROM PanelesSolares WHERE id = ?", (panel_id_seleccionado,)).fetchone()
        if panel_row:
            panel_data = dict(panel_row)

    calculated_data['potencia_pico_panel_w'] = panel_data.get('potencia_pico_w')
    # ... (todos los demás campos de panel_data.get('...'))
    calculated_data['corriente_maxima_funcionamiento_panel_a'] = panel_data.get('corriente_maxima_funcionamiento_a')
    calculated_data['largo_panel_mm'] = panel_data.get('largo_mm')
    calculated_data['ancho_panel_mm'] = panel_data.get('ancho_mm')
    calculated_data['profundidad_panel_mm'] = panel_data.get('profundidad_mm')
    calculated_data['peso_panel_kg'] = panel_data.get('peso_kg')
    calculated_data['eficiencia_panel_porcentaje'] = panel_data.get('eficiencia_panel_porcentaje')
    calculated_data['tension_circuito_abierto_voc_panel'] = panel_data.get('tension_circuito_abierto_voc')
    calculated_data['tecnologia_panel_solar'] = panel_data.get('tecnologia_panel_solar')
    calculated_data['numero_celdas_panel'] = panel_data.get('numero_celdas_panel')
    calculated_data['tension_maximo_funcionamiento_panel_v'] = panel_data.get('tension_maximo_funcionamiento_v')
    calculated_data['fusible_cc_recomendada_a_panel'] = panel_data.get('fusible_cc_recomendada_a')


    # Datos del Inversor Seleccionado
    # nombre_inversor_seleccionado = get_input('nombre_inversor_site') # Si viene así desde el form
    # inverter_data = get_full_product_data(cursor, "Inversores", nombre_inversor_seleccionado, "nombre_inversor")
    inversor_id_seleccionado = get_input('inversor_id', data_type=int) # Viene de datos_tecnicos
    inverter_data = {}
    if inversor_id_seleccionado is not None:
        inverter_row = cursor.execute("SELECT * FROM Inversores WHERE id = ?", (inversor_id_seleccionado,)).fetchone()
        if inverter_row:
            inverter_data = dict(inverter_row)
    
    calculated_data['tipo_conexion_inversor'] = inverter_data.get('monofasico_trifasico')
    # ... (todos los demás campos de inverter_data.get('...'))
    calculated_data['potencia_nominal_inversor_va'] = inverter_data.get('potencia_salida_va')
    calculated_data['largo_inversor_mm'] = inverter_data.get('largo_inversor_mm')
    calculated_data['ancho_inversor_mm'] = inverter_data.get('ancho_inversor_mm')
    calculated_data['profundo_inversor_mm'] = inverter_data.get('profundo_inversor_mm')
    calculated_data['peso_inversor_kg'] = inverter_data.get('peso_inversor_kg')
    calculated_data['proteccion_ip_inversor'] = inverter_data.get('proteccion_ip_inversor')
    calculated_data['potencia_max_paneles_w_inversor'] = inverter_data.get('potencia_max_paneles_w')
    calculated_data['tension_max_entrada_v_inversor'] = inverter_data.get('tension_max_entrada_v')
    calculated_data['secciones_ca_recomendado_mm2_inversor'] = inverter_data.get('secciones_ca_recomendado_mm2')
    calculated_data['corriente_maxima_salida_a_inversor'] = inverter_data.get('corriente_maxima_salida_a')
    calculated_data['magnetotermico_a_inversor'] = inverter_data.get('magnetotermico_a')


    # Datos Batería Seleccionada
    # nombre_bateria_seleccionada = get_input('nombre_de_baterias') # Si viene así del form
    # capacidad_bateria_unitaria_kwh = get_lookup_data(cursor, "Baterias", nombre_bateria_seleccionada, "nombre_bateria", "capacidad_kwh")
    bateria_id_seleccionada = get_input('bateria_id', data_type=int) # Viene de datos_tecnicos
    capacidad_bateria_unitaria_kwh = 0
    if bateria_id_seleccionada is not None:
        bateria_row = cursor.execute("SELECT capacidad_kwh FROM Baterias WHERE id = ?", (bateria_id_seleccionada,)).fetchone()
        if bateria_row:
            capacidad_bateria_unitaria_kwh = bateria_row['capacidad_kwh']
            
    cantidad_baterias = get_input('cantidad_de_baterias', default=0, data_type=int) # ¿Este campo está en user_inputs?
    if capacidad_bateria_unitaria_kwh is not None and cantidad_baterias is not None:
        calculated_data['capacidad_total_almacenamiento_kwh'] = cantidad_baterias * capacidad_bateria_unitaria_kwh
    else:
        calculated_data['capacidad_total_almacenamiento_kwh'] = 0

    # --- CAMPOS CALCULADOS CON LÓGICA IF/ELSE Y CONCATENACIONES ---
    # ... (Direcciones y Nombres completos - asegúrate que las claves como 'tipo_via_cliente' existen en user_inputs)
    # Aquí asumo que los campos del cliente, promotor, etc., ya están aplanados en user_inputs
    # por la función get_instalacion_completa y cómo se construye context_dict
    
    tipo_via_c = get_input('tipo_via_cliente', default='') # Asume que este campo viene del cliente asociado
    nombre_via_c = get_input('nombre_via_cliente', default='')
    # ... etc ...
    calculated_data['direccion_completa_suministro_consumidor'] = f"{tipo_via_c} {nombre_via_c} ..." # Simplificado

    calculated_data['nombre_completo_cliente'] = f"{get_input('usuario_nombre', default='')} {get_input('usuario_apellidos', default='')}".strip()


    # Referencia interna promotor
    cups_val = get_input('cups', default='') # Este 'cups' debe venir de user_inputs.datos_tecnicos.cups
    calculated_data['referencia_interna_promotor'] = f"{cups_val}?????" # Placeholder


    # --- CORRECCIÓN EN LAS LLAMADAS A GET_INPUT ---
    # (Aplica 'default=' en lugar de 'default_value=')
    # (Asegúrate que 'source_dict=user_inputs' no es necesario si 'user_inputs' es el default en get_input)

    # Potencia contratada y otros datos directos de user_inputs.datos_tecnicos
    potencia_contratada = get_input('potencia_contratada_kw', default=0.0, data_type=float)
    cups_instalacion_val = get_input('cups', default='', data_type=str) # Renombrado para evitar conflicto con la variable cups_val
    referencia_catastral = get_input('referencia_catastral', default='', data_type=str)
    
    calculated_data['potencia_contratada_kw'] = potencia_contratada # Guardamos la potencia contratada
    calculated_data['cups'] = cups_instalacion_val
    calculated_data['referencia_catastral'] = referencia_catastral

    # Para tipo_estructura, tipo_cubierta, tipo_finca (que vienen como strings desde el frontend ahora)
    calculated_data['tipo_estructura_seleccionada'] = get_input('tipo_estructura', default='', data_type=str)
    calculated_data['tipo_cubierta_seleccionada'] = get_input('tipo_cubierta', default='', data_type=str)
    calculated_data['tipo_finca_seleccionada'] = get_input('tipo_finca', default='', data_type=str) # Asume que se guarda el string

    # Cálculo de potencia máxima de instalación (GW)
    if potencia_contratada > 0:
        calculated_data['potencia_maxima_instalacion_kw'] = potencia_contratada * 1.25
    else:
        calculated_data['potencia_maxima_instalacion_kw'] = 0.0

    # ... (El resto de tus cálculos existentes, asegurándote de que las claves
    #      que usas en get_input() existen en el diccionario user_inputs
    #      que se pasa a calculate_all_derived_data. Este user_inputs es el
    #      final_context que construyes en api_routes.py, así que los campos de
    #      datos_tecnicos deberían estar directamente accesibles, no anidados) ...

    # Ejemplo: Si en datos_tecnicos tienes 'numero_de_strings'
    num_strings = get_input('numero_strings', default=0, data_type=int) # 'numero_strings' debe estar en el user_inputs
    # Y así para todos los demás campos...


    # --- LIMPIEZA FINAL ---
    final_calculated_data = {}
    for k, v_val in calculated_data.items(): # Renombré v a v_val para evitar conflicto con el panel
        if isinstance(v_val, (int, float)):
            final_calculated_data[k] = v_val if v_val is not None else 0
        else:
            final_calculated_data[k] = v_val if v_val is not None else ""
            
    return final_calculated_data
