# app/api_routes.py
from flask import Blueprint, jsonify, request, current_app, send_file, make_response, g
import json # Para manejar los datos técnicos
from . import db as database # Importa el módulo y le da el alias 'database'
from . import calc as calculations # Importa el módulo de cálculos
from .generation import doc_generator
from .auth import token_required # Importa el decorador
from .calculator import ElectricalCalculator # <-- 1. IMPORTA LA NUEVA CLASE


import os
import io # Para trabajar con bytes en memoria
import zipfile # Para crear archivos ZIP

bp_api = Blueprint('api', __name__)

def get_db_connection():
    # Helper para obtener conexión a la BD. Podrías usar g de Flask.
    return database.connect_db()

# --- Endpoints para Instalaciones ---
@bp_api.route('/instalaciones', methods=['GET'])

@token_required
def get_instalaciones():
    # Obtenemos el parámetro 'ciudad' de la URL, ej: /api/instalaciones?ciudad=Madrid
    ciudad_filtro = request.args.get('ciudad', None)
    
    conn = get_db_connection()
    # Pasamos el filtro de ciudad a la función de la base de datos
    instalaciones = database.get_all_instalaciones(conn, g.user_id, ciudad=ciudad_filtro)
    conn.close()
    
    return jsonify(instalaciones)

@bp_api.route('/instalaciones/<int:instalacion_id>', methods=['GET'])

@token_required
def get_instalacion_detalle(instalacion_id):
    conn = get_db_connection()
    instalacion = database.get_instalacion_completa(conn, instalacion_id, g.user_id)
    conn.close()
    if instalacion:
        return jsonify(instalacion)
    return jsonify({'error': 'Instalación no encontrada o no pertenece a este usuario'}), 404


@bp_api.route('/instalaciones', methods=['POST'])

