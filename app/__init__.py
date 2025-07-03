# app/__init__.py
import os
from flask import Flask, jsonify

def create_app(test_config=None):
    # Crear e inicializar la app
    app = Flask(__name__, instance_relative_config=True)

    # --- CONFIGURACIÓN ---
    # Una clave secreta es necesaria para sesiones, etc. aunque no las uses explícitamente.
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'), # Usamos la variable de entorno
        # Define la ruta a la carpeta de plantillas
        TEMPLATES_PATH=os.path.join(app.root_path, '..', 'templates'),
            # # Define la ruta a la carpeta de salida (usaremos el disco persistente de Render)
            # OUTPUT_DOCS_PATH='/var/data/generated_docs' # Esta es la ruta estándar para Discos de Render
    )

    if test_config is None:
        # Sobrescribir con configuración de producción si existe
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Cargar configuración de prueba
        app.config.from_mapping(test_config)
    
    # comprobacion de si existe el directorio de salida y si se puede escribir en él
    # if os.environ.get("RENDER") and not os.access(app.config['OUTPUT_DOCS_PATH'], os.W_OK):
    #     app.logger.error(f"El directorio {app.config['OUTPUT_DOCS_PATH']} no existe o no se puede escribir en él.")
    # # Asegurarse de que la carpeta de salida exista en el disco de Render
    # # Esta ruta no existirá localmente, así que comprobamos si estamos en Render
    # if os.environ.get("RENDER"):
    #     try:
    #         os.makedirs(app.config['OUTPUT_DOCS_PATH'], exist_ok=True)
    #     except OSError as e:
    #         app.logger.error(f"Error al crear el directorio de salida en Render Disk: {e}")

    # --- REGISTRAR BLUEPRINTS ---
    from . import api_routes
    app.register_blueprint(api_routes.bp_api, url_prefix='/api')

    # Un endpoint de prueba para saber que la app funciona
    @app.route('/hello')
    def hello():
        return '¡Hola! La API está funcionando.'
    
        # #################################################################### #
    # --- INICIO DE SECCIÓN AÑADIDA: ENDPOINT DE SETUP DE LA BASE DE DATOS ---
    # #################################################################### #
    
    # Importa el módulo de la base de datos aquí dentro para evitar importaciones circulares
    from . import db

    @app.route('/setup-database/<path:secret_key>')
    def setup_database_endpoint(secret_key):
        # Compara la clave de la URL con la variable de entorno
        expected_key = os.environ.get('SETUP_SECRET_KEY')
        
        if not expected_key or secret_key != expected_key:
            return jsonify({"error": "Clave secreta no válida o no configurada."}), 403 # 403 Forbidden

        try:
            print("Iniciando setup de la base de datos...")
            db.create_tables()
            print("Tablas creadas. Poblando datos iniciales...")
            db.populate_initial_data()
            print("Setup de la base de datos completado.")
            return jsonify({"status": "success", "message": "Base de datos inicializada correctamente."}), 200
        except Exception as e:
            # Imprime el error en los logs de Render para depuración
            app.logger.error(f"Error durante el setup de la base de datos: {e}", exc_info=True)
            return jsonify({"status": "error", "message": f"Ocurrió un error: {e}"}), 500

    # #################################################################### #
    # --- FIN DE SECCIÓN AÑADIDA ---
    # #################################################################### #

    return app