# app/models/instalacion_model.py

import logging
from .base_model import _execute_select

# --- LECTURA ---
def get_all_instalaciones(conn, app_user_id, ciudad=None):
    """
    Obtiene un resumen de las instalaciones de un usuario.
    Usa LEFT JOIN para mostrar instalaciones incluso si no tienen un cliente,
    promotor o instalador asignado. La seguridad se verifica en la tabla 'instalaciones'.
    """
    sql = """
        SELECT 
            i.id, 
            i.descripcion,
            d.localidad, 
            d.provincia,
            -- CTO: Añadimos los nombres para que la UI pueda mostrarlos o un texto por defecto
            c.nombre AS cliente_nombre,
            p.nombre_razon_social AS promotor_nombre,
            inst.nombre_empresa AS instalador_nombre
        FROM instalaciones i
        -- CTO: LA CORRECCIÓN CLAVE. Cambiamos a LEFT JOIN para no descartar instalaciones.
        LEFT JOIN clientes c ON i.cliente_id = c.id
        LEFT JOIN promotores p ON i.promotor_id = p.id
        LEFT JOIN instaladores inst ON i.instalador_id = inst.id
        LEFT JOIN direcciones d ON i.direccion_emplazamiento_id = d.id
        -- CTO: El filtro de seguridad ahora se aplica a la tabla principal 'instalaciones'.
        WHERE i.app_user_id = %s
    """
    
    params = [app_user_id]

    if ciudad:
        sql += " AND lower(d.localidad) LIKE %s"
        params.append(f"%{ciudad.lower()}%")

    sql += " ORDER BY i.id DESC"
    
    return _execute_select(conn, sql, tuple(params))

def get_instalacion_completa(conn, instalacion_id, app_user_id):
    """
    Obtiene TODOS los datos de una instalación específica, incluyendo los nuevos campos
    de cableado directamente, ya que la tabla de tramos ha sido eliminada.
    """
    # CTO: La consulta ahora es más simple. 'i.*' recogerá automáticamente los nuevos
    # campos de cableado (longitud_cable_dc_m, etc.) porque están en la tabla 'instalaciones'.
    sql_principal = """
        SELECT
            i.*,
            -- Datos del Cliente
            c.nombre AS cliente_nombre, c.apellidos AS cliente_apellidos, c.dni AS cliente_dni,
            c.email AS cliente_email, c.telefono_contacto AS cliente_telefono,
            -- Datos del Promotor
            p.nombre_razon_social AS promotor_nombre, p.dni_cif AS promotor_cif,
            p.email AS promotor_email, p.telefono_contacto AS promotor_telefono,
            -- Datos del Instalador
            inst.nombre_empresa AS instalador_empresa, inst.cif_empresa AS instalador_cif,
            inst.email AS instalador_email, inst.telefono_contacto AS instalador_telefono,
            inst.competencia AS instalador_competencia, inst.numero_colegiado_o_instalador, inst.numero_registro_industrial,
            -- Dirección de Emplazamiento (Completa)
            dir_emp.tipo_via_id AS emplazamiento_tipo_via_id,
            dir_emp.nombre_via AS emplazamiento_nombre_via,
            dir_emp.numero_via AS emplazamiento_numero_via,
            dir_emp.piso_puerta AS emplazamiento_piso_puerta,
            dir_emp.codigo_postal AS emplazamiento_codigo_postal,
            dir_emp.localidad AS emplazamiento_localidad,
            dir_emp.provincia AS emplazamiento_provincia,
            -- Hospital Cercano (Completo)
            h.nombre as hospital_nombre,
            dir_hosp.tipo_via_id as hospital_tipo_via_id,
            dir_hosp.nombre_via as hospital_nombre_via,
            dir_hosp.numero_via as hospital_numero_via,
            dir_hosp.piso_puerta as hospital_piso_puerta,
            dir_hosp.codigo_postal as hospital_codigo_postal,
            dir_hosp.localidad as hospital_localidad,
            dir_hosp.provincia as hospital_provincia,
            -- Nombres de Catálogos para los desplegables
            ps.nombre_panel AS panel_solar_nombre, inv.nombre_inversor AS inversor_nombre,
            b.nombre_bateria AS bateria_nombre, d.nombre_distribuidora AS distribuidora_nombre,
            ti.nombre as tipo_instalacion_nombre, tc.nombre as tipo_cubierta_nombre,
            tf.nombre_tipo_finca AS tipo_finca_nombre
        FROM instalaciones i
        LEFT JOIN clientes c ON i.cliente_id = c.id
        LEFT JOIN promotores p ON i.promotor_id = p.id
        LEFT JOIN instaladores inst ON i.instalador_id = inst.id
        LEFT JOIN direcciones dir_emp ON i.direccion_emplazamiento_id = dir_emp.id
        LEFT JOIN hospitales_cercanos h ON i.hospital_cercano_id = h.id
        LEFT JOIN direcciones dir_hosp ON h.direccion_id = dir_hosp.id
        LEFT JOIN paneles_solares ps ON i.panel_solar_id = ps.id
        LEFT JOIN inversores inv ON i.inversor_id = inv.id
        LEFT JOIN baterias b ON i.bateria_id = b.id
        LEFT JOIN distribuidoras d ON i.distribuidora_id = d.id
        LEFT JOIN tipos_finca tf ON i.tipo_finca_id = tf.id
        LEFT JOIN tipos_instalacion ti ON i.tipo_instalacion_id = ti.id
        LEFT JOIN tipos_cubierta tc ON i.tipo_cubierta_id = tc.id
        WHERE i.id = %s AND i.app_user_id = %s;
    """
    
    # CTO: La segunda consulta para los tramos ha sido ELIMINADA. La función ahora es más simple.
    instalacion_data = _execute_select(conn, sql_principal, (instalacion_id, app_user_id), one=True)
    
    return instalacion_data


