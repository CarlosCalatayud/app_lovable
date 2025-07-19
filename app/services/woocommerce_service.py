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

    def get_product_categories(self, per_page=100, page=1):
        """Obtiene una lista de categorías de productos, soportando paginación."""
        if not self.wcapi:
            return {"error": "El servicio de WooCommerce no está configurado correctamente."}
        
        # CTO: Añadimos per_page y page a los parámetros que enviamos a WooCommerce.
        # Pedimos 100 categorías de golpe, lo que suele ser suficiente para mostrarlas todas.
        params = {
            'per_page': per_page,
            'page': page,
            'orderby': 'name', # Ordenamos alfabéticamente
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

    def search_products(self, search_term, per_page=20, page=1):
        """Busca productos en la tienda, soportando paginación."""
        if not self.wcapi:
            return {"error": "El servicio de WooCommerce no está configurado correctamente."}
        
        # CTO: Añadimos per_page y page a los parámetros de búsqueda.
        params = {
            'search': search_term,
            'per_page': per_page,
            'page': page
        }
        
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

    def search_products(self, search_term):
        """Busca productos en la tienda que coincidan con un término de búsqueda."""
        if not self.wcapi:
            return {"error": "El servicio de WooCommerce no está configurado correctamente."}
        
        # Preparamos los parámetros para la API de WooCommerce. 'search' es el parámetro clave.
        params = {
            'search': search_term,
            'per_page': 20  # Limitamos a 20 resultados para no sobrecargar la respuesta
        }
        
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
