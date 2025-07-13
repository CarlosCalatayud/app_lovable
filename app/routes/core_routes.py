# app/routes/core_routes.py
from flask import Blueprint, jsonify, request, current_app, send_file, g
from decimal import Decimal
import json, io, zipfile, os
import docxtpl

from app.auth import token_required
from app.models import instalacion_model, cliente_model, promotor_model, instalador_model
# NOTA: las funciones get_..._by_name ahora estarán en el modelo de instalación por dependencia
# from app.services import calculation_service # Placeholder para futura refactorización de `calc.py`

bp = Blueprint('core', __name__)

def _sanitize_instalacion_data(data: dict) -> dict:
    numeric_fields = [ 'numero_paneles', 'numero_inversores', 'numero_baterias', 'potencia_contratada_w', 'longitud_cable_cc_string1', 'seccion_cable_ac_mm2', 'longitud_cable_ac_m', 'diferencial_a', 'sensibilidad_ma' ]
    sanitized_data = data.copy()
    for field in numeric_fields:
        if field in sanitized_data and sanitized_data[field] == '':
            sanitized_data[field] = None
    return sanitized_data

# --- Clientes ---
@bp.route('/clientes', methods=['GET'])
@token_required
def get_clientes(conn):
    return jsonify(cliente_model.get_all_clientes(conn, g.user_id))

@bp.route('/clientes/<int:cliente_id>', methods=['GET'])
@token_required
def get_cliente(conn, cliente_id):
    cliente = cliente_model.get_cliente_by_id(conn, cliente_id, g.user_id)
    return jsonify(dict(cliente)) if cliente else (jsonify({'error': 'Cliente no encontrado'}), 404)

@bp.route('/clientes', methods=['POST'])
@token_required
def create_cliente(conn):
    data = request.json
    data['app_user_id'] = g.user_id
    new_id, message = cliente_model.add_cliente(conn, data)
    return (jsonify({'id': new_id, 'message': message}), 201) if new_id else (jsonify({'error': message}), 409)

@bp.route('/clientes/<int:cliente_id>', methods=['PUT'])
@token_required
def update_cliente(conn, cliente_id):
    data = request.json
    success, message = cliente_model.update_cliente(conn, cliente_id, g.user_id, data)
    return jsonify({'message': message}) if success else (jsonify({'error': message}), 400)

@bp.route('/clientes/<int:cliente_id>', methods=['DELETE'])
@token_required
def delete_cliente(conn, cliente_id):
    success, message = cliente_model.delete_cliente(conn, cliente_id, g.user_id)
    return jsonify({'message': message}) if success else (jsonify({'error': message}), 404)

# --- Promotores --- (### CTO: Se aplican las mismas correcciones que para Clientes)

@bp.route('/promotores', methods=['GET'])
@token_required
def get_promotores(conn):
    promotores = database.get_all_promotores(conn, g.user_id)
    return jsonify(promotores)

@bp.route('/promotores/<int:promotor_id>', methods=['GET'])
@token_required
def get_promotor(conn, promotor_id):
    promotor = database.get_promotor_by_id(conn, promotor_id, g.user_id)
    if promotor:
        return jsonify(dict(promotor))
    return jsonify({'error': 'Promotor no encontrado o no pertenece a este usuario'}), 404

@bp.route('/promotores', methods=['POST'])
@token_required
def create_promotor(conn):
    data = request.json
    if not data or not data.get('nombre_razon_social') or not data.get('dni_cif'):
        return jsonify({'error': 'Faltan campos obligatorios: nombre_razon_social y dni_cif'}), 400
    
    data['app_user_id'] = g.user_id
    new_id, message = database.add_promotor(conn, data)
    
    if new_id is not None:
        return jsonify({'id': new_id, 'message': message}), 201
    else:
        error_code = 409 if "UNIQUE" in str(message) or "ya existe" in str(message) else 400
        return jsonify({'error': message}), error_code

@bp.route('/promotores/<int:promotor_id>', methods=['PUT'])
@token_required
def update_promotor_api(conn, promotor_id):
    data = request.json
    success, message = database.update_promotor(conn, promotor_id, g.user_id, data)
    
    if success:
        return jsonify({'message': 'Promotor actualizado'}), 200
    else:
        error_code = 409 if "UNIQUE" in str(message) or "ya existe" in str(message) else 400
        return jsonify({'error': message}), error_code

@bp.route('/promotores/<int:promotor_id>', methods=['DELETE'])
@token_required
def delete_promotor_api(conn, promotor_id):
    success, message = database.delete_promotor(conn, promotor_id, g.user_id)
    if success:
        return jsonify({'message': message}), 200
    return jsonify({'error': message}), 404

# --- Instaladores --- (### CTO: Se aplican las mismas correcciones que para Clientes)

@bp.route('/instaladores', methods=['GET'])
@token_required
def get_instaladores(conn):
    instaladores = database.get_all_instaladores(conn, g.user_id)
    return jsonify(instaladores)

