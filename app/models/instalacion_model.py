# app/models/instalacion_model.py

import logging
from .base_model import _execute_select

# --- LECTURA ---
def get_all_instalaciones(conn, app_user_id, ciudad=None):
    """
    Obtiene un resumen de las instalaciones de un usuario, con filtrado opcional.
    Versión con la sintaxis SQL corregida.
    """
    sql = """
        SELECT 
            i.id, 
            i.descripcion,
            d.localidad, 
            d.provincia
        FROM instalaciones i
        JOIN clientes c ON i.cliente_id = c.id
        LEFT JOIN direcciones d ON i.direccion_emplazamiento_id = d.id
        WHERE c.app_user_id = %s
    """
    
    params = [app_user_id]

    if ciudad:
        sql += " AND lower(d.localidad) LIKE %s"
        params.append(f"%{ciudad.lower()}%")

    # CTO: CORRECCIÓN - Solo hay UNA cláusula ORDER BY al final.
    sql += " ORDER BY i.id DESC"
    
    return _execute_select(conn, sql, tuple(params))

def get_instalacion_completa(conn, instalacion_id, app_user_id):
    """
    Obtiene TODOS los datos de una instalación específica para rellenar un formulario de edición.
    Esto incluye datos de la instalación, su dirección de emplazamiento completa y sus tramos de cableado.
    La seguridad se garantiza comprobando que la instalación pertenece al app_user_id.
    """
    
    # CTO: Consulta Principal. Ahora une todas las tablas necesarias y extrae
    # todos los campos de la dirección de emplazamiento, usando alias para evitar conflictos de nombres.
    sql_principal = """
        SELECT 
            i.*,
            -- Datos del Cliente
            c.nombre AS cliente_nombre, c.apellidos AS cliente_apellidos, c.dni AS cliente_dni,
            -- Datos del Promotor
            p.nombre_razon_social AS promotor_nombre, p.dni_cif AS promotor_cif,
            -- Datos del Instalador
            inst.nombre_empresa AS instalador_empresa, inst.cif_empresa AS instalador_cif,
            -- CTO: Datos COMPLETOS de la dirección de emplazamiento con alias
            dir_emp.alias AS emplazamiento_alias,
            dir_emp.tipo_via_id AS emplazamiento_tipo_via_id,
            dir_emp.nombre_via AS emplazamiento_nombre_via,
            dir_emp.numero_via AS emplazamiento_numero_via,
            dir_emp.piso_puerta AS emplazamiento_piso_puerta,
            dir_emp.codigo_postal AS emplazamiento_codigo_postal,
            dir_emp.localidad AS emplazamiento_localidad,
            dir_emp.provincia AS emplazamiento_provincia,
            -- Nombres de entidades de catálogo para visualización
            ps.nombre_panel AS panel_solar_nombre,
            inv.nombre_inversor AS inversor_nombre,
            b.nombre_bateria AS bateria_nombre,
            d.nombre_distribuidora AS distribuidora_nombre,
            tf.nombre AS tipo_finca_nombre
        FROM instalaciones i
        -- CTO: El JOIN con clientes es CLAVE para la seguridad multi-tenant.
        JOIN clientes c ON i.cliente_id = c.id
        -- CTO: Usamos LEFT JOIN para las demás entidades, ya que pueden ser opcionales.
        LEFT JOIN promotores p ON i.promotor_id = p.id
        LEFT JOIN instaladores inst ON i.instalador_id = inst.id
        LEFT JOIN direcciones dir_emp ON i.direccion_emplazamiento_id = dir_emp.id
        LEFT JOIN paneles_solares ps ON i.panel_solar_id = ps.id
        LEFT JOIN inversores inv ON i.inversor_id = inv.id
        LEFT JOIN baterias b ON i.bateria_id = b.id
        LEFT JOIN distribuidoras d ON i.distribuidora_id = d.id
        LEFT JOIN tipos_finca tf ON i.tipo_finca_id = tf.id
        WHERE 
            i.id = %s AND i.app_user_id = %s;
    """
    
    # CTO: _execute_select ya maneja el cursor y devuelve un diccionario, lo cual es perfecto.
    instalacion_data = _execute_select(conn, sql_principal, (instalacion_id, app_user_id), one=True)
    
    # Si la instalación no se encuentra o no pertenece al usuario, devolvemos None inmediatamente.
    if not instalacion_data:
        return None

    # CTO: Consulta Secundaria para la relación uno-a-muchos (tramos de cableado)
    # Este enfoque de dos pasos es más limpio que un JOIN que duplicaría los datos de la instalación.
    sql_tramos = """
        SELECT * 
        FROM tramos_cableado_instalacion 
        WHERE instalacion_id = %s 
        ORDER BY id ASC;
    """
    tramos_data = _execute_select(conn, sql_tramos, (instalacion_id,))
    
    # CTO: Combinamos los resultados en un único objeto.
    # El frontend recibirá un JSON con un objeto principal y un array anidado para los tramos.
    instalacion_data['tramos_cableado'] = tramos_data
    
    return instalacion_data


