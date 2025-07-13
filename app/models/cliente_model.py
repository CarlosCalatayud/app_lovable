# app/models/cliente_model.py
from .base_model import _execute_select, _execute_insert, _execute_update_delete

def get_all_clientes(conn, app_user_id):
    sql = "SELECT * FROM clientes WHERE app_user_id = ? ORDER BY nombre"
    return _execute_select(conn, sql, (app_user_id,))

def get_cliente_by_id(conn, cliente_id, app_user_id):
    sql = "SELECT * FROM clientes WHERE id = ? AND app_user_id = ?"
    return _execute_select(conn, sql, (cliente_id, app_user_id), one=True)

def add_cliente(conn, data):
    sql = "INSERT INTO clientes (app_user_id, nombre, apellidos, dni, direccion) VALUES (?, ?, ?, ?, ?)"
    params = (data['app_user_id'], data.get('nombre'), data.get('apellidos'), data.get('dni'), data.get('direccion'))
    return _execute_insert(conn, sql, params)

def update_cliente(conn, cliente_id, app_user_id, data):
    sql = "UPDATE clientes SET nombre = ?, apellidos = ?, dni = ?, direccion = ? WHERE id = ? AND app_user_id = ?"
    params = (data.get('nombre'), data.get('apellidos'), data.get('dni'), data.get('direccion'), cliente_id, app_user_id)
    return _execute_update_delete(conn, sql, params)

def delete_cliente(conn, cliente_id, app_user_id):
    sql = "DELETE FROM clientes WHERE id = ? AND app_user_id = ?"
    return _execute_update_delete(conn, sql, (cliente_id, app_user_id))