# --- ESCRITURA ---
def add_instalacion(conn, data):
    dir_emplaz_data = data.get('direccion_emplazamiento', {})
    hospital_data = data.get('hospital_cercano', {})
    # CTO: La variable 'tramos_data' ha sido ELIMINADA.
    
    try:
        with conn: # Transacción automática
            with conn.cursor() as cursor:
                # Paso 1: Crear la dirección de emplazamiento (sin cambios)
                sql_dir_emp = "INSERT INTO direcciones (alias, tipo_via_id, nombre_via, numero_via, piso_puerta, codigo_postal, localidad, provincia) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;"
                cursor.execute(sql_dir_emp, ('Emplazamiento', dir_emplaz_data.get('tipo_via_id'), dir_emplaz_data.get('nombre_via'), dir_emplaz_data.get('numero_via'), dir_emplaz_data.get('piso_puerta'), dir_emplaz_data.get('codigo_postal'), dir_emplaz_data.get('localidad'), dir_emplaz_data.get('provincia')))
                direccion_emplazamiento_id = cursor.fetchone()['id']

                # Paso 2: Crear hospital y su dirección (si aplica, sin cambios)
                hospital_id = None
                if hospital_data and hospital_data.get('nombre'):
                    sql_dir_hosp = "INSERT INTO direcciones (alias, tipo_via_id, nombre_via, numero_via, piso_puerta, codigo_postal, localidad, provincia) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;"
                    cursor.execute(sql_dir_hosp, ('Hospital', hospital_data.get('tipo_via_id'), hospital_data.get('nombre_via'), hospital_data.get('numero_via'), hospital_data.get('piso_puerta'), hospital_data.get('codigo_postal'), hospital_data.get('localidad'), hospital_data.get('provincia')))
                    dir_hospital_id = cursor.fetchone()['id']
                    
                    sql_hosp = "INSERT INTO hospitales_cercanos (nombre, direccion_id) VALUES (%s, %s) RETURNING id;"
                    cursor.execute(sql_hosp, (hospital_data.get('nombre'), dir_hospital_id))
                    hospital_id = cursor.fetchone()['id']

                # Paso 3: Crear la instalación con los nuevos campos de cableado
                sql_instalacion = """
                    INSERT INTO instalaciones (
                        app_user_id, cliente_id, promotor_id, instalador_id, direccion_emplazamiento_id, tipo_finca_id,
                        panel_solar_id, inversor_id, bateria_id, distribuidora_id, tipo_instalacion_id, tipo_cubierta_id,
                        hospital_cercano_id, numero_pedido_presupuesto, descripcion, numero_paneles, numero_inversores,
                        numero_baterias, cups, potencia_contratada_w, referencia_catastral, protector_sobretensiones,
                        diferencial_a, sensibilidad_ma,
                        longitud_cable_dc_m, seccion_cable_dc_mm2, material_cable_dc,
                        longitud_cable_ac_m, seccion_cable_ac_mm2, material_cable_ac
                    ) VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s
                    ) RETURNING id;
                """
                params = (
                    data.get('app_user_id'), data.get('cliente_id'), data.get('promotor_id'), data.get('instalador_id'),
                    direccion_emplazamiento_id, data.get('tipo_finca_id'), data.get('panel_solar_id'),
                    data.get('inversor_id'), data.get('bateria_id'), data.get('distribuidora_id'),
                    data.get('tipo_instalacion_id'), data.get('tipo_cubierta_id'), hospital_id,
                    data.get('numero_pedido_presupuesto'), data.get('descripcion'), data.get('numero_paneles'),
                    data.get('numero_inversores'), data.get('numero_baterias'), data.get('cups'),
                    data.get('potencia_contratada_w'), data.get('referencia_catastral'),
                    data.get('protector_sobretensiones'), data.get('diferencial_a'), data.get('sensibilidad_ma'),
                    # CTO: Parámetros para los nuevos campos de cableado
                    data.get('longitud_cable_dc_m'), data.get('seccion_cable_dc_mm2'), data.get('material_cable_dc'),
                    data.get('longitud_cable_ac_m'), data.get('seccion_cable_ac_mm2'), data.get('material_cable_ac')
                )
                cursor.execute(sql_instalacion, params)
                instalacion_id = cursor.fetchone()['id']

                # CTO: El paso para insertar tramos de cableado ha sido ELIMINADO.

        logging.info(f"Instalación creada con éxito. ID: {instalacion_id}")
        return instalacion_id, "Instalación creada correctamente."
    except Exception as e:
        logging.error(f"Fallo en transacción de añadir instalación: {e}", exc_info=True)
        return None, f"Error en la base de datos: {e}"
    

