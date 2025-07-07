# app/auth.py
import jwt
import os
from functools import wraps
from flask import request, jsonify

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            # El token viene como "Bearer [token]"
            token = request.headers['Authorization'].split(" ")[1]

        if not token:
            return jsonify({'message': 'Falta el token de autenticación'}), 401

        try:
            # Decodifica el token usando el secreto
            jwt_secret = os.environ.get('SUPABASE_JWT_SECRET')
            data = jwt.decode(token, jwt_secret, algorithms=["HS256"])
            # Podrías guardar 'data' si lo necesitas, contiene el ID de usuario de Supabase
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'El token ha expirado'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token inválido'}), 401

        return f(*args, **kwargs)
    return decorated