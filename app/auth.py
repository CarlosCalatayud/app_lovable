# app/auth.py

import jwt
import os
from functools import wraps
from flask import request, jsonify, g, current_app
from app import database

def db_connection_managed(f):
    """
    Decorador LIGERO para RUTAS PÚBLICAS.
    NO verifica token. Su única función es abrir, inyectar
    y cerrar de forma segura la conexión a la base de datos.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        conn = None
        try:
            conn = database.connect_db()
            return f(conn, *args, **kwargs) # Inyecta la conexión
        except Exception as e:
            current_app.logger.error(f"Excepción en ruta pública gestionada. Error: {e}", exc_info=True)
            return jsonify({'error': 'Error interno del servidor'}), 500
        finally:
            if conn:
                conn.close()
                current_app.logger.info("Conexión a la BD (pública) cerrada por el decorador.")
    return decorated


def token_required(f):
    """
    Decorador de SEGURIDAD para RUTAS PRIVADAS.
    Valida el token y gestiona la conexión a la BD.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        conn = None
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Cabecera de autorización Bearer requerida'}), 401
            
            token = auth_header.split(" ")[1]
            jwt_secret = os.environ.get('SUPABASE_JWT_SECRET')
            if not jwt_secret:
                current_app.logger.critical("¡FATAL! SUPABASE_JWT_SECRET no está configurada.")
                return jsonify({'error': 'Error de configuración del servidor'}), 500

            try:
                data = jwt.decode(token, jwt_secret, algorithms=["HS256"], audience="authenticated")
                g.user_id = data['sub']
            except jwt.ExpiredSignatureError:
                return jsonify({'error': 'El token ha expirado'}), 401
            except jwt.InvalidTokenError:
                return jsonify({'error': 'Token inválido'}), 401

            # Si el token es válido, gestionamos la conexión.
            conn = database.connect_db()
            return f(conn, *args, **kwargs)

        except Exception as e:
            current_app.logger.error(f"Excepción en ruta privada. Error: {e}", exc_info=True)
            return jsonify({'error': 'Error interno del servidor'}), 500
        finally:
            if conn:
                conn.close()
                current_app.logger.info("Conexión a la BD (privada) cerrada por el decorador.")

    return decorated
