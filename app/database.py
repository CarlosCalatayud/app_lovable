# app/database.py
import os
import logging
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

# Configuración
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("La variable de entorno DATABASE_URL no está definida.")

# Ajusta los límites según tu tráfico y el límite de Supabase (p.ej. 20-30 conexiones máx.)
MIN_CONN = 1
MAX_CONN = 48

# Crear el pool global al iniciar la app
try:
    logging.info(f"Inicializando pool de conexiones a DB con rango {MIN_CONN}-{MAX_CONN}...")
    connection_pool = pool.SimpleConnectionPool(
        MIN_CONN,
        MAX_CONN,
        dsn=DATABASE_URL,
        cursor_factory=RealDictCursor,
    )
    if connection_pool:
        logging.info("Pool de conexiones a la base de datos creado exitosamente.")
except Exception as e:
    logging.critical(f"No se pudo inicializar el pool de conexiones: {e}", exc_info=True)
    raise
def get_conn():
    """
    Obtiene una conexión del pool.
    """
    try:
        conn = connection_pool.getconn()
        if conn:
            return conn
    except Exception as e:
        logging.error(f"Error al obtener conexión del pool: {e}", exc_info=True)
        raise

def release_conn(conn):
    """
    Devuelve una conexión al pool.
    """
    try:
        if conn:
            connection_pool.putconn(conn)
    except Exception as e:
        logging.error(f"Error al devolver conexión al pool: {e}", exc_info=True)

def close_pool():
    """
    Cierra todas las conexiones del pool (p. ej., al apagar la app).
    """
    try:
        connection_pool.closeall()
        logging.info("Todas las conexiones del pool han sido cerradas.")
    except Exception as e:
        logging.error(f"Error al cerrar el pool de conexiones: {e}", exc_info=True)


# def connect_db():
#     """
#     Se conecta a la base de datos PostgreSQL definida en la variable de entorno DATABASE_URL.
#     """
#     # --- LOGGING DE VERIFICACIÓN ---
#     logging.info("--- INICIANDO CONEXIÓN A BASE DE DATOS ---")
#     database_url = os.environ.get('DATABASE_URL')
    
#     if not database_url:
#         logging.critical("FATAL: La variable de entorno DATABASE_URL NO está definida o es vacía.")
#         raise ValueError("La configuración de la base de datos es incorrecta.")
    
#     # Imprimimos la URL para saber exactamente qué está usando la aplicación.
#     # Por seguridad, en un entorno real podríamos ofuscar la contraseña. Para depurar, la necesitamos.
#     logging.info(f"Intentando conectar usando DATABASE_URL: {database_url}")
#     # --- FIN DE LOGGING DE VERIFICACIÓN ---

#     MAX_RETRIES = 3
#     for attempt in range(MAX_RETRIES):
        
#         logging.info("**************************************************************************************************.")
#         logging.info("****************************************INTENTOOOOOOOO*********************************************.")
#         logging.info("**************************************************************************************************.")
#         try:
#             conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
#             logging.info("Conexión a la base de datos Supabase establecida con éxito.")
#             return conn
#         except psycopg2.OperationalError as e:
#             logging.critical(f"FALLO DE CONEXIÓN con la URL proporcionada. Error: {e}", exc_info=True)
#             raise

# # La función is_postgres ya no es necesaria, la podemos eliminar.