# app/routes/utility_routes.py

import os
from flask import Blueprint, jsonify, current_app
# CTO: Importamos las funciones de setup desde su nueva ubicación
from app.database import create_tables, populate_initial_data

bp = Blueprint('utility', __name__)

@bp.route('/hello')
def hello():
    return '¡Hola! La API está funcionando.'

# --- ENDPOINTS SEGUROS PARA SETUP DE LA BASE DE DATOS ---

@bp.route('/setup/structure/<path:secret_key>')
def setup_database_structure_endpoint(secret_key):
    expected_key = os.environ.get('SETUP_SECRET_KEY')
    if not expected_key or secret_key != expected_key:
        return jsonify({"error": "Clave secreta no válida o no configurada."}), 403

    try:
        current_app.logger.info("--- Iniciando CREACIÓN DE TABLAS ---")
        create_tables()
        current_app.logger.info("--- CREACIÓN DE TABLAS completada ---")
        return jsonify({"status": "success", "message": "Estructura de la base de datos creada."}), 200
    except Exception as e:
        current_app.logger.error(f"Error durante la creación de tablas: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

@bp.route('/setup/data/<path:secret_key>')
def setup_database_data_endpoint(secret_key):
    expected_key = os.environ.get('SETUP_SECRET_KEY')
    if not expected_key or secret_key != expected_key:
        return jsonify({"error": "Clave secreta no válida o no configurada."}), 403

    try:
        current_app.logger.info("--- Iniciando POBLACIÓN DE DATOS ---")
        populate_initial_data()
        current_app.logger.info("--- POBLACIÓN DE DATOS completada ---")
        return jsonify({"status": "success", "message": "Datos iniciales insertados."}), 200
    except Exception as e:
        current_app.logger.error(f"Error durante la población de datos: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500