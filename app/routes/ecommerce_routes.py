# app/routes/ecommerce_routes.py

from flask import Blueprint, jsonify
from app.auth import token_required
# Importamos nuestra nueva clase de servicio
from app.services.woocommerce_service import WooCommerceService

bp = Blueprint('ecommerce', __name__)

# Creamos una única instancia del servicio para reutilizar la conexión
wc_service = WooCommerceService()

@bp.route('/ecommerce/categories', methods=['GET'])
@token_required
def get_categories(conn):
    """Endpoint para obtener categorías, ahora con paginación opcional."""
    # CTO: Leemos los parámetros de la URL, con valores por defecto seguros.
    per_page = request.args.get('per_page', 100, type=int)
    page = request.args.get('page', 1, type=int)

    categories = wc_service.get_product_categories(per_page=per_page, page=page)
    
    if isinstance(categories, dict) and 'error' in categories:
        return jsonify(categories), 503
    
    return jsonify(categories)

@bp.route('/ecommerce/products/search', methods=['GET'])
@token_required
def search_products(conn):
    """Endpoint para buscar productos, ahora con paginación."""
    search_term = request.args.get('term', '')
    # CTO: Leemos los parámetros de paginación para la búsqueda.
    per_page = request.args.get('per_page', 20, type=int)
    page = request.args.get('page', 1, type=int)

    if not search_term:
        return jsonify({'error': 'El parámetro "term" es obligatorio.'}), 400

    products = wc_service.search_products(search_term, per_page=per_page, page=page)
    
    if isinstance(products, dict) and 'error' in products:
        return jsonify(products), 503
    
    return jsonify(products)
