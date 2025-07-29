# app/routes/core_routes.py
from flask import Blueprint, jsonify, request, current_app, send_file, g, make_response
from decimal import Decimal
import json, io, zipfile, os
import docxtpl

# CTO: 1. Importamos los módulos específicos, NO el antiguo 'database'
from app.auth import token_required
from app.services import doc_generator_service 
from app.utils import PROVINCE_TO_COMMUNITY_MAP, COMMUNITIES
from app.models import (
    instalacion_model, 
    cliente_model, 
    promotor_model, 
    instalador_model,
    catalog_model # Para las funciones get_..._by_name
)
# NOTA: las funciones get_..._by_name ahora estarán en el modelo de instalación por dependencia
# from app.services import calculation_service # Placeholder para futura refactorización de `calc.py`

core_bp  = Blueprint('core', __name__)

def _sanitize_instalacion_data(data: dict) -> dict:
    numeric_fields = ['numero_paneles', 'numero_inversores', 'numero_baterias', 'potencia_contratada_w', 'longitud_cable_cc_string1', 'seccion_cable_ac_mm2', 'longitud_cable_ac_m', 'diferencial_a', 'sensibilidad_ma']
    sanitized_data = data.copy()
    for field in numeric_fields:
        if field in sanitized_data and (sanitized_data[field] == '' or sanitized_data[field] is None):
            sanitized_data[field] = None
    return sanitized_data

# --- Clientes ---
@core_bp.route('/clientes', methods=['GET'])
@token_required
def get_clientes(conn):
    # CTO: 2. Usamos el modelo específico: cliente_model
    clientes = cliente_model.get_all_clientes(conn, g.user_id)
    return jsonify([dict(c) for c in clientes])

@core_bp.route('/clientes/<int:cliente_id>', methods=['GET'])
@token_required
def get_cliente(conn, cliente_id):
    cliente = cliente_model.get_cliente_by_id(conn, cliente_id, g.user_id)
    return jsonify(dict(cliente)) if cliente else (jsonify({'error': 'Cliente no encontrado'}), 404)

@core_bp.route('/clientes', methods=['POST'])
@token_required
def create_cliente(conn):
    data = request.json
    # Validación básica de la entrada
    if not all(k in data for k in ['nombre', 'dni', 'direccion']) or not all(k in data['direccion'] for k in ['nombre_via', 'localidad', 'provincia']):
        return jsonify({'error': 'Datos insuficientes para crear el cliente y su dirección'}), 400
    
    data['app_user_id'] = g.user_id
    
    # La ruta confía en el modelo para manejar la lógica compleja
    cliente_id, message = cliente_model.add_cliente(conn, data)
    
    if cliente_id:
        return jsonify({'id': cliente_id, 'message': message}), 201
    else:
        return jsonify({'error': message}), 400

@core_bp.route('/clientes/<int:cliente_id>', methods=['PUT'])
@token_required
def update_cliente(conn, cliente_id):
    data = request.json
    success, message = cliente_model.update_cliente(conn, cliente_id, g.user_id, data)
    return jsonify({'message': message}) if success else (jsonify({'error': message}), 400)

@core_bp.route('/clientes/<int:cliente_id>', methods=['DELETE'])
@token_required
def delete_cliente(conn, cliente_id):
    success, message = cliente_model.delete_cliente(conn, cliente_id, g.user_id)
    return jsonify({'message': message}) if success else (jsonify({'error': message}), 404)

# --- Promotores --- (### CTO: Se aplican las mismas correcciones que para Clientes)

@core_bp.route('/promotores', methods=['GET'])
@token_required
def get_promotores(conn):
    promotores = promotor_model.get_all_promotores(conn, g.user_id)
    return jsonify(promotores)

@core_bp.route('/promotores/<int:promotor_id>', methods=['GET'])
@token_required
def get_promotor(conn, promotor_id):
    promotor = promotor_model.get_promotor_by_id(conn, promotor_id, g.user_id)
    if promotor:
        return jsonify(dict(promotor))
    return jsonify({'error': 'Promotor no encontrado o no pertenece a este usuario'}), 404

