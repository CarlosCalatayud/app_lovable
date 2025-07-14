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
    """
    Añade un cliente y su dirección en una única transacción.
    'data' debe ser un diccionario que contenga una sub-clave 'direccion'.
    """
    direccion_data = data.get('direccion', {})
    direccion_id = None

    try:
        # CTO: 'with conn:' en Psycopg2 inicia una transacción. Si hay un error, se hace rollback automáticamente.
        with conn.cursor() as cursor:
            # Paso 1: Crear la dirección primero para obtener su ID.
            sql_direccion = """
                INSERT INTO direcciones (alias, tipo_via_id, nombre_via, numero_via, piso_puerta, codigo_postal, localidad, provincia)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
            """
            cursor.execute(sql_direccion, (
                direccion_data.get('alias', 'Dirección Principal'),
                direccion_data.get('tipo_via_id'),
                direccion_data.get('nombre_via'),
                direccion_data.get('numero_via'),
                direccion_data.get('piso_puerta'),
                direccion_data.get('codigo_postal'),
                direccion_data.get('localidad'),
                direccion_data.get('provincia')
            ))
            # Obtenemos el ID de la dirección recién creada
            direccion_id = cursor.fetchone()['id']
            
            # Paso 2: Crear el cliente usando el ID de la dirección.
            sql_cliente = """
                INSERT INTO clientes (app_user_id, nombre, apellidos, dni, direccion_id)
                VALUES (%s, %s, %s, %s, %s) RETURNING id;
            """
            cursor.execute(sql_cliente, (
                data['app_user_id'],
                data.get('nombre'),
                data.get('apellidos'),
                data.get('dni'),
                direccion_id  # Usamos el ID que obtuvimos en el paso anterior
            ))
            cliente_id = cursor.fetchone()['id']

        # Si el bloque 'with' termina sin errores, Psycopg2 hace commit automáticamente.
        logging.info(f"Éxito transaccional. Cliente creado ID: {cliente_id}, Dirección ID: {direccion_id}")
        return cliente_id, "Cliente creado correctamente."

    except Exception as e:
        # El rollback es automático. Solo necesitamos registrar el error.
        logging.error(f"Fallo en la transacción de añadir cliente: {e}")
        return None, f"Error en la base de datos: {e}"

def update_cliente(conn, cliente_id, app_user_id, data):
    """
    Actualiza un cliente y su dirección asociada en una única transacción.
    """
    direccion_data = data.get('direccion', {})
    
    try:
        with conn.cursor() as cursor:
            # Primero, necesitamos el direccion_id del cliente que vamos a actualizar.
            # Esto también verifica que el cliente pertenece al usuario (seguridad).
            cursor.execute(
                "SELECT direccion_id FROM clientes WHERE id = %s AND app_user_id = %s",
                (cliente_id, app_user_id)
            )
            result = cursor.fetchone()
            if not result:
                # Si no hay resultado, el cliente no existe o no pertenece al usuario.
                raise ValueError("Cliente no encontrado o no autorizado para esta operación.")
            
            direccion_id = result['direccion_id']

            # Paso 1: Actualizar la dirección existente si se proporcionan datos de dirección.
            if direccion_data and direccion_id is not None:
                sql_update_direccion = """
                    UPDATE direcciones SET
                        alias = %s, tipo_via_id = %s, nombre_via = %s, numero_via = %s,
                        piso_puerta = %s, codigo_postal = %s, localidad = %s, provincia = %s
                    WHERE id = %s;
                """
                cursor.execute(sql_update_direccion, (
                    direccion_data.get('alias'), direccion_data.get('tipo_via_id'),
                    direccion_data.get('nombre_via'), direccion_data.get('numero_via'),
                    direccion_data.get('piso_puerta'), direccion_data.get('codigo_postal'),
                    direccion_data.get('localidad'), direccion_data.get('provincia'),
                    direccion_id
                ))

            # Paso 2: Actualizar los datos del cliente.
            sql_update_cliente = """
                UPDATE clientes SET
                    nombre = %s, apellidos = %s, dni = %s
                WHERE id = %s;
            """
            cursor.execute(sql_update_cliente, (
                data.get('nombre'), data.get('apellidos'), data.get('dni'),
                cliente_id
            ))
        
        # El bloque 'with' se encarga del commit al salir sin errores.
        logging.info(f"Cliente ID: {cliente_id} y Dirección ID: {direccion_id} actualizados.")
        return True, "Cliente actualizado correctamente."

    except Exception as e:
        # El rollback es automático.
        logging.error(f"Fallo en la transacción de actualizar cliente: {e}")
        return False, f"Error al actualizar el cliente: {e}"

def delete_cliente(conn, cliente_id, app_user_id):
    """
    Elimina un cliente y su dirección asociada en una única transacción.
    """
    try:
        with conn.cursor() as cursor:
            # Paso 1: Obtener el direccion_id antes de borrar, y verificar la propiedad.
            cursor.execute(
                "SELECT direccion_id FROM clientes WHERE id = %s AND app_user_id = %s",
                (cliente_id, app_user_id)
            )
            result = cursor.fetchone()
            if not result:
                raise ValueError("Cliente no encontrado o no autorizado para esta operación.")
            
            direccion_id = result['direccion_id']

            # Paso 2: Eliminar al cliente. La base de datos (con ON DELETE SET NULL) podría manejar esto,
            # pero ser explícitos nos da más control.
            cursor.execute("DELETE FROM clientes WHERE id = %s", (cliente_id,))
            
            # Paso 3: Eliminar la dirección asociada, si existe.
            if direccion_id is not None:
                # Opcional: Podrías añadir lógica aquí para comprobar si otra entidad usa esta misma dirección.
                # Por ahora, la eliminamos directamente.
                cursor.execute("DELETE FROM direcciones WHERE id = %s", (direccion_id,))

        # Commit automático al salir del bloque 'with'.
        logging.info(f"Cliente ID: {cliente_id} y su Dirección ID: {direccion_id} eliminados.")
        return True, "Cliente eliminado correctamente."

    except Exception as e:
        logging.error(f"Fallo en la transacción de eliminar cliente: {e}")
        return False, f"Error al eliminar el cliente: {e}"
