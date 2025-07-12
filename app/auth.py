# app/auth.py

import jwt
import os
from functools import wraps
from flask import request, jsonify, g, current_app
from . import db as database ### CTO: 1. Importamos nuestro módulo de base de datos.

def token_required(f):
    """
    Decorador definitivo para la autenticación.
    1. Valida el token JWT de Supabase de la cabecera Authorization.
    2. Extrae el user_id REAL del token.
    3. Abre, inyecta y cierra de forma segura la conexión a la BD.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        conn = None # Inicializamos la conexión a None

        try:
            # --- SECCIÓN 1: VALIDACIÓN DEL TOKEN (Lógica de Producción) ---
            
            auth_header = request.headers.get('Authorization')
            
            if not auth_header or not auth_header.startswith('Bearer '):
                current_app.logger.warning("Petición rechazada: Falta cabecera 'Authorization: Bearer ...'")
                return jsonify({'error': 'Cabecera de autorización Bearer requerida'}), 401
            
            token = auth_header.split(" ")[1]
            
            jwt_secret = os.environ.get('SUPABASE_JWT_SECRET')
            if not jwt_secret:
                current_app.logger.critical("¡FATAL! La variable de entorno SUPABASE_JWT_SECRET no está configurada.")
                return jsonify({'error': 'Error de configuración del servidor'}), 500

            try:
                data = jwt.decode(
                    token,
                    jwt_secret,
                    algorithms=["HS256"],
                    audience="authenticated"  # Valida que el token es para usuarios autenticados
                )
                
                # Esta es la línea más importante: el ID de usuario se extrae del token.
                # Ya no hay valores fijos.
                g.user_id = data['sub']
                current_app.logger.info(f"Token válido. Usuario autenticado: {g.user_id}")

            except jwt.ExpiredSignatureError:
                current_app.logger.warning(f"Intento de acceso con token expirado.")
                return jsonify({'error': 'El token ha expirado'}), 401
            except jwt.InvalidTokenError as e:
                current_app.logger.error(f"Token inválido: {e}")
                return jsonify({'error': 'Token inválido'}), 401

            # --- SECCIÓN 2: GESTIÓN DE LA CONEXIÓN Y EJECUCIÓN ---
            
            # Si llegamos aquí, el usuario está autenticado. Abrimos la conexión.
            conn = database.connect_db()
            
            # Inyectamos la conexión en el endpoint y lo ejecutamos.
            return f(conn, *args, **kwargs)

        except Exception as e:
            # Captura cualquier error inesperado que ocurra dentro del endpoint.
            current_app.logger.error(f"Excepción no controlada en la vista. Error: {e}", exc_info=True)
            # Nota: db.py ya se encarga del rollback, aquí solo devolvemos un error genérico.
            return jsonify({'error': 'Error interno del servidor'}), 500
        
        finally:
            # Este bloque se ejecuta SIEMPRE, garantizando que la conexión se cierre.
            if conn:
                conn.close()
                current_app.logger.info("Conexión a la base de datos cerrada por el decorador.")

    return decorated