@core_bp.route('/promotores', methods=['POST'])
@token_required
def create_promotor(conn):
    data = request.json
    if not data or not data.get('nombre_razon_social') or not data.get('dni_cif'):
        return jsonify({'error': 'Faltan campos obligatorios: nombre_razon_social y dni_cif'}), 400
    
    data['app_user_id'] = g.user_id
    new_id, message = promotor_model.add_promotor(conn, data)
    
    if new_id is not None:
        return jsonify({'id': new_id, 'message': message}), 201
    else:
        error_code = 409 if "UNIQUE" in str(message) or "ya existe" in str(message) else 400
        return jsonify({'error': message}), error_code

@core_bp.route('/promotores/<int:promotor_id>', methods=['PUT'])
@token_required
def update_promotor_api(conn, promotor_id):
    data = request.json
    success, message = promotor_model.update_promotor(conn, promotor_id, g.user_id, data)
    
    if success:
        return jsonify({'message': 'Promotor actualizado'}), 200
    else:
        error_code = 409 if "UNIQUE" in str(message) or "ya existe" in str(message) else 400
        return jsonify({'error': message}), error_code

@core_bp.route('/promotores/<int:promotor_id>', methods=['DELETE'])
@token_required
def delete_promotor_api(conn, promotor_id):
    success, message = promotor_model.delete_promotor(conn, promotor_id, g.user_id)
    if success:
        return jsonify({'message': message}), 200
    return jsonify({'error': message}), 404

# --- Instaladores --- (### CTO: Se aplican las mismas correcciones que para Clientes)

@core_bp.route('/instaladores', methods=['GET'])
@token_required
def get_instaladores(conn):
    instaladores = instalador_model.get_all_instaladores(conn, g.user_id)
    return jsonify(instaladores)

@core_bp.route('/instaladores/<int:instalador_id>', methods=['GET'])
@token_required
def get_instalador(conn, instalador_id):
    instalador = instalador_model.get_instalador_by_id(conn, instalador_id, g.user_id)
    if instalador:
        return jsonify(dict(instalador))
    return jsonify({'error': 'Instalador no encontrado o no pertenece a este usuario'}), 404

@core_bp.route('/instaladores', methods=['POST'])
@token_required
def create_instalador(conn):
    data = request.json
    if not data or not data.get('nombre_empresa') or not data.get('cif_empresa'):
        return jsonify({'error': 'Faltan campos obligatorios: nombre_empresa y cif_empresa'}), 400

    data['app_user_id'] = g.user_id
    new_id, message = instalador_model.add_instalador(conn, data)
    
    if new_id is not None:
        return jsonify({'id': new_id, 'message': message}), 201
    else:
        error_code = 409 if "UNIQUE" in str(message) or "ya existe" in str(message) else 400
        return jsonify({'error': message}), error_code

@core_bp.route('/instaladores/<int:instalador_id>', methods=['PUT'])
@token_required
def update_instalador_api(conn, instalador_id):
    data = request.json
    success, message = instalador_model.update_instalador(conn, instalador_id, g.user_id, data)
    
    if success:
        return jsonify({'message': 'Instalador actualizado'}), 200
    else:
        error_code = 409 if "UNIQUE" in str(message) or "ya existe" in str(message) else 400
        return jsonify({'error': message}), error_code

@core_bp.route('/instaladores/<int:instalador_id>', methods=['DELETE'])
@token_required
def delete_instalador_api(conn, instalador_id):
    success, message = instalador_model.delete_instalador(conn, instalador_id, g.user_id)
    if success:
        return jsonify({'message': message}), 200
    return jsonify({'error': message}), 404

# --- Instalaciones ---
@core_bp.route('/instalaciones', methods=['GET'])
@token_required
def get_instalaciones(conn):
    ciudad_filtro = request.args.get('ciudad', None)
    instalaciones = instalacion_model.get_all_instalaciones(conn, g.user_id, ciudad=ciudad_filtro)
    return jsonify(instalaciones)