@bp.route('/instaladores/<int:instalador_id>', methods=['GET'])
@token_required
def get_instalador(conn, instalador_id):
    instalador = database.get_instalador_by_id(conn, instalador_id, g.user_id)
    if instalador:
        return jsonify(dict(instalador))
    return jsonify({'error': 'Instalador no encontrado o no pertenece a este usuario'}), 404

@bp.route('/instaladores', methods=['POST'])
@token_required
def create_instalador(conn):
    data = request.json
    if not data or not data.get('nombre_empresa') or not data.get('cif_empresa'):
        return jsonify({'error': 'Faltan campos obligatorios: nombre_empresa y cif_empresa'}), 400

    data['app_user_id'] = g.user_id
    new_id, message = database.add_instalador(conn, data)
    
    if new_id is not None:
        return jsonify({'id': new_id, 'message': message}), 201
    else:
        error_code = 409 if "UNIQUE" in str(message) or "ya existe" in str(message) else 400
        return jsonify({'error': message}), error_code

@bp.route('/instaladores/<int:instalador_id>', methods=['PUT'])
@token_required
def update_instalador_api(conn, instalador_id):
    data = request.json
    success, message = database.update_instalador(conn, instalador_id, g.user_id, data)
    
    if success:
        return jsonify({'message': 'Instalador actualizado'}), 200
    else:
        error_code = 409 if "UNIQUE" in str(message) or "ya existe" in str(message) else 400
        return jsonify({'error': message}), error_code

@bp.route('/instaladores/<int:instalador_id>', methods=['DELETE'])
@token_required
def delete_instalador_api(conn, instalador_id):
    success, message = database.delete_instalador(conn, instalador_id, g.user_id)
    if success:
        return jsonify({'message': message}), 200
    return jsonify({'error': message}), 404

# --- Instalaciones ---
@bp.route('/instalaciones', methods=['GET'])
@token_required
def get_instalaciones(conn):
    ciudad_filtro = request.args.get('ciudad', None)
    instalaciones = instalacion_model.get_all_instalaciones(conn, g.user_id, ciudad=ciudad_filtro)
    return jsonify(instalaciones)

@bp.route('/instalaciones/<int:instalacion_id>', methods=['GET'])
@token_required
def get_instalacion_detalle(conn, instalacion_id):
    instalacion = instalacion_model.get_instalacion_completa(conn, instalacion_id, g.user_id)
    return jsonify(dict(instalacion)) if instalacion else (jsonify({'error': 'Instalación no encontrada'}), 404)