def update_instalacion(conn, instalacion_id, app_user_id, data):
    """
    Actualiza una instalación existente y sus datos anidados (direcciones, hospital)
    de forma transaccional, segura y completa, usando la nueva estructura de cableado.
    """
    dir_emplaz_data = data.get('direccion_emplazamiento', {})
    hospital_data = data.get('hospital_cercano')

    try:
        with conn:
            with conn.cursor() as cursor:
                # CTO: PASO 1 - SEGURIDAD Y OBTENER ESTADO ACTUAL
                cursor.execute(
                    "SELECT direccion_emplazamiento_id, hospital_cercano_id FROM instalaciones WHERE id = %s AND app_user_id = %s",
                    (instalacion_id, app_user_id)
                )
                instalacion_actual = cursor.fetchone()
                if not instalacion_actual:
                    raise ValueError("Instalación no encontrada o acceso no autorizado.")

                # CTO: LA CORRECCIÓN CRÍTICA ESTÁ AQUÍ. DEFINIMOS LAS VARIABLES QUE FALTABAN.
                current_dir_emplaz_id = instalacion_actual['direccion_emplazamiento_id']
                current_hospital_id = instalacion_actual['hospital_cercano_id']
                
                # CTO: PASO 2 - ACTUALIZAR DIRECCIÓN DE EMPLAZAMIENTO
                if dir_emplaz_data and current_dir_emplaz_id:
                    sql_update_dir_emplaz = """
                        UPDATE direcciones SET tipo_via_id = %(tipo_via_id)s, nombre_via = %(nombre_via)s,
                        numero_via = %(numero_via)s, piso_puerta = %(piso_puerta)s, codigo_postal = %(codigo_postal)s,
                        localidad = %(localidad)s, provincia = %(provincia)s WHERE id = %(id)s;
                    """
                    dir_emplaz_data['id'] = current_dir_emplaz_id
                    cursor.execute(sql_update_dir_emplaz, dir_emplaz_data)

                # CTO: PASO 3 - LÓGICA COMPLETA PARA EL HOSPITAL CERCANO (Sin cambios, ya era correcta)
                new_hospital_id = current_hospital_id
                if hospital_data and hospital_data.get('nombre'):
                    if current_hospital_id:
                        cursor.execute("SELECT direccion_id FROM hospitales_cercanos WHERE id = %s", (current_hospital_id,))
                        dir_hospital_id = cursor.fetchone()['direccion_id']
                        sql_update_dir_hosp = "UPDATE direcciones SET tipo_via_id=%(tipo_via_id)s, nombre_via=%(nombre_via)s, localidad=%(localidad)s, provincia=%(provincia)s, codigo_postal=%(codigo_postal)s, piso_puerta=%(piso_puerta)s WHERE id=%(id)s;"
                        hospital_data['id'] = dir_hospital_id
                        cursor.execute(sql_update_dir_hosp, hospital_data)
                        cursor.execute("UPDATE hospitales_cercanos SET nombre = %s WHERE id = %s", (hospital_data['nombre'], current_hospital_id))
                    else:
                        sql_dir_hosp = "INSERT INTO direcciones (alias, tipo_via_id, nombre_via, localidad, provincia, codigo_postal, piso_puerta) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;"
                        cursor.execute(sql_dir_hosp, ('Hospital', hospital_data.get('tipo_via_id'), hospital_data.get('nombre_via'), hospital_data.get('localidad'), hospital_data.get('provincia'), hospital_data.get('codigo_postal'), hospital_data.get('piso_puerta')))
                        dir_hospital_id = cursor.fetchone()['id']
                        sql_hosp = "INSERT INTO hospitales_cercanos (nombre, direccion_id) VALUES (%s, %s) RETURNING id;"
                        cursor.execute(sql_hosp, (hospital_data['nombre'], dir_hospital_id))
                        new_hospital_id = cursor.fetchone()['id']
                elif current_hospital_id:
                    cursor.execute("SELECT direccion_id FROM hospitales_cercanos WHERE id = %s", (current_hospital_id,))
                    dir_hospital_id_to_delete = cursor.fetchone()['direccion_id']
                    cursor.execute("DELETE FROM hospitales_cercanos WHERE id = %s", (current_hospital_id,))
                    cursor.execute("DELETE FROM direcciones WHERE id = %s", (dir_hospital_id_to_delete,))
                    new_hospital_id = None
                
                # CTO: PASO 4 - ACTUALIZAR LA TABLA PRINCIPAL 'instalaciones'
                sql_update_instalacion = """
                    UPDATE instalaciones SET
                        cliente_id = %(cliente_id)s, promotor_id = %(promotor_id)s, instalador_id = %(instalador_id)s,
                        tipo_finca_id = %(tipo_finca_id)s, panel_solar_id = %(panel_solar_id)s, inversor_id = %(inversor_id)s,
                        bateria_id = %(bateria_id)s, distribuidora_id = %(distribuidora_id)s, descripcion = %(descripcion)s,
                        numero_paneles = %(numero_paneles)s, numero_inversores = %(numero_inversores)s,
                        numero_baterias = %(numero_baterias)s, cups = %(cups)s, potencia_contratada_w = %(potencia_contratada_w)s,
                        referencia_catastral = %(referencia_catastral)s, protector_sobretensiones = %(protector_sobretensiones)s,
                        diferencial_a = %(diferencial_a)s, sensibilidad_ma = %(sensibilidad_ma)s,
                        tipo_instalacion_id = %(tipo_instalacion_id)s, tipo_cubierta_id = %(tipo_cubierta_id)s,
                        numero_pedido_presupuesto = %(numero_pedido_presupuesto)s, hospital_cercano_id = %(hospital_cercano_id)s,
                        longitud_cable_dc_m = %(longitud_cable_dc_m)s, seccion_cable_dc_mm2 = %(seccion_cable_dc_mm2)s,
                        material_cable_dc = %(material_cable_dc)s, longitud_cable_ac_m = %(longitud_cable_ac_m)s,
                        seccion_cable_ac_mm2 = %(seccion_cable_ac_mm2)s, material_cable_ac = %(material_cable_ac)s
                    WHERE id = %(id)s AND app_user_id = %(app_user_id)s;
                """
                data['id'] = instalacion_id
                data['app_user_id'] = app_user_id
                data['hospital_cercano_id'] = new_hospital_id
                cursor.execute(sql_update_instalacion, data)

        return True, "Instalación actualizada correctamente."

    except ValueError as ve:
        logging.warning(f"Error de validación al actualizar instalación {instalacion_id}: {ve}")
        return False, str(ve)
    except Exception as e:
        logging.error(f"Fallo en transacción de actualizar instalación {instalacion_id}: {e}", exc_info=True)
        return False, f"Error en la base de datos: {e}"

