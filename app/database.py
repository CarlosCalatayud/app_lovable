# app/database.py

import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

def connect_db():
    """
    Se conecta a la base de datos (PostgreSQL en producción, SQLite en local).
    Esta es su única responsabilidad.
    """
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        try:
            conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
            logging.info("Conexión a PostgreSQL establecida con éxito.")
            return conn
        except psycopg2.OperationalError as e:
            logging.critical(f"FATAL: No se pudo conectar a PostgreSQL: {e}")
            raise
    else:
        # Modo de desarrollo local con un archivo de BD
        db_path = os.path.join(os.path.dirname(__file__), 'elecfacil_local.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        logging.info(f"Conexión a SQLite local establecida: {db_path}")
        return conn

def is_postgres(conn):
    """Función de ayuda para comprobar si la conexión es a PostgreSQL."""
    return hasattr(conn, 'get_backend_pid')