@bp.route('/instalaciones', methods=['POST'])
@token_required
def create_instalacion(conn):
    data = request.json
    if not data or not data.get('descripcion'):
        return jsonify({'error': 'Falta la descripción del proyecto'}), 400
    
    data['app_user_id'] = g.user_id
        # CTO: Limpiamos los datos antes de enviarlos a la BD
    sanitized_data = _sanitize_instalacion_data(data)
    
    try:
        new_id, message = database.add_instalacion(conn, sanitized_data)
        if new_id is not None:
            return jsonify({'id': new_id, 'message': message}), 201
        else:
            # El error ahora será más específico gracias a nuestro db.py
            return jsonify({'error': message}), 400
    except Exception as e:
        current_app.logger.error(f"Excepción en create_instalacion: {e}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500

@bp.route('/instalaciones/<int:instalacion_id>', methods=['PUT'])
@token_required
def update_instalacion_endpoint(conn, instalacion_id):
    data = request.json
        # CTO: Limpiamos los datos también en la actualización
    sanitized_data = _sanitize_instalacion_data(data)

    try:
        success, message = database.update_instalacion(conn, instalacion_id, g.user_id, sanitized_data)
        if success:
            return jsonify({'message': 'Proyecto actualizado'}), 200
        else:
            return jsonify({'error': message}), 400
    except Exception as e:
        current_app.logger.error(f"Excepción en update_instalacion: {e}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500


@bp.route('/instalaciones/<int:instalacion_id>', methods=['DELETE'])
@token_required
def delete_instalacion_api(conn, instalacion_id):
    try:
        success, message = database.delete_instalacion(conn, instalacion_id, g.user_id)
        if success:
            return jsonify({'message': 'Instalación eliminada correctamente'}), 200
        else:
            return jsonify({'error': message}), 404
    except Exception as e:
        current_app.logger.error(f"Excepción en delete_instalacion_api: {e}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500


### CTO: VERSIÓN REFACTORIZADA Y SEGURA DE LA GENERACIÓN DE DOCUMENTOS
@bp.route('/instalaciones/<int:instalacion_id>/generate-selected-docs', methods=['POST'])
@token_required
def generate_selected_docs_api(conn, instalacion_id): # ### CTO: 1. La conexión 'conn' ahora es un argumento.
    data = request.json
    selected_template_files = data.get('documentos', [])

    current_app.logger.info(f"Petición para generar docs para instalación ID: {instalacion_id}. Docs: {selected_template_files}")

    if not selected_template_files:
        return jsonify({"error": "No se seleccionaron documentos para generar."}), 400

    # ### CTO: 2. Se elimina toda la gestión manual de la conexión (get_db_connection, try/finally conn.close)
    try:
        # La lógica de negocio principal empieza aquí directamente.
        # El chequeo de `g.user_id` asegura que solo el dueño puede generar los documentos.
        instalacion_completa = database.get_instalacion_completa(conn, instalacion_id, g.user_id)
        if not instalacion_completa:
            # Este mensaje es seguro, ya que no revela la existencia de la instalación a otros usuarios.
            return jsonify({"error": "Instalación no encontrada o no pertenece a este usuario"}), 404

        contexto_final = dict(instalacion_completa)
        
        # --- Construcción del contexto (esta lógica era correcta y se mantiene) ---
        contexto_final.update({
            'clienteNombre': contexto_final.get('promotor_nombre', ''),
            'clienteDireccion': contexto_final.get('promotor_direccion', ''),
            'clienteDni': contexto_final.get('promotor_cif', ''),
            'instaladorEmpresa': contexto_final.get('instalador_empresa', ''),
            'instaladorDireccion': contexto_final.get('instalador_direccion', ''),
            'instaladorCif': contexto_final.get('instalador_cif', ''),
            'instaladorTecnicoNombre': contexto_final.get('instalador_tecnico_nombre', ''),
            'instaladorTecnicoCompetencia': contexto_final.get('instalador_tecnico_competencia', '')
        })

        if nombre_panel := contexto_final.get('panel_solar'):
            if panel_data := database.get_panel_by_name(conn, nombre_panel):
                contexto_final.update(dict(panel_data))

        if nombre_inversor := contexto_final.get('inversor'):
            if inversor_data := database.get_inversor_by_name(conn, nombre_inversor):
                contexto_final.update(dict(inversor_data))
        
        if nombre_bateria := contexto_final.get('bateria'):
             if bateria_data := database.get_bateria_by_name(conn, nombre_bateria):
                 contexto_final.update(dict(bateria_data))

        contexto_calculado = calculations.calculate_all_derived_data(contexto_final.copy(), conn)
        contexto_final.update(contexto_calculado)
        
        # --- Logging seguro del contexto (esta lógica era correcta y se mantiene) ---
        contexto_para_log = {
            key: float(value) if isinstance(value, Decimal) else (value.isoformat() if hasattr(value, 'isoformat') else value)
            for key, value in contexto_final.items()
        }
        current_app.logger.info(f"Contexto final para plantilla: {json.dumps(contexto_para_log, indent=2, ensure_ascii=False)}")
        
        # --- Generación de archivos en memoria (esta lógica era correcta y se mantiene) ---
        generated_files_in_memory = []
        available_templates_map = {
            "MEMORIA TECNICA.docx": "Memoria Tecnica Instalacion {}.docx",
            "DECLARACION RESPONSABLE.docx": "Declaracion de responsable {}.docx",
            # ... resto de plantillas
        }
        templates_base_path = current_app.config.get('TEMPLATES_PATH', './templates')

        for template_file_name in selected_template_files:
            if template_file_name in available_templates_map:
                template_path = os.path.join(templates_base_path, template_file_name)
                if not os.path.exists(template_path):
                    current_app.logger.error(f"Plantilla no encontrada: {template_path}")
                    continue

                file_stream = io.BytesIO()
                # Usamos docxtpl directamente, no una función de nuestro generador.
                doc = docxtpl.DocxTemplate(template_path)
                doc.render(contexto_final)
                doc.save(file_stream)
                file_stream.seek(0)
                
                output_filename = available_templates_map[template_file_name].format(instalacion_id)
                generated_files_in_memory.append({"name": output_filename, "bytes": file_stream.getvalue()})

        if not generated_files_in_memory:
            return jsonify({"error": "No se pudieron generar los documentos seleccionados."}), 500

        # --- Envío de la respuesta (esta lógica era correcta y se mantiene) ---
        if len(generated_files_in_memory) == 1:
            file_to_send = generated_files_in_memory[0]
            return send_file(io.BytesIO(file_to_send["bytes"]), mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document', as_attachment=True, download_name=file_to_send["name"])
        else:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for file_info in generated_files_in_memory:
                    zf.writestr(file_info["name"], file_info["bytes"])
            zip_buffer.seek(0)
            zip_filename = f"Documentos_Instalacion_{instalacion_id}.zip"
            return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name=zip_filename)

    except Exception as e:
        current_app.logger.error(f"Error general en generate_selected_docs_api: {e}", exc_info=True)
        return jsonify({"error": "Error interno del servidor al generar documentos."}), 500
