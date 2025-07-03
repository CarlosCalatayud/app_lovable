# app/__init__.py
import os
from flask import Flask

def create_app(test_config=None):
    # Crear e inicializar la app
    app = Flask(__name__, instance_relative_config=True)

    # --- CONFIGURACIÓN ---
    # Una clave secreta es necesaria para sesiones, etc. aunque no las uses explícitamente.
    app.config.from_mapping(
        SECRET_KEY='dev', # Cámbiala por un valor aleatorio en producción (usaremos variables de entorno)
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
    if os.environ.get("RENDER") and not os.access(app.config['OUTPUT_DOCS_PATH'], os.W_OK):
        app.logger.error(f"El directorio {app.config['OUTPUT_DOCS_PATH']} no existe o no se puede escribir en él.")
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

    return app