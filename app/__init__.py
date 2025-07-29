# app/__init__.py

import os
import logging
from flask import Flask
from flask_cors import CORS

def create_app(test_config=None):
    """
    Application Factory: Crea y configura la instancia de la aplicación Flask.
    """
    app = Flask(__name__, instance_relative_config=True)
    
    # Configuración de CORS
    # Esto permite explícitamente el origen de preview de Lovable,
    # el Content-Type para JSON y la cabecera de Authorization.
    CORS(
        app,
        resources={r"/api/*": {"origins": "*"}}, # Permitir todos los orígenes por ahora
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], # Permitir todos los métodos comunes
        allow_headers=["Content-Type", "Authorization"] # Permitir las cabeceras necesarias
    )

    # Configuración de la aplicación desde variables de entorno o un objeto
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        TEMPLATES_PATH=os.path.join(app.root_path, '..', 'templates')
    )
    if test_config:
        app.config.from_mapping(test_config)
    
    # Configurar el logging
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')

    # El app_context es necesario para que los blueprints puedan registrarse
    with app.app_context():
        # --- Importar y Registrar Blueprints ---
        from .routes.core_routes import core_bp 
        from .routes.calculator_routes import bp as calculator_bp
        from .routes.catalog_routes import bp as catalog_bp
        from .routes.utility_routes import bp as utility_bp # <-- El nuevo
        from .routes import ecommerce_routes

        # Registrar los blueprints en la aplicación con sus prefijos de URL
        app.register_blueprint(core_bp, url_prefix='/api')
        app.register_blueprint(calculator_bp, url_prefix='/api/calculator')
        app.register_blueprint(catalog_bp, url_prefix='/api')
        app.register_blueprint(utility_bp, url_prefix='/') # Rutas de utilidad en la raíz
        app.register_blueprint(ecommerce_routes.bp, url_prefix='/api')
        
        logging.info("Aplicación creada y blueprints registrados.")

    return app