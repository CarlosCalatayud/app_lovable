# app/models/catalog_model.py
from .base_model import _execute_select

def get_catalog_data(conn, table_name, order_by_column="id", columns="*"):
    """
    Obtiene datos de cualquier tabla de catálogo de forma segura.
    """
    # CTO: CORRECCIÓN -> Añadimos las nuevas tablas a la lista de tablas permitidas.
    VALID_CATALOG_TABLES = [
        "inversores", "paneles_solares", "contadores", "baterias", 
        "tipos_vias", "distribuidoras", "categorias_instalador", "tipos_finca",
        "tipos_instalacion", # <-- AÑADIDO
        "tipos_cubierta"   # <-- AÑADIDO
    ]
    
    # Comprobación de seguridad para evitar inyección SQL en el nombre de la tabla.
    if table_name not in VALID_CATALOG_TABLES:
        # Si la tabla no está en nuestra lista blanca, no procedemos.
        return []

    # Validaciones de seguridad simples para los nombres de las columnas.
    # Evita que se inyecten comandos maliciosos.
    if not all(c.isalnum() or c == '_' for c in order_by_column):
        return []
        
    if not all(c.isalnum() or c in ['_', '*', ','] for c in columns):
        return []

    # Construcción segura de la consulta SQL.
    sql = f"SELECT {columns} FROM {table_name} ORDER BY {order_by_column}"
    return _execute_select(conn, sql)

# Funciones para obtener un ítem específico por nombre (útil para generar documentos)
def get_panel_by_name(conn, nombre_panel):
    sql = "SELECT * FROM paneles_solares WHERE nombre_panel = ?"
    return _execute_select(conn, sql, (nombre_panel,), one=True)

def get_inversor_by_name(conn, nombre_inversor):
    sql = "SELECT * FROM inversores WHERE nombre_inversor = ?"
    return _execute_select(conn, sql, (nombre_inversor,), one=True)

def get_bateria_by_name(conn, nombre_bateria):
    sql = "SELECT * FROM baterias WHERE nombre_bateria = ?"
    return _execute_select(conn, sql, (nombre_bateria,), one=True)