# app/models/instalacion_model.py
from .base_model import _execute_select, _execute_insert, _execute_update_delete


# --- Instalaciones ---

def add_instalacion(conn, data_dict):
    """Añade una nueva instalación usando un diccionario de datos."""
    fields = [
        'app_user_id', 'descripcion', 'cliente_id', 'promotor_id', 'instalador_id',
        'direccion_emplazamiento', 'tipo_via', 'nombre_via', 'numero_via', 'piso_puerta',
        'codigo_postal', 'localidad', 'provincia', 'referencia_catastral', 'tipo_finca',
        'panel_solar', 'numero_paneles', 'inversor', 'numero_inversores', 'bateria',
        'numero_baterias', 'distribuidora', 'cups', 'potencia_contratada_w',
        'tipo_de_estructura', 'tipo_de_cubierta', 'material_cableado', 'longitud_cable_cc_string1',
        'seccion_cable_ac_mm2', 'longitud_cable_ac_m', 'protector_sobretensiones',
        'diferencial_a', 'sensibilidad_ma'
    ]
    columns_to_insert = [f for f in fields if f in data_dict]
    if 'app_user_id' not in columns_to_insert:
        return None, "Error crítico: Falta el app_user_id para crear la instalación."
    values_to_insert = [data_dict[f] for f in columns_to_insert]
    placeholders = ', '.join(['?'] * len(columns_to_insert))
    sql = f"INSERT INTO instalaciones ({', '.join(columns_to_insert)}) VALUES ({placeholders})"
    return _execute_insert(conn, sql, tuple(values_to_insert))

def get_all_instalaciones(conn, app_user_id, ciudad=None):
    """Obtiene todas las instalaciones de un usuario, con filtrado opcional por ciudad."""
    params = [app_user_id]
    sql = "SELECT id, descripcion, fecha_creacion, provincia, localidad FROM instalaciones WHERE app_user_id = ?"
    if ciudad:
        sql += " AND lower(localidad) LIKE ?"
        params.append(f"%{ciudad.lower()}%")
    sql += " ORDER BY fecha_creacion DESC"
    return _execute_select(conn, sql, tuple(params))

def get_instalacion_completa(conn, instalacion_id, app_user_id):
    """Obtiene todos los datos de una instalación específica, verificando que pertenece al usuario."""
    sql = """
    SELECT
        I.*,
        U.nombre as cliente_nombre, U.apellidos as cliente_apellidos, U.dni as cliente_dni,
        P.nombre_razon_social as promotor_nombre, P.dni_cif as promotor_cif,
        INS.nombre_empresa as instalador_empresa, INS.cif_empresa as instalador_cif
    FROM instalaciones I
    LEFT JOIN clientes U ON I.cliente_id = U.id
    LEFT JOIN promotores P ON I.promotor_id = P.id
    LEFT JOIN instaladores INS ON I.instalador_id = INS.id
    WHERE I.id = ? AND I.app_user_id = ?
    """
    return _execute_select(conn, sql, (instalacion_id, app_user_id), one=True)

def update_instalacion(conn, instalacion_id, app_user_id, data_dict):
    """Actualiza una instalación, verificando que pertenece al usuario."""
    fields = [
        'descripcion', 'cliente_id', 'promotor_id', 'instalador_id',
        'direccion_emplazamiento', 'tipo_via', 'nombre_via', 'numero_via', 'piso_puerta',
        'codigo_postal', 'localidad', 'provincia', 'referencia_catastral', 'tipo_finca',
        'panel_solar', 'numero_paneles', 'inversor', 'numero_inversores', 'bateria',
        'numero_baterias', 'distribuidora', 'cups', 'potencia_contratada_w',
        'tipo_de_estructura', 'tipo_de_cubierta', 'material_cableado', 'longitud_cable_cc_string1',
        'seccion_cable_ac_mm2', 'longitud_cable_ac_m', 'protector_sobretensiones',
        'diferencial_a', 'sensibilidad_ma'
    ]
    fields_to_update = [f for f in fields if f in data_dict]
    if not fields_to_update:
        return False, "No se proporcionaron campos para actualizar."
    values = [data_dict[f] for f in fields_to_update]
    values.append(instalacion_id)
    values.append(app_user_id)
    set_clause = ', '.join([f"{field} = ?" for field in fields_to_update])
    sql = f"UPDATE instalaciones SET {set_clause} WHERE id = ? AND app_user_id = ?"
    return _execute_update_delete(conn, sql, tuple(values))

def delete_instalacion(conn, instalacion_id, app_user_id):
    """Elimina una instalación, verificando que pertenece al usuario."""
    sql = "DELETE FROM instalaciones WHERE id = ? AND app_user_id = ?"
    return _execute_update_delete(conn, sql, (instalacion_id, app_user_id))

def get_all_from_table(conn, table_name, order_by_column="id", columns="*"):
    # Lista de validación para seguridad
    VALID_TABLES = ["inversores", "paneles_solares", "contadores", "baterias", "tipos_vias", "distribuidoras", "categorias_instalador", "clientes", "promotores", "instaladores", "tipos_finca"]
    if table_name not in VALID_TABLES:
        print(f"!!! INTENTO DE ACCESO A TABLA NO VÁLIDA: {table_name} !!!")
        # Devolvemos una lista vacía para no romper el frontend
        return []

    # Usamos la función de ayuda _execute_select que ya maneja errores
    # y devuelve [] en caso de fallo.
    sql = f"SELECT {columns} FROM {table_name} ORDER BY {order_by_column}"
    
    # La llamada a _execute_select ya es segura.
    # No necesitamos un try/except aquí.
    return _execute_select(conn, sql)