@core_bp.route('/instalaciones/<int:instalacion_id>', methods=['GET'])
@token_required
def get_instalacion_detalle(conn, instalacion_id):
    instalacion = instalacion_model.get_instalacion_completa(conn, instalacion_id, g.user_id)
    return jsonify(dict(instalacion)) if instalacion else (jsonify({'error': 'Instalación no encontrada'}), 404)

@core_bp.route('/instalaciones', methods=['POST'])
@token_required
def create_instalacion(conn):
    data = request.json
    
    # CTO: Validación de entrada más robusta y específica para IDs.
    required_ids = [
        'cliente_id', 'promotor_id', 'instalador_id', 
        'panel_solar_id', 'inversor_id', 'bateria_id',
        'distribuidora_id', 'tipo_finca_id'
    ]
    missing_fields = [field for field in required_ids if data.get(field) is None]
    if missing_fields:
        return jsonify({'error': f"Faltan los siguientes IDs de entidades obligatorias: {', '.join(missing_fields)}"}), 400

    if 'direccion_emplazamiento' not in data:
        return jsonify({'error': 'Faltan datos en la dirección de emplazamiento.'}), 400

    # CTO: Añadimos el app_user_id a la instalación para seguridad directa.
    # Asegúrate de que la tabla 'instalaciones' tiene una columna 'app_user_id'.
    data['app_user_id'] = g.user_id
    
    # La llamada al modelo ahora es correcta.
    instalacion_id, message = instalacion_model.add_instalacion(conn, data)
    
    if instalacion_id:
        return jsonify({'id': instalacion_id, 'message': message}), 201
    else:
        return jsonify({'error': message}), 400


