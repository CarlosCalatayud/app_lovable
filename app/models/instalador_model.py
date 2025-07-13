# app/models/instalador_model.py
from .base_model import _execute_select, _execute_insert, _execute_update_delete

# --- Instaladores ---

def add_instalador(conn, data_dict):
    """Añade un nuevo instalador."""
    sql = "INSERT INTO instaladores (app_user_id, nombre_empresa, direccion_empresa, cif_empresa, nombre_tecnico, competencia_tecnico) VALUES (?, ?, ?, ?, ?, ?)"
    return _execute_insert(conn, sql, (data_dict['app_user_id'], data_dict.get('nombre_empresa'), data_dict.get('direccion_empresa'), data_dict.get('cif_empresa'), data_dict.get('nombre_tecnico'), data_dict.get('competencia_tecnico')))

def get_all_instaladores(conn, app_user_id):
    """Obtiene todos los instaladores de un usuario."""
    sql = "SELECT * FROM instaladores WHERE app_user_id = ? ORDER BY nombre_empresa"
    return _execute_select(conn, sql, (app_user_id,))

def get_instalador_by_id(conn, instalador_id, app_user_id):
    """Obtiene un instalador específico de un usuario."""
    sql = "SELECT * FROM instaladores WHERE id = ? AND app_user_id = ?"
    return _execute_select(conn, sql, (instalador_id, app_user_id), one=True)

def update_instalador(conn, instalador_id, app_user_id, data_dict):
    """Actualiza un instalador de un usuario."""
    sql = "UPDATE instaladores SET nombre_empresa = ?, direccion_empresa = ?, cif_empresa = ?, nombre_tecnico = ?, competencia_tecnico = ? WHERE id = ? AND app_user_id = ?"
    return _execute_update_delete(conn, sql, (data_dict.get('nombre_empresa'), data_dict.get('direccion_empresa'), data_dict.get('cif_empresa'), data_dict.get('nombre_tecnico'), data_dict.get('competencia_tecnico'), instalador_id, app_user_id))

def delete_instalador(conn, instalador_id, app_user_id):
    """Elimina un instalador de un usuario."""
    sql = "DELETE FROM instaladores WHERE id = ? AND app_user_id = ?"
    return _execute_update_delete(conn, sql, (instalador_id, app_user_id))

