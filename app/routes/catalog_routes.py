# app/routes/catalog_routes.py

from flask import Blueprint, jsonify, current_app
from app.auth import db_connection_managed
# CTO: Importamos la función desde el nuevo modelo de catálogos
from app.models import catalog_model

bp = Blueprint('catalog', __name__)

# MAPA DE CATÁLOGOS UNIFICADO
CATALOG_TABLE_MAP = {
    "inversores": {"table": "inversores", "order_by": "nombre_inversor"},
    "paneles": {"table": "paneles_solares", "order_by": "nombre_panel"},
    "contadores": {"table": "contadores", "order_by": "nombre_contador"},
    "baterias": {"table": "baterias", "order_by": "nombre_bateria"},
    "tipos_vias": {"table": "tipos_vias", "order_by": "nombre_tipo_via"},
    "distribuidoras": {"table": "distribuidoras", "order_by": "nombre_distribuidora"},
    "categorias_instalador": {"table": "categorias_instalador", "order_by": "nombre_categoria"},
    "tipos_finca": {"table": "tipos_finca", "order_by": "nombre_tipo_finca"},
    "tipos_instalacion": {"table": "tipos_instalacion", "order_by": "nombre"},
    "tipos_cubierta": {"table": "tipos_cubierta", "order_by": "nombre"}

}

@bp.route('/catalogos/<string:catalog_name>', methods=['GET'])
@db_connection_managed
def get_catalog_data(conn, catalog_name):
    if catalog_name not in CATALOG_TABLE_MAP:
        return jsonify({'error': f'Catálogo no válido: {catalog_name}'}), 404

    config = CATALOG_TABLE_MAP[catalog_name]
    items = catalog_model.get_catalog_data(conn, config["table"], order_by_column=config["order_by"])
    
    current_app.logger.info(f"Obtenidos {len(items)} items para el catálogo público '{catalog_name}'.")
    return jsonify(items)