@core_bp.route('/instalaciones/<int:instalacion_id>', methods=['PUT'])
@token_required
def update_instalacion_endpoint(conn, instalacion_id):
    data = request.json
        # CTO: Limpiamos los datos también en la actualización
    sanitized_data = _sanitize_instalacion_data(data)

    try:
        success, message = instalacion_model.update_instalacion(conn, instalacion_id, g.user_id, sanitized_data)
        if success:
            return jsonify({'message': 'Proyecto actualizado'}), 200
        else:
            return jsonify({'error': message}), 400
    except Exception as e:
        current_app.logger.error(f"Excepción en update_instalacion: {e}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500


@core_bp.route('/instalaciones/<int:instalacion_id>', methods=['DELETE'])
@token_required
def delete_instalacion_api(conn, instalacion_id):
    try:
        success, message = instalacion_model.delete_instalacion(conn, instalacion_id, g.user_id)
        if success:
            return jsonify({'message': 'Instalación eliminada correctamente'}), 200
        else:
            return jsonify({'error': message}), 404
    except Exception as e:
        current_app.logger.error(f"Excepción en delete_instalacion_api: {e}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500


### CTO: VERSIÓN REFACTORIZADA Y SEGURA DE LA GENERACIÓN DE DOCUMENTOS
@core_bp.route('/instalaciones/<int:instalacion_id>/generate-docs', methods=['POST'])
@token_required
def generate_docs_api(conn, instalacion_id):
    user_id = g.user_id
    data = request.json

        # --- PASO 1: DEPURACIÓN Y LOGGING ---
    # Logueamos el payload exacto que recibimos del frontend.
    # Esto nos dirá si la lista 'documentos' contiene elementos inesperados.
    current_app.logger.info(f"Petición para generar docs para Inst ID {instalacion_id}. Payload recibido: {data}")


    # --- PASO 2: BLINDAJE DE LA ENTRADA ---
    # Obtenemos la lista de documentos y la limpiamos, eliminando cualquier
    # string vacío o valor nulo que el frontend pudiera enviar por error.
    selected_doc_files_raw = data.get('documentos', [])
    selected_doc_files = [doc for doc in selected_doc_files_raw if doc] # Filtra strings vacíos y None

    community_slug = data.get('community_slug')

    # Logueamos la lista ya limpia para comparar.
    current_app.logger.info(f"Lista de documentos limpia para procesar: {selected_doc_files}")

    if not selected_doc_files:
        return jsonify({"error": "No se seleccionaron documentos para generar."}), 400
    if not community_slug:
        return jsonify({"error": "No se especificó la comunidad autónoma."}), 400

    try:
        instalacion_completa = instalacion_model.get_instalacion_completa(conn, instalacion_id, user_id)
        if not instalacion_completa:
            return jsonify({"error": "Instalación no encontrada o no pertenece a este usuario"}), 404

        contexto_base = dict(instalacion_completa)
        # Enriquecer contexto con datos de catálogo...
        if nombre_panel := contexto_base.get('panel_solar'):
            if panel_data := catalog_model.get_panel_by_name(conn, nombre_panel):
                contexto_base.update(dict(panel_data))
        if nombre_inversor := contexto_base.get('inversor'):
            if inversor_data := catalog_model.get_inversor_by_name(conn, nombre_inversor):
                contexto_base.update(dict(inversor_data))
        if nombre_bateria := contexto_base.get('bateria'):
             if bateria_data := catalog_model.get_bateria_by_name(conn, nombre_bateria):
                 contexto_base.update(dict(bateria_data))
        
        contexto_final = doc_generator_service.prepare_document_context(contexto_base)
        
        generated_files_in_memory = []
        templates_base_path = os.path.join('templates', community_slug)

        for template_file_name in selected_doc_files:
            template_path = os.path.join(templates_base_path, template_file_name)
            try:
                # La generación con docxtpl ya funciona.
                file_bytes = doc_generator_service.generate_document(template_path, contexto_final)
                
                # Creamos un diccionario con toda la info necesaria para la respuesta.
                base_name = os.path.splitext(template_file_name)[0].replace("_", " ").title()
                output_filename = f"{base_name} - Inst {instalacion_id}.docx"
                
                generated_files_in_memory.append({
                    "name": output_filename, 
                    "bytes": file_bytes,
                    "mimetype": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                })
            except FileNotFoundError:
                current_app.logger.warning(f"Plantilla no encontrada, se omite: {template_path}")
                continue
            except Exception as e:
                current_app.logger.error(f"Error procesando plantilla {template_file_name}: {e}", exc_info=True)
                continue
        
        # Logueamos cuántos documentos se generaron realmente.
        current_app.logger.info(f"Generados {len(generated_files_in_memory)} documentos en memoria.")


        if not generated_files_in_memory:
            return jsonify({"error": "No se pudieron generar los documentos. Las plantillas podrían no existir para la comunidad seleccionada."}), 500

        # --- PASO 4: LÓGICA DE RESPUESTA CORREGIDA Y EXPLÍCITA ---
        if len(generated_files_in_memory) == 1:
            file_to_send = generated_files_in_memory[0]
            current_app.logger.info(f"Enviando 1 archivo: {file_to_send['name']} con mimetype {file_to_send['mimetype']}")
            
            # --- INICIO DE LA CORRECCIÓN ESTRATÉGICA ---
            # Construimos la respuesta manualmente para tener control total sobre las cabeceras.
            response = make_response(file_to_send["bytes"])
            response.headers['Content-Type'] = file_to_send["mimetype"]
            response.headers['Content-Disposition'] = f"attachment; filename=\"{file_to_send['name']}\""
            # Esta es la cabecera clave que podría solucionar el problema.
            # Le pide a los proxies que no modifiquen la codificación del contenido.
            response.headers['Content-Encoding'] = 'identity'
            response.headers['Content-Length'] = len(file_to_send["bytes"])
            return response
        else:
            current_app.logger.info(f"Enviando {len(generated_files_in_memory)} archivos en un ZIP.")
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for file_info in generated_files_in_memory:
                    zf.writestr(file_info["name"], file_info["bytes"])
            zip_buffer.seek(0)
            zip_filename = f"Documentacion Inst {instalacion_id}.zip"
            return send_file(
                zip_buffer,
                mimetype='application/zip',
                as_attachment=True,
                download_name=zip_filename
            )

    except Exception as e:
        current_app.logger.error(f"Error en generate_docs_api para instalación {instalacion_id}: {e}", exc_info=True)
        return jsonify({"error": "Error interno del servidor al generar documentos."}), 500

@core_bp.route('/instalaciones/<int:instalacion_id>/document_options', methods=['GET'])
@token_required
def get_document_options(conn, instalacion_id):
    user_id = g.user_id
    # Usamos get_instalacion_by_id porque solo necesitamos la provincia, es más ligero.
    instalacion = instalacion_model.get_instalacion_completa(conn, instalacion_id, user_id) 
    if not instalacion:
        return jsonify({"error": "Instalación no encontrada"}), 404

    # 1. Determinar la comunidad autónoma
    provincia = instalacion.get('emplazamiento_provincia') # Asegúrate que 'get_instalacion_by_id' devuelve 'provincia'
    if not provincia:
        # Fallback si la instalación no tiene provincia definida
        return jsonify({
            "all_communities": [{"slug": k, "name": v} for k, v in COMMUNITIES.items()],
            "selected_community_slug": None,
            "available_docs": []
        }), 200
        
    community_slug = PROVINCE_TO_COMMUNITY_MAP.get(provincia, None)

    # 2. Obtener los documentos para esa comunidad
    available_docs = doc_generator_service.get_available_docs_for_community(community_slug) if community_slug else []

    # 3. Devolver toda la información necesaria para el popup de Lovable
    response_data = {
        "all_communities": [{"slug": k, "name": v} for k, v in sorted(COMMUNITIES.items(), key=lambda item: item[1])],
        "selected_community_slug": community_slug,
        "available_docs": available_docs
    }
    
    return jsonify(response_data), 200

@core_bp.route('/documentos_por_comunidad/<string:community_slug>', methods=['GET'])
@token_required
def get_docs_by_community(conn, community_slug):
    docs = doc_generator_service.get_available_docs_for_community(community_slug)
    return jsonify({"available_docs": docs})


@core_bp.route('/clientes/<int:cliente_id>/usage', methods=['GET'])
@token_required
def get_cliente_usage(conn, cliente_id):
    count = cliente_model.get_usage_count(conn, cliente_id, g.user_id)
    return jsonify({'usage_count': count})

@core_bp.route('/promotores/<int:promotor_id>/usage', methods=['GET'])
@token_required
def get_promotor_usage(conn, promotor_id):
    count = promotor_model.get_usage_count(conn, promotor_id, g.user_id)
    return jsonify({'usage_count': count})

@core_bp.route('/instaladores/<int:instalador_id>/usage', methods=['GET'])
@token_required
def get_instalador_usage(conn, instalador_id):
    count = instalador_model.get_usage_count(conn, instalador_id, g.user_id)
    return jsonify({'usage_count': count})


# dependencias para eliminar instalaciones con clientes instlaadores y rpmotores
@core_bp.route('/clientes/<int:cliente_id>/dependencies', methods=['GET'])
@token_required
def get_cliente_dependencies(conn, cliente_id):
    # Llama al nuevo método del modelo que devuelve la lista de descripciones.
    dependencies = cliente_model.get_dependencies(conn, cliente_id, g.user_id)
    return jsonify(dependencies)

@core_bp.route('/promotores/<int:promotor_id>/dependencies', methods=['GET'])
@token_required
def get_promotor_dependencies(conn, promotor_id):
    # Reutilizamos el mismo patrón para los promotores.
    dependencies = promotor_model.get_dependencies(conn, promotor_id, g.user_id)
    return jsonify(dependencies)

@core_bp.route('/instaladores/<int:instalador_id>/dependencies', methods=['GET'])
@token_required
def get_instalador_dependencies(conn, instalador_id):
    # Y también para los instaladores, manteniendo la consistencia.
    dependencies = instalador_model.get_dependencies(conn, instalador_id, g.user_id)
    return jsonify(dependencies)
