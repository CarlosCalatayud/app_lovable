# app/__init__.py
import os
from flask import Flask, jsonify
from flask_cors import CORS # Asegúrate de que esta importación está

def create_app(test_config=None):
    # Crear e inicializar la app
    app = Flask(__name__, instance_relative_config=True)
    
    # Aplicar CORS para permitir peticiones desde Lovable
    CORS(app)

    # --- CONFIGURACIÓN ---
    # Una clave secreta para la app de Flask y la ruta a las plantillas
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        TEMPLATES_PATH=os.path.join(app.root_path, '..', 'templates')
    )

    if test_config is not None:
        app.config.from_mapping(test_config)

    # --- REGISTRAR BLUEPRINTS (RUTAS PRINCIPALES) ---
    from . import api_routes
    app.register_blueprint(api_routes.bp_api, url_prefix='/api')

    # --- ENDPOINT DE SALUDO (PARA PRUEBAS) ---
    @app.route('/hello')
    def hello():
        return '¡Hola! La API está funcionando.'

    # --- ENDPOINTS SEGUROS PARA SETUP DE LA BASE DE DATOS ---
    
    # Importa el módulo de la base de datos aquí dentro
    from . import db

    # ENDPOINT 1: SOLO PARA CREAR LA ESTRUCTURA DE TABLAS
    @app.route('/setup-database-structure/<path:secret_key>')
    def setup_database_structure_endpoint(secret_key):
        # --- LÓGICA DE VERIFICACIÓN DE CLAVE SECRETA (RESTAURADA) ---
        expected_key = os.environ.get('SETUP_SECRET_KEY')
        if not expected_key or secret_key != expected_key:
            return jsonify({"error": "Clave secreta no válida o no configurada."}), 403
        # --- FIN DE LA LÓGICA DE VERIFICACIÓN ---

        try:
            print("--- Iniciando CREACIÓN DE TABLAS ---")
            db.create_tables()
            print("--- CREACIÓN DE TABLAS completada ---")
            return jsonify({"status": "success", "message": "Estructura de la base de datos creada correctamente."}), 200
        except Exception as e:
            app.logger.error(f"Error durante la creación de tablas: {e}", exc_info=True)
            return jsonify({"status": "error", "message": f"Ocurrió un error: {e}"}), 500

    # ENDPOINT 2: SOLO PARA POBLAR LOS DATOS DE CATÁLOGOS
    @app.route('/setup-database-data/<path:secret_key>')
    def setup_database_data_endpoint(secret_key):
        # --- LÓGICA DE VERIFICACIÓN DE CLAVE SECRETA (RESTAURADA) ---
        expected_key = os.environ.get('SETUP_SECRET_KEY')
        if not expected_key or secret_key != expected_key:
            return jsonify({"error": "Clave secreta no válida o no configurada."}), 403
        # --- FIN DE LA LÓGICA DE VERIFICACIÓN ---

        try:
            print("--- Iniciando POBLACIÓN DE DATOS ---")
            db.populate_initial_data()
            print("--- POBLACIÓN DE DATOS completada ---")
            return jsonify({"status": "success", "message": "Datos iniciales insertados correctamente."}), 200
        except Exception as e:
            app.logger.error(f"Error durante la población de datos: {e}", exc_info=True)
            return jsonify({"status": "error", "message": f"Ocurrió un error: {e}"}), 500

    return app