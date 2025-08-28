# app/models/base_model.py

import logging
import psycopg2
# Ya no necesitamos sqlite3 porque solo usaremos PostgreSQL
# Ya no necesitamos importar is_postgres

def _execute_select(conn, sql, params=None, one=False):
    """
    Ejecuta una consulta SELECT en PostgreSQL.
    No es necesario reemplazar '?' por '%s' si siempre usamos %s en el SQL.
    """
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params or ())
            return cursor.fetchone() if one else cursor.fetchall()
    except Exception as e:
        logging.error(f"Error en SELECT. SQL: {sql}, PARAMS: {params}. Error: {e}", exc_info=True)
        # Re-lanzar el error para que sea manejado por el decorador de conexión
        raise

def _execute_insert(conn, sql, params):
    """
    Ejecuta una consulta INSERT en PostgreSQL y devuelve el ID.
    Asegura que la sentencia RETURNING id esté presente.
    """
    # Siempre usamos PostgreSQL, no hay necesidad de comprobar db_type
    # y si usas %(key)s en el SQL, tampoco necesitas reemplazar '?'
    if "RETURNING id" not in sql.upper():
        sql += " RETURNING id"

    try:
        with conn.cursor() as cursor: # Usamos with conn.cursor() para una mejor gestión de recursos
            cursor.execute(sql, params)
            new_id = cursor.fetchone()['id']
            # conn.commit() ya no es necesario aquí, el decorador lo gestiona si es necesario
            logging.info(f"INSERT exitoso en tabla {sql.split(' ')[2]}. Nueva ID: {new_id}")
            return new_id, "Creado correctamente."
    except psycopg2.IntegrityError as e:
        # conn.rollback() ya no es necesario aquí, el decorador lo gestiona si es necesario
        logging.warning(f"Error de integridad en INSERT: {e}", exc_info=True)
        raise # Re-lanzar para que el decorador o la ruta lo capturen con un rollback
    except Exception as e:
        # conn.rollback() ya no es necesario aquí
        logging.error(f"Error de BD en INSERT: {e}", exc_info=True)
        raise # Re-lanzar

def _execute_update_delete(conn, sql, params):
    """
    Ejecuta una consulta UPDATE o DELETE en PostgreSQL.
    """
    try:
        with conn.cursor() as cursor: # Usamos with conn.cursor()
            cursor.execute(sql, params)
            rowcount = cursor.rowcount
            # conn.commit() ya no es necesario aquí
            if rowcount == 0:
                return False, "Elemento no encontrado o los datos no cambiaron."
            return True, "Operación completada con éxito."
    except Exception as e:
        # conn.rollback() ya no es necesario aquí
        logging.error(f"Error de BD en UPDATE/DELETE: {e}", exc_info=True)
        raise # Re-lanzar