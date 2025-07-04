# app/api_routes.py
from flask import Blueprint, jsonify, request, current_app, send_file, make_response
import json # Para manejar los datos técnicos
from . import db as database # Importa el módulo y le da el alias 'database'
from . import calc as calculations # Importa el módulo de cálculos
from .generation import doc_generator
import os
import io # Para trabajar con bytes en memoria
import zipfile # Para crear archivos ZIP

bp_api = Blueprint('api', __name__)

def get_db_connection():
    # Helper para obtener conexión a la BD. Podrías usar g de Flask.
    return database.connect_db()

# --- Endpoints para Instalaciones ---
@bp_api.route('/instalaciones', methods=['GET'])
def get_instalaciones():
    conn = get_db_connection()
    # Usa tu función get_all_instalaciones, adáptala si es necesario
    # para devolver una lista de diccionarios fácilmente serializables a JSON
    instalaciones_raw = database.get_all_instalaciones(conn) # Esta función devuelve (id, descripcion, fecha_creacion)
    conn.close()
    # Convertir sqlite3.Row a dicts
    instalaciones = [dict(row) for row in instalaciones_raw]
    return jsonify(instalaciones)

@bp_api.route('/instalaciones/<int:instalacion_id>', methods=['GET'])
def get_instalacion_detalle(instalacion_id):
    conn = get_db_connection()
    # Usa tu función get_instalacion_completa
    instalacion = database.get_instalacion_completa(conn, instalacion_id)
    conn.close()
    if instalacion:
        return jsonify(instalacion) # get_instalacion_completa ya devuelve un dict
    return jsonify({'error': 'Instalación no encontrada'}), 404

@bp_api.route('/instalaciones', methods=['POST'])
def create_instalacion():
    data = request.json # 'data' es ahora un diccionario plano
    if not data or not data.get('descripcion'):
        return jsonify({'error': 'Falta la descripción del proyecto'}), 400

    conn = None
    try:
        conn = get_db_connection()
        # Pasamos el diccionario completo a la función de la DB
        new_id, message = database.add_instalacion(conn, data)
        
        if new_id is not None:
            conn.commit()
            return jsonify({'id': new_id, 'message': message}), 201
        else:
            conn.rollback()
            return jsonify({'error': message}), 400
    except Exception as e:
        if conn: 
            conn.rollback() 
    if new_id:
        return jsonify({'id': new_id, 'message': 'Instalación creada'}), 201
    return jsonify({'error': 'Error al crear instalación'}), 400

