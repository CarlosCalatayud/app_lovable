# app/models/base_model.py

import sqlite3
import psycopg2
import logging
from app.database import is_postgres

def _execute_select(conn, sql, params=None, one=False):
    db_type = 'postgres' if is_postgres(conn) else 'sqlite'
    sql = sql.replace('?', '%s' if db_type == 'postgres' else '?')
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params or ())
            return cursor.fetchone() if one else cursor.fetchall()
    except Exception as e:
        logging.error(f"Error en SELECT. SQL: {sql}, PARAMS: {params}. Error: {e}")
        return None if one else []

def _execute_insert(conn, sql, params):
    db_type = 'postgres' if is_postgres(conn) else 'sqlite'
    sql = sql.replace('?', '%s' if db_type == 'postgres' else '?')
    if db_type == 'postgres' and "RETURNING id" not in sql.upper():
        sql += " RETURNING id"

    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        new_id = cursor.fetchone()['id'] if db_type == 'postgres' else cursor.lastrowid
        conn.commit()
        logging.info(f"INSERT exitoso en tabla {sql.split(' ')[2]}. Nueva ID: {new_id}")
        return new_id, "Creado correctamente."
    except (psycopg2.IntegrityError, sqlite3.IntegrityError) as e:
        conn.rollback()
        logging.warning(f"Error de integridad en INSERT: {e}")
        return None, "Error de integridad: El registro ya existe o viola una restricción."
    except Exception as e:
        conn.rollback()
        logging.error(f"Error de BD en INSERT: {e}")
        return None, f"Error de base de datos: {e}"

def _execute_update_delete(conn, sql, params):
    db_type = 'postgres' if is_postgres(conn) else 'sqlite'
    sql = sql.replace('?', '%s' if db_type == 'postgres' else '?')
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rowcount = cursor.rowcount
        conn.commit()
        if rowcount == 0:
            return False, "Elemento no encontrado o los datos no cambiaron."
        return True, "Operación completada con éxito."
    except Exception as e:
        conn.rollback()
        logging.error(f"Error de BD en UPDATE/DELETE: {e}")
        return False, f"Error de base de datos: {e}"