# app/models/promotor_model.py
from .base_model import _execute_select, _execute_insert, _execute_update_delete

# --- Promotores ---

def add_promotor(conn, data_dict):
    """Añade un nuevo promotor."""
    sql = "INSERT INTO promotores (app_user_id, nombre_razon_social, apellidos, direccion_fiscal, dni_cif) VALUES (?, ?, ?, ?, ?)"
    return _execute_insert(conn, sql, (data_dict['app_user_id'], data_dict.get('nombre_razon_social'), data_dict.get('apellidos'), data_dict.get('direccion_fiscal'), data_dict.get('dni_cif')))

def get_all_promotores(conn, app_user_id):
    """Obtiene todos los promotores de un usuario."""
    sql = "SELECT * FROM promotores WHERE app_user_id = ? ORDER BY nombre_razon_social"
    return _execute_select(conn, sql, (app_user_id,))

def get_promotor_by_id(conn, promotor_id, app_user_id):
    """Obtiene un promotor específico de un usuario."""
    sql = "SELECT * FROM promotores WHERE id = ? AND app_user_id = ?"
    return _execute_select(conn, sql, (promotor_id, app_user_id), one=True)

def update_promotor(conn, promotor_id, app_user_id, data_dict):
    """Actualiza un promotor de un usuario."""
    sql = "UPDATE promotores SET nombre_razon_social = ?, apellidos = ?, direccion_fiscal = ?, dni_cif = ? WHERE id = ? AND app_user_id = ?"
    return _execute_update_delete(conn, sql, (data_dict.get('nombre_razon_social'), data_dict.get('apellidos'), data_dict.get('direccion_fiscal'), data_dict.get('dni_cif'), promotor_id, app_user_id))

def delete_promotor(conn, promotor_id, app_user_id):
    """Elimina un promotor de un usuario."""
    sql = "DELETE FROM promotores WHERE id = ? AND app_user_id = ?"
    return _execute_update_delete(conn, sql, (promotor_id, app_user_id))
