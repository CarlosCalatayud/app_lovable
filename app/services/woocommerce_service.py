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

    def get_product_categories(self):
        """Obtiene una lista de todas las categorías de productos de la tienda."""
        if not self.wcapi:
            return {"error": "El servicio de WooCommerce no está configurado correctamente."}
        
        try:
            response = self.wcapi.get("products/categories")
            if response.status_code == 200:
                return response.json()
            else:
                logging.error(f"Error al obtener categorías de WooCommerce: {response.status_code} {response.text}")
                return {"error": f"Respuesta inesperada de WooCommerce: {response.status_code}"}
        except Exception as e:
            logging.error(f"Excepción al contactar con WooCommerce para obtener categorías: {e}")
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
