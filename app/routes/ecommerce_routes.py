# app/routes/ecommerce_routes.py

from flask import Blueprint, jsonify
from app.auth import token_required
# Importamos nuestra nueva clase de servicio
from app.services.woocommerce_service import WooCommerceService

bp = Blueprint('ecommerce', __name__)

# Creamos una única instancia del servicio para reutilizar la conexión
wc_service = WooCommerceService()

@bp.route('/ecommerce/categories', methods=['GET'])
@token_required # Protegemos el endpoint, solo usuarios logueados pueden verlo
def get_categories(conn): # 'conn' es inyectado por el decorador, aunque no lo usemos aquí
    """
    Endpoint para obtener la lista de categorías de productos de WooCommerce.
    """
    categories = wc_service.get_product_categories()
    
    # Si hubo un error en el servicio, lo devolvemos con un código de error apropiado
    if isinstance(categories, dict) and 'error' in categories:
        return jsonify(categories), 503 # 503 Service Unavailable es apropiado aquí
    
    return jsonify(categories)


@bp.route('/ecommerce/products/search', methods=['GET'])
@token_required
def search_products(conn):
    """
    Endpoint para buscar productos en WooCommerce.
    Espera un parámetro de consulta, ej: /search?term=panel
    """
    # Obtenemos el término de búsqueda de los parámetros de la URL
    search_term = request.args.get('term', '')

    # Validamos que el término de búsqueda no esté vacío
    if not search_term:
        return jsonify({'error': 'El parámetro "term" es obligatorio.'}), 400

    products = wc_service.search_products(search_term)
    
    if isinstance(products, dict) and 'error' in products:
        return jsonify(products), 503
    
    return jsonify(products)