@token_required # ¡Aplica el decorador!
def create_instalacion():
    data = request.json
    data['app_user_id'] = g.user_id
    
    if not data.get('descripcion'):
        return jsonify({'error': 'Falta la descripción del proyecto'}), 400
    
    conn = None
    try:
        conn = get_db_connection()
        new_id, message = database.add_instalacion(conn, data)
        if new_id is not None:
            conn.commit()
            return jsonify({'id': new_id, 'message': message}), 201
        else:
            conn.rollback()
            return jsonify({'error': message}), 400
    except Exception as e:
        if conn: conn.rollback()
        current_app.logger.error(f"Excepción en create_instalacion: {e}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500
    finally:
        if conn: conn.close()

@bp_api.route('/instalaciones/<int:instalacion_id>', methods=['PUT'])

@token_required # ¡Aplica el decorador!
def update_instalacion_endpoint(instalacion_id):
    data = request.json
    conn = None
    try:
        conn = get_db_connection()
        # La función de DB debe verificar que la instalación pertenece al usuario
        success, message = database.update_instalacion(conn, instalacion_id, g.user_id, data)
        if success:
            conn.commit()
            return jsonify({'message': 'Proyecto actualizado'}), 200
        else:
            conn.rollback()
            return jsonify({'error': message}), 400
    except Exception as e:
        if conn: conn.rollback()
        current_app.logger.error(f"Excepción en update_instalacion: {e}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500
    finally:
        if conn: conn.close()

@bp_api.route('/instalaciones/<int:instalacion_id>', methods=['DELETE'])
@token_required
def delete_instalacion_api(instalacion_id):
    conn = None
    try:
        conn = get_db_connection()
        # Pasamos el ID de la instalación y el ID del propietario para seguridad
        success, message = database.delete_instalacion(conn, instalacion_id, g.user_id)
        
        if success:
            conn.commit()
            return jsonify({'message': 'Instalación eliminada correctamente'}), 200
        else:
            conn.rollback()
            # Esto puede ocurrir si el ID no existe o no pertenece al usuario
            return jsonify({'error': message}), 404
            
    except Exception as e:
        if conn: conn.rollback()
        current_app.logger.error(f"Excepción en delete_instalacion_api: {e}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500
    finally:
        if conn: conn.close()


@bp_api.route('/instalaciones/<int:instalacion_id>/generate-selected-docs', methods=['POST'])

@token_required # ¡Aplica el decorador!
def generate_selected_docs_api(instalacion_id):
    # --- Esta parte inicial no cambia ---
    data = request.json
    current_app.logger.info("=============================================")
    current_app.logger.info(f"Petición para generar docs para ID: {instalacion_id}")
    current_app.logger.info(f"BODY RECIBIDO DE LOVABLE: {json.dumps(data, indent=2)}")
    current_app.logger.info("=============================================")
    selected_template_files = data.get('documentos', [])

    if not selected_template_files:
        return jsonify({"error": "No se seleccionaron documentos para generar."}), 400
    
    conn = None # Inicializamos fuera del try para que exista en el finally

    try:
        conn = get_db_connection()
        instalacion_completa = database.get_instalacion_completa(conn, instalacion_id, g.user_id)
        if not instalacion_completa:
            return jsonify({"error": "Instalación no encontrada"}), 404

        contexto_final = dict(instalacion_completa) # Creamos una copia
        
                # Mapeamos y añadimos los datos de las entidades relacionadas para que coincidan
        # con las variables de la plantilla de Word.
        contexto_final.update({
            'clienteNombre': instalacion_completa.get('promotor_nombre', ''),
            'clienteDireccion': instalacion_completa.get('promotor_direccion', ''),
            'clienteDni': instalacion_completa.get('promotor_cif', ''),
            'instaladorEmpresa': instalacion_completa.get('instalador_empresa', ''),
            'instaladorDireccion': instalacion_completa.get('instalador_direccion', ''),
            'instaladorCif': instalacion_completa.get('instalador_cif', ''),
            'instaladorTecnicoNombre': instalacion_completa.get('instalador_tecnico_nombre', ''),
            'instaladorTecnicoCompetencia': instalacion_completa.get('instalador_tecnico_competencia', '')
        })
        # Obtener y fusionar datos de equipos
        nombre_panel = contexto_final.get('panel_solar')
        if nombre_panel:
            panel_data = database.get_panel_by_name(conn, nombre_panel)
            if panel_data: contexto_final.update(panel_data)

        nombre_inversor = contexto_final.get('inversor')
        if nombre_inversor:
            inversor_data = database.get_inversor_by_name(conn, nombre_inversor)
            if inversor_data: contexto_final.update(inversor_data)
        
        nombre_bateria = contexto_final.get('bateria')
        if nombre_bateria:
             bateria_data = database.get_bateria_by_name(conn, nombre_bateria)
             if bateria_data: contexto_final.update(bateria_data)

        contexto_calculado = calculations.calculate_all_derived_data(contexto_final.copy(), conn)
        contexto_final.update(contexto_calculado)


        # --- INICIO DE LA SOLUCIÓN AL TypeError ---
        from decimal import Decimal # Asegúrate de importar Decimal al principio del archivo
        # Creamos una copia del contexto solo para el logging, para no modificar el original.
        contexto_para_log = contexto_final.copy()
        # Buscamos claves que puedan contener objetos datetime y las convertimos a string.
        for key, value in contexto_para_log.items():
            if hasattr(value, 'isoformat'):  # Detecta objetos date/datetime
                contexto_para_log[key] = value.isoformat()
            elif isinstance(value, Decimal): # Detecta objetos Decimal
                # Convertimos Decimal a float para que sea serializable.
                # float() es suficiente para logging.
                contexto_para_log[key] = float(value)
        
        current_app.logger.info("=============================================")
        current_app.logger.info("CONTEXTO FINAL (APLANADO) A ENVIAR A LA PLANTILLA:")
        current_app.logger.info(json.dumps(contexto_para_log, indent=2, ensure_ascii=False))
        current_app.logger.info("=============================================")
        # Ahora el logging es seguro porque no hay objetos datetime.
        # Ahora el logging es seguro contra datetime y decimal.
        try:
            current_app.logger.info(f"Contexto final para plantilla: {json.dumps(contexto_para_log, indent=2)}")
        except TypeError as e:
            current_app.logger.error(f"Aún hay un error de serialización en el log: {e}")
            # Imprimimos el contexto original para ver qué tipo de dato se nos escapó
            current_app.logger.info(f"Contexto original problemático: {contexto_final}")
        # --- FIN DE LA SOLUCIÓN ---

        # --- AHORA VIENE EL CAMBIO ---

        
        generated_files_in_memory = [] # Almacenará (nombre_archivo, bytes_del_archivo)

        # Mapa de plantillas
        available_templates_map = {
            "MEMORIA TECNICA.docx": "Memoria Tecnica Instalacion {}.docx",
            "DECLARACION RESPONSABLE.docx": "Declaracion de responsable {}.docx",
            "ESTUDIO BASICO SEG Y SALUD.docx": "Estudio Básico Seguridad y Salud {}.docx",
            "GESTION RESIDUOS.docx": "Gestion de Residuos{}.docx",
            "PLAN DE CONTROL DE CALIDAD.docx": "Plan de Control de Calidad {}.docx",
            "CERTIFICADO FIN DE OBRA.docx": "Certificado Fin Obra Instalacion {}.docx",
        }
        
        templates_base_path = current_app.config.get('TEMPLATES_PATH', './templates')

        for template_file_name in selected_template_files:
            if template_file_name in available_templates_map:
                template_path = os.path.join(templates_base_path, template_file_name)
                
                if not os.path.exists(template_path):
                    current_app.logger.error(f"Plantilla no encontrada: {template_path}")
                    continue

                # 1. Crear un buffer de bytes en memoria
                file_stream = io.BytesIO()

                # 2. Llamar a tu generador para que guarde en el buffer, NO en un archivo
                # Para esto, necesitamos una pequeña modificación en doc_generator.py (ver abajo)
                # O podemos hacer el truco aquí mismo:
                doc = doc_generator.DocxTemplate(template_path)
                doc.render(contexto_final) # Renderizamos el contexto limpio
                doc.save(file_stream) # Guardamos en el buffer de memoria
                file_stream.seek(0) # Rebobinamos el buffer para poder leerlo

                # 3. Guardar el nombre y los bytes en nuestra lista
                output_filename = available_templates_map[template_file_name].format(instalacion_id)
                generated_files_in_memory.append({
                    "name": output_filename,
                    "bytes": file_stream.getvalue()
                })
            else:
                current_app.logger.warning(f"Plantilla solicitada no reconocida: {template_file_name}")

        if not generated_files_in_memory:
            return jsonify({"error": "No se pudieron generar los documentos seleccionados."}), 500

        # --- Lógica para enviar la respuesta ---

        if len(generated_files_in_memory) == 1:
            # Si solo es un archivo, enviarlo directamente desde la memoria
            file_to_send = generated_files_in_memory[0]
            return send_file(
                io.BytesIO(file_to_send["bytes"]),
                mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                as_attachment=True,
                download_name=file_to_send["name"]
            )
        else:
            # Si son varios, crear un ZIP en memoria
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for file_info in generated_files_in_memory:
                    zf.writestr(file_info["name"], file_info["bytes"]) # Escribir bytes directamente
            
            zip_buffer.seek(0)
            zip_filename = f"Documentos_Instalacion_{instalacion_id}.zip"
            
            return send_file(
                zip_buffer,
                mimetype='application/zip',
                as_attachment=True,
                download_name=zip_filename
            )

    except Exception as e:
        current_app.logger.error(f"Error general en generate_selected_docs_api: {e}", exc_info=True)
        return jsonify({"error": "Error interno del servidor al generar documentos."}), 500
    finally:
        if conn:
            conn.close()


# --- Endpoints para Usuarios (completando) ---
@bp_api.route('/clientes', methods=['POST'])

@token_required # ¡Aplica el decorador!
def create_cliente_api():
    data = request.json
    # TEMPORAL: Asignamos el ID de usuario fijo
    data['app_user_id'] = "7978ca1c-503d-4550-8d04-3aa01d9113ba" 
    if not data or not data.get('nombre') or not data.get('dni'):
        return jsonify({'error': 'Faltan campos obligatorios: nombre y dni'}), 400

    conn = None
    try:
        conn = get_db_connection()
        new_id, message = database.add_cliente(conn,
                                            data.get('app_user_id'),
                                            data.get('nombre'),
                                            data.get('apellidos'),
                                            data.get('dni'),
                                            data.get('direccion'))
        
        if new_id is not None:
            conn.commit()
            current_app.logger.info(f"Usuario creado con ID: {new_id}. COMMIT realizado.")
            return jsonify({'id': new_id, 'message': message}), 201
        else:
            conn.rollback()
            current_app.logger.error(f"Error al crear cliente, haciendo ROLLBACK. Mensaje: {message}")
            error_code = 409 if "UNIQUE" in str(message) or "ya existe" in str(message) else 400
            return jsonify({'error': message}), error_code

    except Exception as e:
        if conn: conn.rollback()
        current_app.logger.error(f"Excepción en create_cliente_api: {e}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500
    finally:
        if conn: conn.close()


@bp_api.route('/clientes/<int:user_id>', methods=['GET'])

@token_required # ¡Aplica el decorador!
def get_cliente(user_id):
    conn = get_db_connection()
    cliente = database.get_cliente_by_id(conn, user_id)
    conn.close()
    if cliente:
        return jsonify(cliente)
    return jsonify({'error': 'Usuario no encontrado'}), 404

@bp_api.route('/clientes/<int:user_id>', methods=['PUT'])

@token_required # ¡Aplica el decorador!
def update_cliente_api(user_id):
    data = request.json
    conn = None
    try:
        conn = get_db_connection()
        success, message = database.update_cliente(conn, user_id,
                                   data.get('nombre'), data.get('apellidos'),
                                   data.get('dni'), data.get('direccion'))
        if success:
            conn.commit()
            current_app.logger.info(f"Usuario ID {user_id} actualizado. COMMIT realizado.")
            return jsonify({'message': 'Usuario actualizado'}), 200
        else:
            conn.rollback()
            current_app.logger.warning(f"Fallo al actualizar cliente ID {user_id}: {message}")
            return jsonify({'error': message}), 400
    except Exception as e:
        if conn: conn.rollback()
        current_app.logger.error(f"Excepción al actualizar cliente ID {user_id}: {e}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500
    finally:
        if conn: conn.close()


@bp_api.route('/clientes/<int:user_id>', methods=['DELETE'])

@token_required # ¡Aplica el decorador!
def delete_cliente_api(user_id): # Renombrado
    conn = get_db_connection()
    success, message = database.delete_cliente(conn, user_id) # delete_cliente devuelve (bool, mensaje)
    conn.close()
    if success:
        return jsonify({'message': message}), 200
    return jsonify({'error': message}), 400 # O 409 si no se puede eliminar por dependencias


# --- Endpoints para Promotores (CRUD completo) ---
@bp_api.route('/promotores', methods=['POST'])

@token_required # ¡Aplica el decorador!
def create_promotor():
    data = request.json
    if not data or not data.get('nombre_razon_social') or not data.get('dni_cif'):
        return jsonify({'error': 'Faltan campos obligatorios: nombre_razon_social y dni_cif'}), 400

    # --- LÍNEA CLAVE AÑADIDA ---
    data['app_user_id'] = g.user_id
    # ---------------------------

    conn = None
    try:
        conn = get_db_connection()
        new_id, message = database.add_promotor(conn,
                                            data.get('app_user_id'), # Asignar el ID del usuario actual
                                            data.get('nombre_razon_social'),
                                            data.get('apellidos'),
                                            data.get('direccion_fiscal'),
                                            data.get('dni_cif'))
        
        if new_id is not None:
            conn.commit()
            current_app.logger.info(f"Promotor creado con ID: {new_id}. COMMIT realizado.")
            return jsonify({'id': new_id, 'message': message}), 201
        else:
            conn.rollback()
            current_app.logger.error(f"Error al crear promotor, haciendo ROLLBACK. Mensaje: {message}")
            error_code = 409 if "UNIQUE" in str(message) or "ya existe" in str(message) else 400
            return jsonify({'error': message}), error_code

    except Exception as e:
        if conn: conn.rollback()
        current_app.logger.error(f"Excepción en create_promotor: {e}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500
    finally:
        if conn: conn.close()

@bp_api.route('/promotores', methods=['GET'])

@token_required # ¡Aplica el decorador!
def get_promotores():
    conn = get_db_connection()
    promotores = database.get_all_promotores(conn, g.user_id)
    conn.close()
    return jsonify(promotores)

@bp_api.route('/promotores/<int:promotor_id>', methods=['GET'])

@token_required # ¡Aplica el decorador!
def get_promotor(promotor_id):
    conn = get_db_connection()
    promotor = database.get_promotor_by_id(conn, promotor_id)
    conn.close()
    if promotor:
        return jsonify(promotor)
    return jsonify({'error': 'Promotor no encontrado'}), 404

@bp_api.route('/promotores/<int:promotor_id>', methods=['PUT'])

@token_required # ¡Aplica el decorador!
def update_promotor_api(promotor_id):
    data = request.json
    conn = None
    try:
        conn = get_db_connection()
        success, message = database.update_promotor(conn, promotor_id,
                                        data.get('nombre_razon_social'),
                                        data.get('apellidos'),
                                        data.get('direccion_fiscal'),
                                        data.get('dni_cif'))
        
        if success:
            conn.commit()
            current_app.logger.info(f"Promotor ID {promotor_id} actualizado. COMMIT realizado.")
            return jsonify({'message': 'Promotor actualizado'}), 200
        else:
            conn.rollback()
            current_app.logger.warning(f"Fallo al actualizar promotor ID {promotor_id}: {message}")
            error_code = 409 if "UNIQUE" in str(message) or "ya existe" in str(message) else 400
            return jsonify({'error': message}), error_code

    except Exception as e:
        if conn: conn.rollback()
        current_app.logger.error(f"Excepción al actualizar promotor ID {promotor_id}: {e}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500
    finally:
        if conn: conn.close()

@bp_api.route('/promotores/<int:promotor_id>', methods=['DELETE'])

@token_required # ¡Aplica el decorador!
def delete_promotor_api(promotor_id):
    conn = get_db_connection()
    success, message = database.delete_promotor(conn, promotor_id)
    conn.close()
    if success:
        return jsonify({'message': message}), 200
    return jsonify({'error': message}), 400


# --- Endpoints para Instaladores (CRUD completo) ---
@bp_api.route('/instaladores', methods=['POST'])

@token_required # ¡Aplica el decorador!
def create_instalador():
    data = request.json
    if not data or not data.get('nombre_empresa') or not data.get('cif_empresa'):
        return jsonify({'error': 'Faltan campos obligatorios: nombre_empresa y cif_empresa'}), 400

    # --- LÍNEA CLAVE AÑADIDA ---
    data['app_user_id'] = g.user_id
    # ---------------------------

    conn = None # Inicializamos a None
    try:
        conn = get_db_connection()
        new_id, message = database.add_instalador(conn,
                                            data.get('app_user_id'), # Asignar el ID del usuario actual
                                            data.get('nombre_empresa'),
                                            data.get('direccion_empresa'),
                                            data.get('cif_empresa'),
                                            data.get('nombre_tecnico'),
                                            data.get('competencia_tecnico'))
        
        if new_id is not None:
            conn.commit() # <--- COMMIT EXPLÍCITO Y FINAL
            current_app.logger.info(f"Instalador creado con ID: {new_id}. COMMIT realizado.")
            return jsonify({'id': new_id, 'message': message}), 201
        else:
            conn.rollback() # <--- ROLLBACK si la función de DB falla
            current_app.logger.error(f"Error al crear instalador, haciendo ROLLBACK. Mensaje: {message}")
            error_code = 409 if "UNIQUE" in str(message) or "ya existe" in str(message) else 400
            return jsonify({'error': message}), error_code

    except Exception as e:
        if conn:
            conn.rollback() # Rollback en caso de excepción inesperada
        current_app.logger.error(f"Excepción en create_instalador, haciendo ROLLBACK: {e}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500
    finally:
        if conn:
            conn.close()

@bp_api.route('/instaladores', methods=['GET'])

@token_required # ¡Aplica el decorador!
def get_instaladores():
    conn = get_db_connection()
    instaladores = database.get_all_instaladores(conn, g.user_id)
    conn.close()

    # --- LÍNEAS DE DEPURACIÓN AÑADIDAS ---
    # Esto imprimirá en los logs de Render
    current_app.logger.info(f"Obtenidos {len(instaladores)} instaladores de la BD.")
    # Si la lista no es muy larga, podemos incluso imprimirla
    if instaladores:
        current_app.logger.info(f"Datos de instaladores: {instaladores}")
    # ------------------------------------

    return jsonify(instaladores)

@bp_api.route('/instaladores/<int:instalador_id>', methods=['GET'])

@token_required # ¡Aplica el decorador!
def get_instalador(instalador_id):
    conn = get_db_connection()
    instalador = database.get_instalador_by_id(conn, instalador_id)
    conn.close()
    if instalador:
        return jsonify(instalador)
    return jsonify({'error': 'Instalador no encontrado'}), 404

@bp_api.route('/instaladores/<int:instalador_id>', methods=['PUT'])

@token_required # ¡Aplica el decorador!
def update_instalador_api(instalador_id):
    data = request.json
    conn = None
    try:
        conn = get_db_connection()
        success, message = database.update_instalador(conn, instalador_id,
                                            data.get('nombre_empresa'),
                                            data.get('direccion_empresa'),
                                            data.get('cif_empresa'),
                                            data.get('nombre_tecnico'),
                                            data.get('competencia_tecnico'))
        
        if success:
            conn.commit()
            current_app.logger.info(f"Instalador ID {instalador_id} actualizado. COMMIT realizado.")
            return jsonify({'message': 'Instalador actualizado'}), 200
        else:
            conn.rollback()
            current_app.logger.warning(f"Fallo al actualizar instalador ID {instalador_id}: {message}")
            error_code = 409 if "UNIQUE" in str(message) or "ya existe" in str(message) else 400
            return jsonify({'error': message}), error_code

    except Exception as e:
        if conn: conn.rollback()
        current_app.logger.error(f"Excepción al actualizar instalador ID {instalador_id}: {e}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500
    finally:
        if conn: conn.close()

@bp_api.route('/instaladores/<int:instalador_id>', methods=['DELETE'])

@token_required # ¡Aplica el decorador!
def delete_instalador_api(instalador_id):
    conn = get_db_connection()
    success, message = database.delete_instalador(conn, instalador_id)
    conn.close()
    if success:
        return jsonify({'message': message}), 200
    return jsonify({'error': message}), 400

# --- MAPAS DE CONFIGURACIÓN PARA PRODUCTOS Y CATÁLOGOS ---
# DESPUÉS - CORRECTO
PRODUCT_TABLE_MAP = {
    "inversores": {"table": "inversores", "order_by": "nombre_inversor", "add_func": database.add_inversor, "update_func": database.update_inversor},
    "paneles": {"table": "paneles_solares", "order_by": "nombre_panel", "add_func": database.add_panel_solar, "update_func": database.update_panel_solar},
    "contadores": {"table": "contadores", "order_by": "nombre_contador", "add_func": database.add_contador, "update_func": database.update_contador},
    "baterias": {"table": "baterias", "order_by": "nombre_bateria", "add_func": database.add_bateria, "update_func": database.update_bateria},
}

CATALOG_TABLE_MAP = {
    "tipos_vias": {"table": "tipos_vias", "order_by": "nombre_tipo_via"},
    "distribuidoras": {"table": "distribuidoras", "order_by": "nombre_distribuidora"},
    "categorias_instalador": {"table": "categorias_instalador", "order_by": "nombre_categoria"}
}


@bp_api.route('/productos/<string:product_type>', methods=['GET'])

@token_required # ¡Aplica el decorador!
def get_all_products_by_type(product_type):
    if product_type not in PRODUCT_TABLE_MAP:
        return jsonify({'error': f'Tipo de producto no válido: {product_type}'}), 404
    
    config = PRODUCT_TABLE_MAP[product_type]
    table_name = config.get("table")
    order_by = config.get("order_by", "id")

    if not table_name:
        return jsonify({'error': f'Configuración interna errónea para {product_type}'}), 500
    
    conn = get_db_connection()
    # Con la corrección en db.py, 'items' está garantizado que es una lista.
    items = database.get_all_from_table(conn, table_name, order_by_column=order_by)
    conn.close()

    # Este logging ahora es seguro.
    current_app.logger.info(f"Obtenidos {len(items)} items para el producto tipo '{product_type}'.")
    
    return jsonify(items)

@bp_api.route('/catalogos/<string:catalog_name>', methods=['GET'])

@token_required # ¡Aplica el decorador!
def get_catalog_data(catalog_name):
    if catalog_name not in CATALOG_TABLE_MAP:
        return jsonify({'error': f'Catálogo no válido: {catalog_name}'}), 404

    config = CATALOG_TABLE_MAP[catalog_name]
    table_name = config.get("table")
    order_by = config.get("order_by", "id")

    if not table_name:
        return jsonify({'error': f'Configuración interna errónea para {catalog_name}'}), 500

    conn = get_db_connection()
    # 'items' siempre será una lista.
    items = database.get_all_from_table(conn, table_name, order_by_column=order_by)
    conn.close()
    
    current_app.logger.info(f"Obtenidos {len(items)} items para el catálogo '{catalog_name}'.")

    return jsonify(items)



@bp_api.route('/productos/<string:product_type>/<int:item_id>', methods=['GET'])

@token_required # ¡Aplica el decorador!
def get_product_by_id(product_type, item_id):
    if product_type not in PRODUCT_TABLE_MAP:
        return jsonify({'error': 'Tipo de producto no válido'}), 404
    
    table_name = PRODUCT_TABLE_MAP[product_type]["table"]
    conn = get_db_connection()
    item = database.get_item_by_id_from_table(conn, table_name, item_id)
    conn.close()
    if item:
        return jsonify(item)
    return jsonify({'error': f'{product_type[:-1].capitalize()} no encontrado'}), 404


@bp_api.route('/productos/<string:product_type>', methods=['POST'])

@token_required # ¡Aplica el decorador!
def create_product(product_type):
    if product_type not in PRODUCT_TABLE_MAP or "add_func" not in PRODUCT_TABLE_MAP[product_type]:
        return jsonify({'error': 'Creación no soportada para este tipo de producto'}), 400
    
    data = request.json
    conn = None
    try:
        conn = get_db_connection()
        add_function = PRODUCT_TABLE_MAP[product_type]["add_func"]
        new_id, message = add_function(conn, data)

        if new_id is not None:
            conn.commit()
            current_app.logger.info(f"Producto de tipo '{product_type}' creado con ID: {new_id}. COMMIT realizado.")
            return jsonify({'id': new_id, 'message': message}), 201
        else:
            conn.rollback()
            current_app.logger.error(f"Error al crear producto tipo '{product_type}', haciendo ROLLBACK. Mensaje: {message}")
            error_code = 409 if "UNIQUE" in str(message) or "ya existe" in str(message) else 400
            return jsonify({'error': message}), error_code

    except Exception as e:
        if conn: conn.rollback()
        current_app.logger.error(f"Excepción en create_product para '{product_type}': {e}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500
    finally:
        if conn: conn.close()


@bp_api.route('/productos/<string:product_type>/<int:item_id>', methods=['PUT'])

@token_required # ¡Aplica el decorador!
def update_product(product_type, item_id):
    if product_type not in PRODUCT_TABLE_MAP or "update_func" not in PRODUCT_TABLE_MAP[product_type]:
        return jsonify({'error': 'Actualización no soportada para este tipo de producto'}), 400

    data = request.json
    conn = None
    try:
        conn = get_db_connection()
        update_function = PRODUCT_TABLE_MAP[product_type]["update_func"]
        success, message = update_function(conn, item_id, data)

        if success:
            conn.commit()
            current_app.logger.info(f"Producto tipo '{product_type}' con ID {item_id} actualizado. COMMIT realizado.")
            return jsonify({'message': f'{product_type[:-1].capitalize()} actualizado'}), 200
        else:
            conn.rollback()
            current_app.logger.warning(f"Fallo al actualizar producto tipo '{product_type}' ID {item_id}: {message}")
            error_code = 409 if "UNIQUE" in str(message) or "ya existe" in str(message) else 400
            return jsonify({'error': message}), error_code

    except Exception as e:
        if conn: conn.rollback()
        current_app.logger.error(f"Excepción en update_product para '{product_type}' ID {item_id}: {e}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500
    finally:
        if conn: conn.close()


@bp_api.route('/productos/<string:product_type>/<int:item_id>', methods=['DELETE'])

@token_required # ¡Aplica el decorador!
def delete_product(product_type, item_id):
    if product_type not in PRODUCT_TABLE_MAP: # Solo los que tienen CRUD completo
        return jsonify({'error': 'Eliminación no soportada para este tipo de producto o tipo no válido'}), 400

    table_name = PRODUCT_TABLE_MAP[product_type]["table"]
    conn = get_db_connection()
    success, message = database.delete_item_from_table(conn, table_name, item_id)
    conn.close()
    if success:
        return jsonify({'message': message}), 200
    return jsonify({'error': message}), 400

# ... (Implementar GET by ID, PUT, DELETE para Usuarios) ...

@bp_api.route('/clientes', methods=['GET']) # RUTA CAMBIADA
@token_required
def get_clientes():
    conn = get_db_connection()
    clientes = database.get_all_clientes(conn, g.user_id)
    conn.close()
    return jsonify(clientes)


# --- NUEVO ENDPOINT DE PRUEBA DE AUTENTICACIÓN ---
@bp_api.route('/me', methods=['GET'])
@token_required # ¡Protegido por nuestro decorador!
def get_current_user():
    """
    Devuelve el ID del usuario autenticado que viene en el token.
    Sirve para probar que la autenticación funciona.
    """
    
    return jsonify({"message": "Autenticación exitosa", "user_id": g.user_id}), 200


# --- NUEVO ENDPOINT PARA LA CALCULADORA ELÉCTRICA ---
@bp_api.route('/calculator/voltage-drop', methods=['POST'])
@token_required # Protegemos el endpoint, ya que es una funcionalidad de la app
def calculate_voltage_drop_endpoint():
    """
    Endpoint para calcular la caída de tensión.
    Recibe un JSON con todos los parámetros y lo pasa a la calculadora.
    """
    data = request.json
    if not data:
        return jsonify({"error": "No se recibieron datos en la petición."}), 400

    # Creamos una instancia de nuestra calculadora
    calculator = ElectricalCalculator()
    
    try:
        # Llamamos a la función de cálculo pasando los parámetros requeridos
        result = calculator.calculate_voltage_drop(
            current=data.get('current'),
            length=data.get('length'),
            wire_cross_section=data.get('wire_cross_section'),
            material=data.get('material'),
            system_type=data.get('system_type'),
            source_voltage=data.get('source_voltage'),
            power_factor=data.get('power_factor', 1.0) # Usamos el default si no viene
        )
        return jsonify(result), 200
    except ValueError as e:
        # Capturamos los errores de validación y los devolvemos como un 400
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        # Capturamos cualquier otro error inesperado
        current_app.logger.error(f"Error inesperado en la calculadora: {e}", exc_info=True)
        return jsonify({"error": "Error interno del servidor en el cálculo."}), 500

@bp_api.route('/calculator/wire-section', methods=['POST'])
@token_required
def calculate_wire_section_endpoint():
    data = request.json
    calculator = ElectricalCalculator()
    try:
        # --- LÓGICA DE CONVERSIÓN DEFENSIVA ---
        # Definimos una función de ayuda para convertir a float de forma segura
        def to_float(value):
            if value is None or str(value).strip() == "":
                return 0.0 # O puedes lanzar un error si el campo es obligatorio
            return float(str(value).replace(',', '.'))

        # Pasamos los datos a la calculadora usando la conversión segura
        result = calculator.calculate_wire_section(
            system_type=data.get('system_type'),
            voltage=to_float(data.get('voltage')),
            power=to_float(data.get('power')),
            cos_phi=to_float(data.get('cos_phi', 1.0)),
            length=to_float(data.get('length')),
            max_voltage_drop_percent=to_float(data.get('max_voltage_drop_percent')),
            material=data.get('material')
        )
        return jsonify(result), 200
        
    except (ValueError, TypeError, KeyError) as e:
        # Capturamos errores de conversión o si falta una clave
        return jsonify({"error": f"Datos de entrada inválidos: {e}"}), 400
    except Exception as e:
        current_app.logger.error(f"Error en calculate_wire_section: {e}", exc_info=True)
        return jsonify({"error": "Error interno del servidor."}), 500


@bp_api.route('/calculator/panel-separation', methods=['POST'])
@token_required
def calculate_panel_separation_endpoint():
    data = request.json
    calculator = ElectricalCalculator()
    try:
        result = calculator.calculate_panel_separation(
            panel_vertical_side_m=float(data.get('panel_vertical_side_m')),
            panel_inclination_deg=float(data.get('panel_inclination_deg')),
            latitude_deg=float(data.get('latitude_deg'))
        )
        return jsonify(result), 200
    except (ValueError, TypeError) as e:
        return jsonify({"error": f"Datos de entrada inválidos: {e}"}), 400
    except Exception as e:
        current_app.logger.error(f"Error en calculate_panel_separation: {e}", exc_info=True)
        return jsonify({"error": "Error interno del servidor."}), 500
        
# Endpoints Placeholder para los cálculos complejos
@bp_api.route('/calculator/current', methods=['POST'])
@token_required
def calculate_current_endpoint():
    data = request.json
    calculator = ElectricalCalculator()
    result = calculator.calculate_current(data.get('method'), data.get('params'))
    return jsonify(result)

@bp_api.route('/calculator/voltage', methods=['POST'])
@token_required
def calculate_voltage_endpoint():
    data = request.json
    calculator = ElectricalCalculator()
    result = calculator.calculate_voltage(data.get('method'), data.get('params'))
    return jsonify(result)

@bp_api.route('/calculator/protections', methods=['POST'])
@token_required
def calculate_protections_endpoint():
    data = request.json
    
    # --- LOGGING DE DEPURACIÓN ---
    current_app.logger.info("--- CÁLCULO DE PROTECCIONES ---")
    current_app.logger.info(f"BODY RECIBIDO DE LOVABLE: {json.dumps(data, indent=2)}")
    # -----------------------------
    
    calculator = ElectricalCalculator()
    try:
        # El try/except ahora está dentro del endpoint para capturar errores de la calculadora
        result = calculator.calculate_protections(data)
        current_app.logger.info(f"RESULTADO DEL CÁLCULO: {result}")
        return jsonify(result)
        
    except ValueError as e:
        # Capturamos los errores de validación de la calculadora y los devolvemos
        current_app.logger.error(f"Error de validación en cálculo de protecciones: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error inesperado en cálculo de protecciones: {e}", exc_info=True)
        return jsonify({"error": "Error interno del servidor en el cálculo."}), 500
