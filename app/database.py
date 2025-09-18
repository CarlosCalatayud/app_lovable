# app/database.py
import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor

def connect_db():
    """
    Se conecta a la base de datos PostgreSQL definida en la variable de entorno DATABASE_URL.
    """
    # --- LOGGING DE VERIFICACIÓN ---
    logging.info("--- INICIANDO CONEXIÓN A BASE DE DATOS ---")
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        logging.critical("FATAL: La variable de entorno DATABASE_URL NO está definida o es vacía.")
        raise ValueError("La configuración de la base de datos es incorrecta.")
    
    # Imprimimos la URL para saber exactamente qué está usando la aplicación.
    # Por seguridad, en un entorno real podríamos ofuscar la contraseña. Para depurar, la necesitamos.
    logging.info(f"Intentando conectar usando DATABASE_URL: {database_url}")
    # --- FIN DE LOGGING DE VERIFICACIÓN ---

    MAX_RETRIES = 3
    for attempt in range(MAX_RETRIES):
        
        logging.info("**************************************************************************************************.")
        logging.info("****************************************INTENTOOOOOOOO*********************************************.")
        logging.info("**************************************************************************************************.")
        try:
            conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
            logging.info("Conexión a la base de datos Supabase establecida con éxito.")
            return conn
        except psycopg2.OperationalError as e:
            logging.critical(f"FALLO DE CONEXIÓN con la URL proporcionada. Error: {e}", exc_info=True)
            raise

# La función is_postgres ya no es necesaria, la podemos eliminar.