# app/auth.py
import jwt
import os
from functools import wraps
from flask import request, jsonify, g, current_app

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
                # --- MODO DE DEPURACIÓN (BYPASS DE AUTENTICACIÓN) ---
        # Comprueba si la variable de entorno para desactivar la auth está activada
        if os.environ.get('DISABLE_AUTH') == 'true':
            current_app.logger.warning("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            current_app.logger.warning("!!! ADVERTENCIA: LA AUTENTICACIÓN ESTÁ DESACTIVADA !!!")
            current_app.logger.warning("!!! USANDO ID DE USUARIO DE PRUEBA FIJO. !!!")
            current_app.logger.warning("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            
            # Asigna un ID de usuario fijo para todas las peticiones
            g.user_id = "7978ca1c-503d-4550-8d04-3aa01d9113ba" # <-- USA TU PROPIO ID DE USUARIO DE SUPABASE AQUÍ
            
            # Llama directamente a la función del endpoint sin verificar token
            return f(*args, **kwargs)
        # --- FIN DEL MODO DE DEPURACIÓN ---


        token = None
        auth_header = request.headers.get('Authorization')
        
        # --- LOGGING DE DEPURACIÓN DETALLADO ---
        current_app.logger.info("--- DEPURANDO @token_required ---")
        if not auth_header:
            current_app.logger.error("No se encontró la cabecera 'Authorization'.")
            return jsonify({'message': 'Falta la cabecera de autorización'}), 401
        
        current_app.logger.info(f"Cabecera 'Authorization' recibida: {auth_header}")
        
        parts = auth_header.split()

        if parts[0].lower() != 'bearer':
            current_app.logger.error("La cabecera 'Authorization' no empieza con 'Bearer'.")
            return jsonify({'message': 'Cabecera de autorización mal formada'}), 401
        elif len(parts) == 1:
            current_app.logger.error("El token está ausente después de 'Bearer'.")
            return jsonify({'message': 'Token no encontrado'}), 401
        elif len(parts) > 2:
            current_app.logger.error("La cabecera 'Authorization' contiene demasiadas partes.")
            return jsonify({'message': 'Cabecera de autorización mal formada'}), 401
        
        token = parts[1]
        current_app.logger.info(f"Token extraído para verificación: {token}")
        # --- FIN DEL LOGGING ---

        if not token:
            return jsonify({'message': 'Falta el token de autenticación'}), 401

        try:
            jwt_secret = os.environ.get('SUPABASE_JWT_SECRET')
            if not jwt_secret:
                current_app.logger.critical("¡LA VARIABLE DE ENTORNO SUPABASE_JWT_SECRET NO ESTÁ CONFIGURADA EN RENDER!")
                return jsonify({'message': 'Error de configuración del servidor'}), 500

            # Decodifica el token usando el secreto y el algoritmo correcto
            data = jwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"],
                audience="authenticated"  # <-- AÑADIMOS ESTA LÍNEA
            )
            app_user_id_fijo = "7978ca1c-503d-4550-8d04-3aa01d9113ba" # Tu ID de usuario de Supabase 
            g.user_id = app_user_id_fijo
            #data['sub']

        except jwt.ExpiredSignatureError:
            current_app.logger.warning("Intento de uso de un token expirado.")
            return jsonify({'message': 'El token ha expirado'}), 401
        except Exception as e:
            # Capturamos cualquier otro error de JWT y lo logueamos
            current_app.logger.error(f"Error al decodificar el token: {e}")
            return jsonify({'message': 'Token inválido'}), 401

        return f(*args, **kwargs)
    return decorated