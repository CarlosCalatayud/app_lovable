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
    
    # CTO: Consulta Principal. Corregida para coincidir con el esquema real de la BD.
    sql_principal = """
        SELECT 
            i.*,
            -- Datos del Cliente
            c.nombre AS cliente_nombre, c.apellidos AS cliente_apellidos, c.dni AS cliente_dni,
            -- Datos del Promotor
            p.nombre_razon_social AS promotor_nombre, p.dni_cif AS promotor_cif,
            -- Datos del Instalador
            inst.nombre_empresa AS instalador_empresa, inst.cif_empresa AS instalador_cif,
            -- Datos COMPLETOS de la dirección de emplazamiento con alias
            dir_emp.alias AS emplazamiento_alias,
            dir_emp.tipo_via_id AS emplazamiento_tipo_via_id,
            dir_emp.nombre_via AS emplazamiento_nombre_via,
            dir_emp.numero_via AS emplazamiento_numero_via,
            dir_emp.piso_puerta AS emplazamiento_piso_puerta,
            dir_emp.codigo_postal AS emplazamiento_codigo_postal,
            dir_emp.localidad AS emplazamiento_localidad,
            dir_emp.provincia AS emplazamiento_provincia,
            -- Nombres de entidades de catálogo para visualización (CORREGIDOS)
            ps.nombre_panel AS panel_solar_nombre,
            inv.nombre_inversor AS inversor_nombre,
            b.nombre_bateria AS bateria_nombre,
            d.nombre_distribuidora AS distribuidora_nombre,
            -- CTO: CORRECCIÓN CLAVE AQUÍ -> de 'tf.nombre' a 'tf.nombre_tipo_finca'
            tf.nombre_tipo_finca AS tipo_finca_nombre,
            tes.nombre_tipo_estructura AS tipo_estructura_nombre
        FROM instalaciones i
        -- El JOIN con clientes es CLAVE para la seguridad multi-tenant.
        -- Se comprueba tanto el i.id como el i.app_user_id para doble seguridad.
        JOIN clientes c ON i.cliente_id = c.id
        LEFT JOIN promotores p ON i.promotor_id = p.id
        LEFT JOIN instaladores inst ON i.instalador_id = inst.id
        LEFT JOIN direcciones dir_emp ON i.direccion_emplazamiento_id = dir_emp.id
        LEFT JOIN paneles_solares ps ON i.panel_solar_id = ps.id
        LEFT JOIN inversores inv ON i.inversor_id = inv.id
        LEFT JOIN baterias b ON i.bateria_id = b.id
        LEFT JOIN distribuidoras d ON i.distribuidora_id = d.id
        -- CTO: CORRECCIÓN -> La tabla es tipos_finca
        LEFT JOIN tipos_finca tf ON i.tipo_finca_id = tf.id
        -- CTO: AJUSTE PROACTIVO -> Añadimos la tabla de tipo_estructura
        LEFT JOIN tipos_estructura tes ON i.tipo_estructura_id = tes.id
        WHERE 
            i.id = %s AND i.app_user_id = %s;
    """
    
    instalacion_data = _execute_select(conn, sql_principal, (instalacion_id, app_user_id), one=True)
    
    if not instalacion_data:
        return None

    # Consulta Secundaria para los tramos de cableado (esta ya era correcta)
    sql_tramos = """
        SELECT * 
        FROM tramos_cableado_instalacion 
        WHERE instalacion_id = %s 
        ORDER BY id ASC;
    """
    tramos_data = _execute_select(conn, sql_tramos, (instalacion_id,))
    
    # Combinamos los resultados en un único objeto.
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
    

