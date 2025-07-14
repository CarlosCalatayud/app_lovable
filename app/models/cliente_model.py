# app/models/cliente_model.py
import logging
from .base_model import _execute_select, _execute_insert, _execute_update_delete

# --- LECTURA (ahora requiere un JOIN para ser útil) ---
def get_all_clientes(conn, app_user_id):
    """Obtiene todos los clientes de un usuario, incluyendo su dirección principal."""
    # CTO: Usamos LEFT JOIN para que si un cliente no tiene dirección, aún aparezca en la lista.
    sql = """
        SELECT c.id, c.nombre, c.apellidos, c.dni, d.alias as direccion_alias
        FROM clientes c
        LEFT JOIN direcciones d ON c.direccion_id = d.id
        WHERE c.app_user_id = %s
        ORDER BY c.nombre, c.apellidos
    """
    return _execute_select(conn, sql, (app_user_id,))

def get_cliente_by_id(conn, cliente_id, app_user_id):
    """Obtiene los detalles completos de un cliente, incluyendo su dirección."""
    sql = """
        SELECT 
            c.id, c.nombre, c.apellidos, c.dni,
            d.id as direccion_id, d.alias, d.tipo_via_id, tv.nombre_tipo_via,
            d.nombre_via, d.numero_via, d.piso_puerta, d.codigo_postal,
            d.localidad, d.provincia
        FROM clientes c
        LEFT JOIN direcciones d ON c.direccion_id = d.id
        LEFT JOIN tipos_vias tv ON d.tipo_via_id = tv.id
        WHERE c.id = %s AND c.app_user_id = %s
    """
    return _execute_select(conn, sql, (cliente_id, app_user_id), one=True)

# --- ESCRITURA (ahora es una transacción) ---
def add_cliente(conn, data):
    direccion_data = data.get('direccion', {})
    try:
        # CTO: LA CORRECCIÓN CLAVE. `with conn:` inicia una transacción y
        # hace COMMIT automáticamente si el bloque termina sin errores,
        # o ROLLBACK si ocurre una excepción.
        with conn:
            with conn.cursor() as cursor:
                # Paso 1: Crear la dirección
                sql_direccion = "INSERT INTO direcciones (alias, tipo_via_id, nombre_via, numero_via, piso_puerta, codigo_postal, localidad, provincia) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;"
                cursor.execute(sql_direccion, (direccion_data.get('alias', 'Dirección Principal'), direccion_data.get('tipo_via_id'), direccion_data.get('nombre_via'), direccion_data.get('numero_via'), direccion_data.get('piso_puerta'), direccion_data.get('codigo_postal'), direccion_data.get('localidad'), direccion_data.get('provincia')))
                direccion_id = cursor.fetchone()['id']
                
                # Paso 2: Crear el cliente
                sql_cliente = "INSERT INTO clientes (app_user_id, nombre, apellidos, dni, direccion_id) VALUES (%s, %s, %s, %s, %s) RETURNING id;"
                cursor.execute(sql_cliente, (data['app_user_id'], data.get('nombre'), data.get('apellidos'), data.get('dni'), direccion_id))
                cliente_id = cursor.fetchone()['id']

        logging.info(f"Éxito transaccional y COMMIT realizado. Cliente ID: {cliente_id}")
        return cliente_id, "Cliente creado correctamente."
    except Exception as e:
        # El rollback es automático gracias a 'with conn:'.
        logging.error(f"Fallo en transacción de añadir cliente (ROLLBACK automático): {e}")
        return None, f"Error en la base de datos: {e}"

def update_cliente(conn, cliente_id, app_user_id, data):
    direccion_data = data.get('direccion', {})
    try:
        with conn: # Usamos la misma estructura transaccional
            with conn.cursor() as cursor:
                cursor.execute("SELECT direccion_id FROM clientes WHERE id = %s AND app_user_id = %s", (cliente_id, app_user_id))
                result = cursor.fetchone()
                if not result: raise ValueError("Cliente no encontrado o no autorizado.")
                
                direccion_id = result['direccion_id']
                if direccion_data and direccion_id is not None:
                    sql_update_direccion = "UPDATE direcciones SET alias = %s, tipo_via_id = %s, nombre_via = %s, numero_via = %s, piso_puerta = %s, codigo_postal = %s, localidad = %s, provincia = %s WHERE id = %s;"
                    cursor.execute(sql_update_direccion, (direccion_data.get('alias'), direccion_data.get('tipo_via_id'), direccion_data.get('nombre_via'), direccion_data.get('numero_via'), direccion_data.get('piso_puerta'), direccion_data.get('codigo_postal'), direccion_data.get('localidad'), direccion_data.get('provincia'), direccion_id))
                
                sql_update_cliente = "UPDATE clientes SET nombre = %s, apellidos = %s, dni = %s WHERE id = %s;"
                cursor.execute(sql_update_cliente, (data.get('nombre'), data.get('apellidos'), data.get('dni'), cliente_id))
        logging.info(f"Cliente ID: {cliente_id} actualizado y COMMIT realizado.")
        return True, "Cliente actualizado correctamente."
    except Exception as e:
        logging.error(f"Fallo en transacción de actualizar cliente (ROLLBACK automático): {e}")
        return False, f"Error al actualizar el cliente: {e}"

def delete_cliente(conn, cliente_id, app_user_id):
    try:
        with conn: # Y de nuevo, la misma estructura transaccional
            with conn.cursor() as cursor:
                cursor.execute("SELECT direccion_id FROM clientes WHERE id = %s AND app_user_id = %s", (cliente_id, app_user_id))
                result = cursor.fetchone()
                if not result: raise ValueError("Cliente no encontrado o no autorizado.")
                
                direccion_id = result['direccion_id']
                cursor.execute("DELETE FROM clientes WHERE id = %s", (cliente_id,))
                if direccion_id is not None:
                    cursor.execute("DELETE FROM direcciones WHERE id = %s", (direccion_id,))
        logging.info(f"Cliente ID: {cliente_id} eliminado y COMMIT realizado.")
        return True, "Cliente eliminado correctamente."
    except Exception as e:
        logging.error(f"Fallo en transacción de eliminar cliente (ROLLBACK automático): {e}")
        return False, f"Error al eliminar el cliente: {e}"
