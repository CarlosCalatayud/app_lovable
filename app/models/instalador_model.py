# app/models/instalador_model.py

import logging
from .base_model import _execute_select

# --- LECTURA ---
def get_all_instaladores(conn, app_user_id):
    sql = """
        SELECT i.id, i.nombre_empresa, i.cif_empresa, d.alias as direccion_alias
        FROM instaladores i
        LEFT JOIN direcciones d ON i.direccion_empresa_id = d.id
        WHERE i.app_user_id = %s ORDER BY i.nombre_empresa
    """
    return _execute_select(conn, sql, (app_user_id,))

def get_instalador_by_id(conn, instalador_id, app_user_id):
    """Obtiene los detalles completos de un instalador."""
    sql = """
        SELECT
            i.id, i.nombre_empresa, i.cif_empresa, i.email, i.telefono_contacto,
            i.competencia, i.numero_colegiado_o_instalador, i.numero_registro_industrial,
            d.id as direccion_id, d.alias, d.tipo_via_id, tv.nombre_tipo_via,
            d.nombre_via, d.numero_via, d.piso_puerta, d.codigo_postal,
            d.localidad, d.provincia
        FROM instaladores i
        LEFT JOIN direcciones d ON i.direccion_empresa_id = d.id
        LEFT JOIN tipos_vias tv ON d.tipo_via_id = tv.id
        WHERE i.id = %s AND i.app_user_id = %s
    """
    return _execute_select(conn, sql, (instalador_id, app_user_id), one=True)

# REEMPLAZAR add_instalador
def add_instalador(conn, data):
    direccion_data = data.get('direccion', {})
    try:
        with conn:
            with conn.cursor() as cursor:
                # ... (la lógica de add_direccion sigue igual)
                sql_direccion = "INSERT INTO direcciones (alias, tipo_via_id, nombre_via, numero_via, piso_puerta, codigo_postal, localidad, provincia) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;"
                cursor.execute(sql_direccion, (direccion_data.get('alias', 'Dirección Empresa'), direccion_data.get('tipo_via_id'), direccion_data.get('nombre_via'), direccion_data.get('numero_via'), direccion_data.get('piso_puerta'), direccion_data.get('codigo_postal'), direccion_data.get('localidad'), direccion_data.get('provincia')))
                direccion_id = cursor.fetchone()['id']

                sql_instalador = """
                    INSERT INTO instaladores (
                        app_user_id, nombre_empresa, cif_empresa, direccion_empresa_id,
                        email, telefono_contacto, competencia, numero_colegiado_o_instalador,
                        numero_registro_industrial
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
                """
                params = (
                    data['app_user_id'], data.get('nombre_empresa'), data.get('cif_empresa'), direccion_id,
                    data.get('email'), data.get('telefono_contacto'), data.get('competencia'),
                    data.get('numero_colegiado_o_instalador'), data.get('numero_registro_industrial')
                )
                cursor.execute(sql_instalador, params)
                instalador_id = cursor.fetchone()['id']
        logging.info(f"Instalador creado ID: {instalador_id}")
        return instalador_id, "Instalador creado correctamente."
    except Exception as e:
        logging.error(f"Fallo en transacción de añadir instalador: {e}")
        return None, f"Error en la base de datos: {e}"

# REEMPLAZAR update_instalador
def update_instalador(conn, instalador_id, app_user_id, data):
    direccion_data = data.get('direccion', {})
    try:
        with conn:
            with conn.cursor() as cursor:
                # ... (la lógica de get y update de dirección sigue igual)
                cursor.execute("SELECT direccion_empresa_id FROM instaladores WHERE id = %s AND app_user_id = %s", (instalador_id, app_user_id))
                result = cursor.fetchone()
                if not result: raise ValueError("Instalador no encontrado o no autorizado.")
                direccion_id = result['direccion_empresa_id']
                if direccion_data and direccion_id is not None:
                    sql_update_direccion = "UPDATE direcciones SET alias = %s, tipo_via_id = %s, nombre_via = %s, numero_via = %s, piso_puerta = %s, codigo_postal = %s, localidad = %s, provincia = %s WHERE id = %s;"
                    cursor.execute(sql_update_direccion, (direccion_data.get('alias'), direccion_data.get('tipo_via_id'), direccion_data.get('nombre_via'), direccion_data.get('numero_via'), direccion_data.get('piso_puerta'), direccion_data.get('codigo_postal'), direccion_data.get('localidad'), direccion_data.get('provincia'), direccion_id))
                
                sql_update_instalador = """
                    UPDATE instaladores SET
                        nombre_empresa = %s, cif_empresa = %s, email = %s, telefono_contacto = %s,
                        competencia = %s, numero_colegiado_o_instalador = %s,
                        numero_registro_industrial = %s
                    WHERE id = %s;
                """
                params = (
                    data.get('nombre_empresa'), data.get('cif_empresa'), data.get('email'),
                    data.get('telefono_contacto'), data.get('competencia'),
                    data.get('numero_colegiado_o_instalador'), data.get('numero_registro_industrial'),
                    instalador_id
                )
                cursor.execute(sql_update_instalador, params)
        logging.info(f"Instalador ID: {instalador_id} actualizado.")
        return True, "Instalador actualizado correctamente."
    except Exception as e:
        logging.error(f"Fallo en transacción de actualizar instalador: {e}")
        return False, f"Error al actualizar el instalador: {e}"

def delete_instalador(conn, instalador_id, app_user_id):
    try:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT direccion_empresa_id FROM instaladores WHERE id = %s AND app_user_id = %s", (instalador_id, app_user_id))
                result = cursor.fetchone()
                if not result: raise ValueError("Instalador no encontrado o no autorizado.")
                
                direccion_id = result['direccion_empresa_id']
                cursor.execute("DELETE FROM instaladores WHERE id = %s", (instalador_id,))
                if direccion_id is not None:
                    cursor.execute("DELETE FROM direcciones WHERE id = %s", (direccion_id,))
        logging.info(f"Instalador ID: {instalador_id} eliminado.")
        return True, "Instalador eliminado correctamente."
    except Exception as e:
        logging.error(f"Fallo en transacción de eliminar instalador: {e}")
        return False, f"Error al eliminar el instalador: {e}"