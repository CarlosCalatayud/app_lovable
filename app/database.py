# app/database.py
import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor

def connect_db():
    """
    Se conecta a la base de datos PostgreSQL definida en la variable de entorno DATABASE_URL.
    Esta es ahora su única responsabilidad.
    """
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logging.critical("FATAL: La variable de entorno DATABASE_URL no está definida.")
        raise ValueError("La configuración de la base de datos es incorrecta.")
    
    try:
        # psycopg2 sabe cómo manejar directamente la URL de conexión completa.
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        logging.info("Conexión a la base de datos Supabase establecida con éxito.")
        return conn
    except psycopg2.OperationalError as e:
        logging.critical(f"FATAL: No se pudo conectar a la base de datos de Supabase: {e}", exc_info=True)
        raise

# La función is_postgres ya no es necesaria, la podemos eliminar.