def delete_instalacion(conn, instalacion_id, app_user_id):
    """
    Elimina una instalación y sus datos anidados (dirección, hospital) de forma segura.
    Ya no hace referencia a la tabla obsoleta de tramos de cableado.
    """
    try:
        with conn:
            with conn.cursor() as cursor:
                # Paso 1: Verificar propiedad y obtener IDs de las entidades anidadas
                cursor.execute(
                    "SELECT direccion_emplazamiento_id, hospital_cercano_id FROM instalaciones WHERE id = %s AND app_user_id = %s",
                    (instalacion_id, app_user_id)
                )
                result = cursor.fetchone()
                if not result:
                    raise ValueError("Instalación no encontrada o no autorizado para esta operación.")
                
                direccion_emplazamiento_id = result['direccion_emplazamiento_id']
                hospital_id = result['hospital_cercano_id']
                
                dir_hospital_id_to_delete = None
                if hospital_id:
                    cursor.execute("SELECT direccion_id FROM hospitales_cercanos WHERE id = %s", (hospital_id,))
                    res_hosp = cursor.fetchone()
                    if res_hosp:
                        dir_hospital_id_to_delete = res_hosp['direccion_id']

                # Paso 2: Eliminar la instalación.
                cursor.execute("DELETE FROM instalaciones WHERE id = %s", (instalacion_id,))
                
                # Paso 3: Eliminar el hospital y su dirección (si existían)
                if hospital_id:
                    cursor.execute("DELETE FROM hospitales_cercanos WHERE id = %s", (hospital_id,))
                if dir_hospital_id_to_delete:
                    cursor.execute("DELETE FROM direcciones WHERE id = %s", (dir_hospital_id_to_delete,))
                
                # Paso 4: Eliminar la dirección de emplazamiento
                if direccion_emplazamiento_id is not None:
                    cursor.execute("DELETE FROM direcciones WHERE id = %s", (direccion_emplazamiento_id,))

        logging.info(f"Instalación ID: {instalacion_id} y sus datos asociados eliminados correctamente.")
        return True, "Instalación eliminada correctamente."
    except Exception as e:
        logging.error(f"Fallo en la transacción de eliminar instalación: {e}", exc_info=True)
        return False, f"Error al eliminar la instalación: {e}"
    
