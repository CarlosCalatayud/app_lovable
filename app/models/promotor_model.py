# app/models/promotor_model.py

import logging
from .base_model import _execute_select

def get_all_promotores(conn, app_user_id):
    sql = """
        SELECT p.id, p.nombre_razon_social, p.dni_cif, d.alias as direccion_alias
        FROM promotores p
        LEFT JOIN direcciones d ON p.direccion_fiscal_id = d.id
        WHERE p.app_user_id = %s ORDER BY p.nombre_razon_social
    """
    return _execute_select(conn, sql, (app_user_id,))

def get_promotor_by_id(conn, promotor_id, app_user_id):
    sql = """
        SELECT 
            p.id, p.nombre_razon_social, p.dni_cif,
            d.id as direccion_id, d.alias, d.tipo_via_id, tv.nombre_tipo_via,
            d.nombre_via, d.numero_via, d.piso_puerta, d.codigo_postal,
            d.localidad, d.provincia
        FROM promotores p
        LEFT JOIN direcciones d ON p.direccion_fiscal_id = d.id
        LEFT JOIN tipos_vias tv ON d.tipo_via_id = tv.id
        WHERE p.id = %s AND p.app_user_id = %s
    """
    return _execute_select(conn, sql, (promotor_id, app_user_id), one=True)

def add_promotor(conn, data):
    direccion_data = data.get('direccion', {})
    try:
        with conn:
            with conn.cursor() as cursor:
                sql_direccion = "INSERT INTO direcciones (alias, tipo_via_id, nombre_via, numero_via, piso_puerta, codigo_postal, localidad, provincia) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;"
                cursor.execute(sql_direccion, (direccion_data.get('alias', 'Dirección Fiscal'), direccion_data.get('tipo_via_id'), direccion_data.get('nombre_via'), direccion_data.get('numero_via'), direccion_data.get('piso_puerta'), direccion_data.get('codigo_postal'), direccion_data.get('localidad'), direccion_data.get('provincia')))
                direccion_id = cursor.fetchone()['id']
                
                sql_promotor = "INSERT INTO promotores (app_user_id, nombre_razon_social, dni_cif, direccion_fiscal_id) VALUES (%s, %s, %s, %s) RETURNING id;"
                cursor.execute(sql_promotor, (data['app_user_id'], data.get('nombre_razon_social'), data.get('dni_cif'), direccion_id))
                promotor_id = cursor.fetchone()['id']
        logging.info(f"Promotor creado ID: {promotor_id}, Dirección ID: {direccion_id}")
        return promotor_id, "Promotor creado correctamente."
    except Exception as e:
        logging.error(f"Fallo en transacción de añadir promotor: {e}")
        return None, f"Error en la base de datos: {e}"

def update_promotor(conn, promotor_id, app_user_id, data):
    direccion_data = data.get('direccion', {})
    try:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT direccion_fiscal_id FROM promotores WHERE id = %s AND app_user_id = %s", (promotor_id, app_user_id))
                result = cursor.fetchone()
                if not result: raise ValueError("Promotor no encontrado o no autorizado.")
                
                direccion_id = result['direccion_fiscal_id']
                if direccion_data and direccion_id is not None:
                    sql_update_direccion = "UPDATE direcciones SET alias = %s, tipo_via_id = %s, nombre_via = %s, numero_via = %s, piso_puerta = %s, codigo_postal = %s, localidad = %s, provincia = %s WHERE id = %s;"
                    cursor.execute(sql_update_direccion, (direccion_data.get('alias'), direccion_data.get('tipo_via_id'), direccion_data.get('nombre_via'), direccion_data.get('numero_via'), direccion_data.get('piso_puerta'), direccion_data.get('codigo_postal'), direccion_data.get('localidad'), direccion_data.get('provincia'), direccion_id))
                
                sql_update_promotor = "UPDATE promotores SET nombre_razon_social = %s, dni_cif = %s WHERE id = %s;"
                cursor.execute(sql_update_promotor, (data.get('nombre_razon_social'), data.get('dni_cif'), promotor_id))
        logging.info(f"Promotor ID: {promotor_id} actualizado.")
        return True, "Promotor actualizado correctamente."
    except Exception as e:
        logging.error(f"Fallo en transacción de actualizar promotor: {e}")
        return False, f"Error al actualizar el promotor: {e}"

def delete_promotor(conn, promotor_id, app_user_id):
    try:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT direccion_fiscal_id FROM promotores WHERE id = %s AND app_user_id = %s", (promotor_id, app_user_id))
                result = cursor.fetchone()
                if not result: raise ValueError("Promotor no encontrado o no autorizado.")
                
                direccion_id = result['direccion_fiscal_id']
                cursor.execute("DELETE FROM promotores WHERE id = %s", (promotor_id,))
                if direccion_id is not None:
                    cursor.execute("DELETE FROM direcciones WHERE id = %s", (direccion_id,))
        logging.info(f"Promotor ID: {promotor_id} eliminado.")
        return True, "Promotor eliminado correctamente."
    except Exception as e:
        logging.error(f"Fallo en transacción de eliminar promotor: {e}")
        return False, f"Error al eliminar el promotor: {e}"