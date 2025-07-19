# app/services/woocommerce_service.py

import os
from woocommerce import API
import logging

class WooCommerceService:
    """
    Servicio para encapsular toda la comunicación con la API de WooCommerce.
    """
    def __init__(self):
        self.wcapi = None
        # Comprobamos que las claves existen para evitar errores al iniciar
        consumer_key = os.getenv("WC_KEY")
        consumer_secret = os.getenv("WC_SECRET")

        if not all([consumer_key, consumer_secret]):
            logging.error("Las variables de entorno de WooCommerce (WC_KEY, WC_SECRET) no están configuradas.")
            # Dejamos self.wcapi como None para que los métodos fallen de forma controlada
            return

        try:
            self.wcapi = API(
                url="https://cuencasolar.es/",  # La URL de tu tienda
                consumer_key=consumer_key,
                consumer_secret=consumer_secret,
                version="wc/v3",
                timeout=10 # Añadimos un timeout para evitar que la app se cuelgue
            )
            logging.info("Servicio de WooCommerce inicializado con éxito.")
        except Exception as e:
            logging.error(f"Error al inicializar la API de WooCommerce: {e}")

    def get_product_categories(self, parent_id=0):
        """
        Obtiene categorías. Si parent_id es 0, trae las de nivel superior.
        Si se especifica un parent_id, trae las subcategorías de esa categoría.
        """
        if not self.wcapi:
            return {"error": "El servicio de WooCommerce no está configurado correctamente."}
        
        params = {
            'per_page': 100,
            'parent': parent_id, # Parámetro clave para obtener categorías padre o hijas
            'orderby': 'name',
            'order': 'asc'
        }

        try:
            response = self.wcapi.get("products/categories", params=params)
            if response.status_code == 200:
                return response.json()
            else:
                logging.error(f"Error al obtener categorías de WooCommerce: {response.status_code} {response.text}")
                return {"error": f"Respuesta inesperada de WooCommerce: {response.status_code}"}
        except Exception as e:
            logging.error(f"Excepción al contactar con WooCommerce para obtener categorías: {e}")
            return {"error": "No se pudo conectar con la tienda de WooCommerce."}

    def get_products_by_category(self, category_id, per_page=20, page=1):
        """
        Obtiene una lista de productos de una categoría específica, con paginación y campos optimizados.
        """
        if not self.wcapi:
            return {"error": "El servicio de WooCommerce no está configurado correctamente."}
            
        params = {
            'category': str(category_id), # El ID de la categoría a filtrar
            'per_page': per_page,
            'page': page,
            'status': 'publish', # Solo productos publicados y visibles
            # Pedimos solo los datos que necesitamos para la vista de lista, para que sea súper rápido
            '_fields': 'id,name,price,stock_status,images,permalink,short_description,average_rating' 
        }
        
        try:
            response = self.wcapi.get("products", params=params)
            if response.status_code == 200:
                return response.json()
            else:
                logging.error(f"Error al obtener productos por categoría ({category_id}) de WooCommerce: {response.status_code} {response.text}")
                return {"error": f"Respuesta inesperada de WooCommerce: {response.status_code}"}
        except Exception as e:
            logging.error(f"Excepción al contactar con WooCommerce para obtener productos por categoría ({category_id}): {e}")
            return {"error": "No se pudo conectar con la tienda de WooCommerce."}

    def get_product_by_id(self, product_id):
        """Obtiene todos los detalles de un único producto por su ID."""
        if not self.wcapi:
            return {"error": "El servicio de WooCommerce no está configurado correctamente."}
        
        try:
            # Pedimos toda la información porque es para la vista de detalle
            response = self.wcapi.get(f"products/{product_id}")
            if response.status_code == 200:
                return response.json()
            else:
                logging.error(f"Error al obtener el producto {product_id} de WooCommerce: {response.status_code} {response.text}")
                return {"error": f"Producto no encontrado o error en WooCommerce: {response.status_code}"}
        except Exception as e:
            logging.error(f"Excepción al contactar con WooCommerce para obtener el producto {product_id}: {e}")
            return {"error": "No se pudo conectar con la tienda de WooCommerce."}

    # CTO: PASO 2 - LA FUNCIÓN DE AYUDA RECURSIVA (YA ERA CORRECTA)
    def _calculate_bundle_price(self, product_data):
        """Función recursiva para calcular el precio total de un producto 'bundle'."""
        total_price = 0.0
        if 'bundled_items' in product_data and product_data['bundled_items']:
            for item in product_data['bundled_items']:
                item_id = item['product_id']
                item_quantity = int(item.get('quantity_default', 1))
                
                sub_product_data = self.get_product_by_id(item_id)
                
                if sub_product_data and 'error' not in sub_product_data:
                    sub_product_price = 0.0
                    if sub_product_data.get('type') == 'bundle':
                        sub_product_price = self._calculate_bundle_price(sub_product_data)
                    else:
                        sub_product_price = float(sub_product_data.get('price', 0))
                    
                    total_price += sub_product_price * item_quantity
        return total_price

    # CTO: PASO 3 - LA FUNCIÓN INTELIGENTE QUE USA LAS OTRAS DOS (YA ERA CORRECTA)
    def get_product_with_calculated_price(self, product_id):
        """
        Obtiene los detalles de un producto y calcula el precio de los 'bundles'.
        """
        product_data = self.get_product_by_id(product_id)
        
        if product_data and 'error' not in product_data:
            if product_data.get('type') == 'bundle' and float(product_data.get('price', 0)) == 0:
                calculated_price = self._calculate_bundle_price(product_data)
                product_data['price'] = f"{calculated_price:.2f}" # Formateamos a 2 decimales
        
        return product_data


    def search_products(self, search_term, category_id=None, per_page=20, page=1):
        """
        Busca productos en la tienda. Si se proporciona un category_id, la búsqueda
        se limita a esa categoría específica. Soporta paginación.
        """
        if not self.wcapi:
            return {"error": "El servicio de WooCommerce no está configurado correctamente."}
        
        # Preparamos los parámetros base
        params = {
            'search': search_term,
            'per_page': per_page,
            'page': page,
            '_fields': 'id,name,price,regular_price,sale_price,stock_status,images,permalink,short_description,average_rating'
        }

        # CTO: LA MEJORA CLAVE -> Si nos pasan un category_id, lo añadimos a los parámetros.
        if category_id:
            params['category'] = str(category_id)
        
        try:
            response = self.wcapi.get("products", params=params)
            if response.status_code == 200:
                return response.json()
            else:
                logging.error(f"Error al buscar productos en WooCommerce: {response.status_code} {response.text}")
                return {"error": f"Respuesta inesperada de WooCommerce: {response.status_code}"}
        except Exception as e:
            logging.error(f"Excepción al contactar con WooCommerce para buscar productos: {e}")
            return {"error": "No se pudo conectar con la tienda de WooCommerce."}