@bp_api.route('/instalaciones/<int:instalacion_id>', methods=['PUT'])
def update_instalacion_endpoint(instalacion_id):
    data = request.json # 'data' es un diccionario plano
    conn = None
        # --- LOGGING DE DEPURACIÓN AÑADIDO ---
    current_app.logger.info(f"Recibida petición PUT para ID {instalacion_id}.")
    current_app.logger.info(f"BODY RECIBIDO: {json.dumps(data, indent=2)}")
    # ------------------------------------

    # Validación básica
    if not data:
        return jsonify({'error': 'No se recibieron datos en el cuerpo de la petición'}), 400

    try:
        conn = get_db_connection()
        # Pasamos el diccionario completo
        success, message = database.update_instalacion(conn, instalacion_id, data)
        
        if success:
            conn.commit()
            return jsonify({'message': message}), 200
        else:
            conn.rollback()
            return jsonify({'error': message}), 400
    except Exception as e:
        if conn: # Si la conexión aún está abierta y hay un error, hacer rollback
            conn.rollback()
        current_app.logger.error(f"Excepción al actualizar instalación ID {instalacion_id}: {e}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor al actualizar instalación.'}), 500
    finally:
        if conn:
            conn.close()

@bp_api.route('/instalaciones/<int:instalacion_id>', methods=['DELETE']) # <--- DEBE TENER EL ID Y 'DELETE'
def delete_instalacion_api(instalacion_id): # Renombrado para claridad
    conn = get_db_connection()
    try:
        # Asume que delete_instalacion devuelve (True/False, "mensaje")
        success, message = database.delete_instalacion(conn, instalacion_id)
        if success:
            return jsonify({'message': message}), 200
        else:
            # Error al eliminar (ej. no encontrado, o dependencia si no se maneja en BD)
            return jsonify({'error': message or 'Error al eliminar instalación'}), 400 # o 404
    except Exception as e:
        current_app.logger.error(f"Error en delete_instalacion_api (id: {instalacion_id}): {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500
    finally:
        if conn:
            conn.close()

# --- Endpoint para generar documentos ---
# @bp_api.route('/instalaciones/<int:instalacion_id>/generate-docs', methods=['POST'])
# def generate_docs_api(instalacion_id):
#     # En el futuro, podrías pasar qué documentos generar en el request.json
#     # doc_types_to_generate = request.json.get('documentos', [])

#     conn = get_db_connection()
#     instalacion_completa = database.get_instalacion_completa(conn, instalacion_id)

#     if not instalacion_completa:
#         conn.close()
#         return jsonify({"error": "Instalación no encontrada"}), 404

#     # 'instalacion_completa' es el 'user_inputs' para calculations
#     # y ya contiene datos_tecnicos como un dict
#     # Asegúrate que los nombres de las claves en instalacion_completa coincidan
#     # con lo que espera calculate_all_derived_data
    
#     # Si 'datos_tecnicos' está anidado:
#     user_inputs_for_calc = instalacion_completa.get('datos_tecnicos', {})
#     # Añade otros campos necesarios para los cálculos que están al nivel superior
#     user_inputs_for_calc.update({
#         k: v for k, v in instalacion_completa.items() if k != 'datos_tecnicos'
#     })
    
#     # O si `calculate_all_derived_data` espera que `user_inputs` sea el dict plano
#     # que se guardaba como JSON (y que ahora es `instalacion_completa['datos_tecnicos']`)
#     # más los datos de las entidades relacionadas:
#     # Deberás reestructurar `user_inputs_for_calc` para que tenga la forma
#     # que `calculate_all_derived_data` espera. Esto es CRUCIAL.
#     # Probablemente `user_inputs_for_calc` deba ser el `datos_tecnicos_dict`
#     # más los datos de las entidades (usuario, promotor, instalador) y de la propia instalación.

#     # Ejemplo: Asumiendo que calculations.py espera un dict plano:
#     context_dict = {}
#     context_dict.update(instalacion_completa.get('datos_tecnicos', {}))
#     print("instalacion completa values", instalacion_completa.values())
#     print("instalacion completa items", instalacion_completa.items())
#     context_dict.update({ # Añadir datos de entidades y generales
#         'descripcion_instalacion': instalacion_completa.get('descripcion'),
#         'fecha_creacion_instalacion': instalacion_completa.get('fecha_creacion'),
#         'nombre_usuario': instalacion_completa.get('nombre_usuario'),
#         # ... y así sucesivamente para todos los datos de entidades
#         # que se usan directamente en las plantillas o en los cálculos
#     })

#     # Llamar a los cálculos
#     calculated_data = calculations.calculate_all_derived_data(context_dict, conn)
#     conn.close() # Cerramos la conexión después de los cálculos

#     # Combinar datos originales y calculados para la plantilla
#     final_context = {**context_dict, **calculated_data}

#     # Lógica de generación de documentos (simplificada)
#     # Deberías tener una lista de plantillas y nombres de salida
#     template_name = "CERTIFICADO FIN DE OBRA.docx" # Esto debería ser dinámico
#     template_path = os.path.join(current_app.config['TEMPLATES_PATH'], template_name)
#     output_filename = f"documento_instalacion_{instalacion_id}_{template_name}"
#     output_path = os.path.join(current_app.config['OUTPUT_DOCS_PATH'], output_filename)

#     success_generation = doc_generator.fill_template_docxtpl(template_path, output_path, final_context)

#     if success_generation:
#         # Ofrecer el archivo para descarga
#         return send_file(output_path, as_attachment=True)
#     else:
#         return jsonify({"error": "Error al generar el documento"}), 500
# NUEVO Endpoint para generar documentos seleccionados
@bp_api.route('/instalaciones/<int:instalacion_id>/generate-selected-docs', methods=['POST'])
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
        instalacion_completa = database.get_instalacion_completa(conn, instalacion_id)
        if not instalacion_completa:
            return jsonify({"error": "Instalación no encontrada"}), 404

        contexto_final = dict(instalacion_completa) # Creamos una copia
        
                # Mapeamos y añadimos los datos de las entidades relacionadas para que coincidan
        # con las variables de la plantilla de Word.
        contexto_final.update({
            'usuarioNombre': instalacion_completa.get('promotor_nombre', ''),
            'usuarioDireccion': instalacion_completa.get('promotor_direccion', ''),
            'usuarioDni': instalacion_completa.get('promotor_cif', ''),
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
@bp_api.route('/usuarios', methods=['POST'])
def create_usuario_api():
    data = request.json
    if not data or not data.get('nombre') or not data.get('dni'):
        return jsonify({'error': 'Faltan campos obligatorios: nombre y dni'}), 400

    conn = None
    try:
        conn = get_db_connection()
        new_id, message = database.add_usuario(conn,
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
            current_app.logger.error(f"Error al crear usuario, haciendo ROLLBACK. Mensaje: {message}")
            error_code = 409 if "UNIQUE" in str(message) or "ya existe" in str(message) else 400
            return jsonify({'error': message}), error_code

    except Exception as e:
        if conn: conn.rollback()
        current_app.logger.error(f"Excepción en create_usuario_api: {e}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500
    finally:
        if conn: conn.close()


@bp_api.route('/usuarios', methods=['GET'])
def get_usuarios():
    conn = get_db_connection()
    # Usa tu función get_all_instalaciones, adáptala si es necesario
    # para devolver una lista de diccionarios fácilmente serializables a JSON
    usuarios_raw = database.get_all_usuarios(conn) # Esta función devuelve (id, descripcion, fecha_creacion)
    conn.close()
    # Convertir sqlite3.Row a dicts
    usuarios = [dict(row) for row in usuarios_raw]
    return jsonify(usuarios)

@bp_api.route('/usuarios/<int:user_id>', methods=['GET'])
def get_usuario(user_id):
    conn = get_db_connection()
    usuario = database.get_usuario_by_id(conn, user_id)
    conn.close()
    if usuario:
        return jsonify(usuario)
    return jsonify({'error': 'Usuario no encontrado'}), 404

@bp_api.route('/usuarios/<int:user_id>', methods=['PUT'])
def update_usuario_api(user_id):
    data = request.json
    conn = None
    try:
        conn = get_db_connection()
        success, message = database.update_usuario(conn, user_id,
                                   data.get('nombre'), data.get('apellidos'),
                                   data.get('dni'), data.get('direccion'))
        if success:
            conn.commit()
            current_app.logger.info(f"Usuario ID {user_id} actualizado. COMMIT realizado.")
            return jsonify({'message': 'Usuario actualizado'}), 200
        else:
            conn.rollback()
            current_app.logger.warning(f"Fallo al actualizar usuario ID {user_id}: {message}")
            return jsonify({'error': message}), 400
    except Exception as e:
        if conn: conn.rollback()
        current_app.logger.error(f"Excepción al actualizar usuario ID {user_id}: {e}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500
    finally:
        if conn: conn.close()


@bp_api.route('/usuarios/<int:user_id>', methods=['DELETE'])
def delete_usuario_api(user_id): # Renombrado
    conn = get_db_connection()
    success, message = database.delete_usuario(conn, user_id) # delete_usuario devuelve (bool, mensaje)
    conn.close()
    if success:
        return jsonify({'message': message}), 200
    return jsonify({'error': message}), 400 # O 409 si no se puede eliminar por dependencias


# --- Endpoints para Promotores (CRUD completo) ---
@bp_api.route('/promotores', methods=['POST'])
def create_promotor():
    data = request.json
    if not data or not data.get('nombre_razon_social') or not data.get('dni_cif'):
        return jsonify({'error': 'Faltan campos obligatorios: nombre_razon_social y dni_cif'}), 400

    conn = None
    try:
        conn = get_db_connection()
        new_id, message = database.add_promotor(conn,
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
def get_promotores():
    conn = get_db_connection()
    promotores = database.get_all_promotores(conn)
    conn.close()
    return jsonify(promotores)

@bp_api.route('/promotores/<int:promotor_id>', methods=['GET'])
def get_promotor(promotor_id):
    conn = get_db_connection()
    promotor = database.get_promotor_by_id(conn, promotor_id)
    conn.close()
    if promotor:
        return jsonify(promotor)
    return jsonify({'error': 'Promotor no encontrado'}), 404

@bp_api.route('/promotores/<int:promotor_id>', methods=['PUT'])
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
def delete_promotor_api(promotor_id):
    conn = get_db_connection()
    success, message = database.delete_promotor(conn, promotor_id)
    conn.close()
    if success:
        return jsonify({'message': message}), 200
    return jsonify({'error': message}), 400


# --- Endpoints para Instaladores (CRUD completo) ---
@bp_api.route('/instaladores', methods=['POST'])
def create_instalador():
    data = request.json
    if not data or not data.get('nombre_empresa') or not data.get('cif_empresa'):
        return jsonify({'error': 'Faltan campos obligatorios: nombre_empresa y cif_empresa'}), 400

    conn = None # Inicializamos a None
    try:
        conn = get_db_connection()
        new_id, message = database.add_instalador(conn,
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
def get_instaladores():
    conn = get_db_connection()
    instaladores = database.get_all_instaladores(conn)
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
def get_instalador(instalador_id):
    conn = get_db_connection()
    instalador = database.get_instalador_by_id(conn, instalador_id)
    conn.close()
    if instalador:
        return jsonify(instalador)
    return jsonify({'error': 'Instalador no encontrado'}), 404

@bp_api.route('/instaladores/<int:instalador_id>', methods=['PUT'])
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
