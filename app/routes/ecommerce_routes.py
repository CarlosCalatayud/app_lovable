# app/routes/ecommerce_routes.py

from flask import Blueprint, jsonify, request
from app.auth import token_required
# Importamos nuestra nueva clase de servicio
from app.services.woocommerce_service import WooCommerceService

bp = Blueprint('ecommerce', __name__)

# Creamos una única instancia del servicio para reutilizar la conexión
wc_service = WooCommerceService()

@bp.route('/ecommerce/categories', methods=['GET'])
@token_required
def get_categories(conn):
    """
    Obtiene categorías. Acepta un parámetro opcional 'parent_id' para subcategorías.
    Ej: /ecommerce/categories?parent_id=15
    """
    parent_id = request.args.get('parent_id', 0, type=int)
    categories = wc_service.get_product_categories(parent_id=parent_id)
    
    if isinstance(categories, dict) and 'error' in categories:
        return jsonify(categories), 503
    
    return jsonify(categories)

@bp.route('/ecommerce/categories/<int:category_id>/products', methods=['GET'])
@token_required
def get_products_by_category_route(conn, category_id):
    """
    Nuevo endpoint para obtener productos de una categoría específica, con paginación.
    Ejemplo de uso: /api/ecommerce/categories/15/products?page=1&per_page=10
    """
    # Leemos los parámetros de la URL para la paginación, con valores por defecto.
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # Llamamos a nuestro nuevo método del servicio.
    products = wc_service.get_products_by_category(category_id, per_page=per_page, page=page)
    
    # Manejo de errores estándar.
    if isinstance(products, dict) and 'error' in products:
        return jsonify(products), 503
    
    return jsonify(products)

@bp.route('/ecommerce/products/<int:product_id>', methods=['GET'])
@token_required
def get_product_detail(conn, product_id):
    """
    Endpoint para obtener los detalles completos de un producto, con el precio de los 'bundles' calculado.
    """
    # CTO: Llamamos a la nueva función del servicio que hace la magia.
    product = wc_service.get_product_with_calculated_price(product_id)
    
    if isinstance(product, dict) and 'error' in product:
        status_code = 404 if "Producto no encontrado" in product.get('error', '') else 503
        return jsonify(product), status_code
    
    return jsonify(product)


@bp.route('/ecommerce/products/search', methods=['GET'])
@token_required
def search_products(conn):
    """
    Endpoint para buscar productos. Acepta 'term' y parámetros opcionales
    de paginación ('page', 'per_page') y filtrado por categoría ('category_id').
    Ej: /search?term=panel&category_id=15
    """
    # Obtenemos todos los parámetros de la URL
    search_term = request.args.get('term', '')
    category_id = request.args.get('category_id', None, type=int) # Nuevo parámetro opcional
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    if not search_term:
        return jsonify({'error': 'El parámetro "term" es obligatorio.'}), 400

    # Pasamos todos los parámetros a nuestra nueva y potente función de servicio
    products = wc_service.search_products(
        search_term, 
        category_id=category_id, 
        page=page, 
        per_page=per_page
    )
    
    if isinstance(products, dict) and 'error' in products:
        return jsonify(products), 503
    
    return jsonify(products)
