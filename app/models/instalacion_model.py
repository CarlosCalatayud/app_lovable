# app/models/instalacion_model.py

import logging
from .base_model import _execute_select

# --- LECTURA ---
def get_all_instalaciones(conn, app_user_id, ciudad=None): # CTO: Volvemos a añadir el parámetro opcional 'ciudad'
    """Obtiene un resumen de las instalaciones de un usuario, con filtrado opcional por ciudad."""
    
    # Parámetros para la consulta SQL. Empezamos con el app_user_id.
    params = [app_user_id]
    
    # La seguridad se basa en que la instalación DEBE pertenecer a un cliente del usuario.
    # Además, hemos añadido app_user_id directamente a la tabla de instalaciones para doble seguridad.
    sql = """
        SELECT i.id, i.descripcion, d.localidad, d.provincia, i.fecha_creacion
        FROM instalaciones i
        JOIN clientes c ON i.cliente_id = c.id
        LEFT JOIN direcciones d ON i.direccion_emplazamiento_id = d.id
        WHERE c.app_user_id = %s
    """

    # Si se proporciona un filtro de ciudad, lo añadimos a la consulta y a los parámetros.
    if ciudad:
        sql += " AND lower(d.localidad) LIKE %s"
        params.append(f"%{ciudad.lower()}%")

    sql += " ORDER BY i.fecha_creacion DESC"
    
    return _execute_select(conn, sql, tuple(params))

def get_instalacion_completa(conn, instalacion_id, app_user_id):
    # Esta es la consulta más grande. Une todas las piezas.
    sql = """
        SELECT 
            i.*,
            c.nombre as cliente_nombre, c.apellidos as cliente_apellidos,
            p.nombre_razon_social as promotor_nombre,
            inst.nombre_empresa as instalador_nombre,
            dir_emp.nombre_via as direccion_emplazamiento_via,
            ps.nombre_panel as panel_nombre,
            inv.nombre_inversor as inversor_nombre,
            b.nombre_bateria as bateria_nombre
        FROM instalaciones i
        JOIN clientes c ON i.cliente_id = c.id AND c.app_user_id = %s
        LEFT JOIN promotores p ON i.promotor_id = p.id
        LEFT JOIN instaladores inst ON i.instalador_id = inst.id
        LEFT JOIN direcciones dir_emp ON i.direccion_emplazamiento_id = dir_emp.id
        LEFT JOIN paneles_solares ps ON i.panel_solar_id = ps.id
        LEFT JOIN inversores inv ON i.inversor_id = inv.id
        LEFT JOIN baterias b ON i.bateria_id = b.id
        WHERE i.id = %s
    """
    return _execute_select(conn, sql, (app_user_id, instalacion_id), one=True)


# --- ESCRITURA ---
def add_instalacion(conn, data):
    """
    Añade una nueva instalación. Asume que ya se han creado la dirección, cliente, etc.,
    y que el frontend nos pasa sus IDs.
    """
    # También necesita su propia dirección de emplazamiento
    direccion_data = data.get('direccion_emplazamiento', {})
    
    try:
        with conn:
            with conn.cursor() as cursor:
                # Paso 1: Crear la dirección de emplazamiento
                sql_direccion = "INSERT INTO direcciones (...) VALUES (...) RETURNING id;"
                cursor.execute(sql_direccion, (...))
                direccion_emplazamiento_id = cursor.fetchone()['id']

                # Paso 2: Crear la instalación con todos los IDs
                sql_instalacion = """
                    INSERT INTO instalaciones (
                        cliente_id, promotor_id, instalador_id, direccion_emplazamiento_id,
                        tipo_finca_id, panel_solar_id, inversor_id, bateria_id, distribuidora_id,
                        ... otros campos ...
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, ...) RETURNING id;
                """
                params = (
                    data.get('cliente_id'), data.get('promotor_id'), data.get('instalador_id'),
                    direccion_emplazamiento_id, data.get('tipo_finca_id'), 
                    data.get('panel_solar_id'), data.get('inversor_id'),
                    data.get('bateria_id'), data.get('distribuidora_id'),
                    # ... otros valores ...
                )
                cursor.execute(sql_instalacion, params)
                instalacion_id = cursor.fetchone()['id']

                # Paso 3 (Avanzado): Insertar los tramos de cableado
                tramos_data = data.get('tramos_cableado', [])
                if tramos_data:
                    sql_tramos = "INSERT INTO tramos_cableado_instalacion (instalacion_id, tipo_cable_id, ...) VALUES (%s, %s, ...);"
                    for tramo in tramos_data:
                        cursor.execute(sql_tramos, (instalacion_id, tramo.get('tipo_cable_id'), ...))

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