def update_instalacion(conn, instalacion_id, app_user_id, data):
    """
    Actualiza una instalación existente y sus datos relacionados (dirección, tramos)
    de forma transaccional.
    """
    direccion_data = data.get('direccion_emplazamiento', {})
    tramos_data = data.get('tramos_cableado', [])

    try:
        with conn:  # Inicia transacción
            with conn.cursor() as cursor:
                # CTO: Paso 1 - Seguridad y obtener IDs.
                # Verificamos que la instalación pertenece al usuario y obtenemos el ID de su dirección.
                cursor.execute(
                    "SELECT direccion_emplazamiento_id FROM instalaciones WHERE id = %s AND app_user_id = %s",
                    (instalacion_id, app_user_id)
                )
                instalacion_actual = cursor.fetchone()
                if not instalacion_actual:
                    # Si no se encuentra, no pertenece al usuario. No damos más información.
                    raise ValueError("Instalación no encontrada o acceso no autorizado.")
                
                direccion_emplazamiento_id = instalacion_actual['direccion_emplazamiento_id']

                # CTO: Paso 2 - Actualizar la tabla de direcciones.
                # Solo si se han proporcionado datos de dirección en el JSON.
                if direccion_data and direccion_emplazamiento_id:
                    sql_update_direccion = """
                        UPDATE direcciones SET
                            tipo_via_id = %(tipo_via_id)s, nombre_via = %(nombre_via)s, numero_via = %(numero_via)s,
                            piso_puerta = %(piso_puerta)s, codigo_postal = %(codigo_postal)s,
                            localidad = %(localidad)s, provincia = %(provincia)s
                        WHERE id = %(id)s;
                    """
                    # Añadimos el ID al diccionario de datos para el WHERE
                    direccion_data['id'] = direccion_emplazamiento_id 
                    cursor.execute(sql_update_direccion, direccion_data)

                # CTO: Paso 3 - Actualizar la tabla de instalaciones.
                # Construimos la consulta dinámicamente para ser más flexibles.
                sql_update_instalacion = """
                    UPDATE instalaciones SET
                        cliente_id = %(cliente_id)s, promotor_id = %(promotor_id)s, instalador_id = %(instalador_id)s,
                        tipo_finca_id = %(tipo_finca_id)s, panel_solar_id = %(panel_solar_id)s, inversor_id = %(inversor_id)s,
                        bateria_id = %(bateria_id)s, distribuidora_id = %(distribuidora_id)s, descripcion = %(descripcion)s,
                        numero_paneles = %(numero_paneles)s, numero_inversores = %(numero_inversores)s,
                        numero_baterias = %(numero_baterias)s, cups = %(cups)s, potencia_contratada_w = %(potencia_contratada_w)s,
                        referencia_catastral = %(referencia_catastral)s, tipo_de_cubierta = %(tipo_de_cubierta)s,
                        protector_sobretensiones = %(protector_sobretensiones)s, diferencial_a = %(diferencial_a)s,
                        sensibilidad_ma = %(sensibilidad_ma)s, tipo_estructura_id = %(tipo_estructura_id)s
                    WHERE id = %(id)s AND app_user_id = %(app_user_id)s;
                """
                # Añadimos los IDs necesarios para el WHERE
                data['id'] = instalacion_id
                data['app_user_id'] = app_user_id
                cursor.execute(sql_update_instalacion, data)

                # CTO: Paso 4 - Actualizar tramos de cableado.
                # El enfoque más simple y robusto: borrar los viejos e insertar los nuevos.
                cursor.execute("DELETE FROM tramos_cableado_instalacion WHERE instalacion_id = %s", (instalacion_id,))
                if tramos_data:
                    sql_insert_tramos = """
                        INSERT INTO tramos_cableado_instalacion 
                            (instalacion_id, tipo_cable_id, material, longitud_m, seccion_mm2, descripcion)
                        VALUES (%(instalacion_id)s, %(tipo_cable_id)s, %(material)s, %(longitud_m)s, %(seccion_mm2)s, %(descripcion)s);
                    """
                    # Añadimos el instalacion_id a cada tramo antes de insertar
                    for tramo in tramos_data:
                        tramo['instalacion_id'] = instalacion_id
                    cursor.executemany(sql_insert_tramos, tramos_data)

        # Si todo ha ido bien, la transacción se confirma al salir del 'with conn'.
        return True, "Instalación actualizada correctamente."

    except ValueError as ve:
        # Error de autorización o ID no encontrado
        logging.warning(f"Error de validación al actualizar instalación {instalacion_id}: {ve}")
        return False, str(ve)
    except Exception as e:
        # Cualquier otro error de base de datos
        logging.error(f"Fallo en transacción de actualizar instalación {instalacion_id}: {e}", exc_info=True)
        return False, f"Error en la base de datos: {e}"