# --- ESCRITURA ---
def add_instalacion(conn, data):
    direccion_data = data.get('direccion_emplazamiento', {})
    tramos_data = data.get('tramos_cableado', [])
    
    try:
        with conn: # Transacción automática
            with conn.cursor() as cursor:
                # Paso 1: Crear la dirección de emplazamiento
                sql_direccion = "INSERT INTO direcciones (alias, tipo_via_id, nombre_via, numero_via, piso_puerta, codigo_postal, localidad, provincia) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;"
                cursor.execute(sql_direccion, (
                    direccion_data.get('alias', 'Emplazamiento'), direccion_data.get('tipo_via_id'),
                    direccion_data.get('nombre_via'), direccion_data.get('numero_via'),
                    direccion_data.get('piso_puerta'), direccion_data.get('codigo_postal'),
                    direccion_data.get('localidad'), direccion_data.get('provincia')
                ))
                direccion_emplazamiento_id = cursor.fetchone()['id']

                # Paso 2: Crear la instalación con TODAS las columnas
                sql_instalacion = """
                    INSERT INTO instalaciones (
                        app_user_id, cliente_id, promotor_id, instalador_id, direccion_emplazamiento_id, tipo_finca_id,
                        panel_solar_id, inversor_id, bateria_id, distribuidora_id, descripcion, numero_paneles,
                        numero_inversores, numero_baterias, cups, potencia_contratada_w, referencia_catastral,
                        tipo_de_cubierta, protector_sobretensiones, diferencial_a, sensibilidad_ma, tipo_estructura_id
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    ) RETURNING id;
                """
                params = (
                    data.get('app_user_id'), data.get('cliente_id'), data.get('promotor_id'), data.get('instalador_id'),
                    direccion_emplazamiento_id, data.get('tipo_finca_id'), data.get('panel_solar_id'),
                    data.get('inversor_id'), data.get('bateria_id'), data.get('distribuidora_id'),
                    data.get('descripcion'), data.get('numero_paneles'), data.get('numero_inversores'),
                    data.get('numero_baterias'), data.get('cups'), data.get('potencia_contratada_w'),
                    data.get('referencia_catastral'), data.get('tipo_de_cubierta'),
                    data.get('protector_sobretensiones'), data.get('diferencial_a'),
                    data.get('sensibilidad_ma'), data.get('tipo_estructura_id')
                )
                cursor.execute(sql_instalacion, params)
                instalacion_id = cursor.fetchone()['id']

                # Paso 3: Insertar los tramos de cableado
                if tramos_data:
                    sql_tramos = "INSERT INTO tramos_cableado_instalacion (instalacion_id, tipo_cable_id, material, longitud_m, seccion_mm2, descripcion) VALUES (%s, %s, %s, %s, %s, %s);"
                    tramos_params = [(instalacion_id, tramo.get('tipo_cable_id'), tramo.get('material'), tramo.get('longitud_m'), tramo.get('seccion_mm2'), tramo.get('descripcion')) for tramo in tramos_data]
                    cursor.executemany(sql_tramos, tramos_params)

        logging.info(f"Instalación creada con éxito. ID: {instalacion_id}")
        return instalacion_id, "Instalación creada correctamente."
    except Exception as e:
        logging.error(f"Fallo en transacción de añadir instalación: {e}")
        return None, f"Error en la base de datos: {e}"
    
def delete_instalacion(conn, instalacion_id, app_user_id):
    """
    Elimina una instalación, su dirección de emplazamiento y sus tramos de cableado
    en una única transacción. La seguridad se verifica a través del cliente asociado.
    """
    try:
        with conn: # Inicia la transacción
            with conn.cursor() as cursor:
                # Paso 1: Verificar la propiedad y obtener el ID de la dirección de emplazamiento
                # Hacemos un JOIN con clientes para asegurarnos de que el usuario es el dueño.
                sql_get_ids = """
                    SELECT i.direccion_emplazamiento_id 
                    FROM instalaciones i
                    JOIN clientes c ON i.cliente_id = c.id
                    WHERE i.id = %s AND c.app_user_id = %s;
                """
                cursor.execute(sql_get_ids, (instalacion_id, app_user_id))
                result = cursor.fetchone()
                if not result:
                    raise ValueError("Instalación no encontrada o no autorizado para esta operación.")
                
                direccion_emplazamiento_id = result['direccion_emplazamiento_id']

                # Paso 2: Eliminar los tramos de cableado asociados a la instalación
                cursor.execute(
                    "DELETE FROM tramos_cableado_instalacion WHERE instalacion_id = %s",
                    (instalacion_id,)
                )
                
                # Paso 3: Eliminar la instalación
                cursor.execute("DELETE FROM instalaciones WHERE id = %s", (instalacion_id,))
                
                # Paso 4: Eliminar la dirección de emplazamiento asociada
                if direccion_emplazamiento_id is not None:
                    cursor.execute("DELETE FROM direcciones WHERE id = %s", (direccion_emplazamiento_id,))

        logging.info(f"Instalación ID: {instalacion_id} y sus datos asociados eliminados correctamente.")
        return True, "Instalación eliminada correctamente."

    except Exception as e:
        logging.error(f"Fallo en la transacción de eliminar instalación: {e}")
        return False, f"Error al eliminar la instalación: {e}"
