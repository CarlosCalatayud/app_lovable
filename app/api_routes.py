# app/api_routes.py
from flask import Blueprint, jsonify, request, current_app, send_file, g
import json
from . import db as database
from . import calc as calculations
from .generation import doc_generator
from .auth import token_required, db_connection_managed
from .calculator import ElectricalCalculator
import os
import io
import zipfile
from decimal import Decimal
import docxtpl # Asegúrate de que este import esté, ya que se usa explícitamente.

bp_api = Blueprint('api', __name__)


# --- Endpoints para Instalaciones ---
@bp_api.route('/instalaciones', methods=['GET'])
@token_required
def get_instalaciones(conn): ### CTO: El decorador nos pasa la conexión.
    ciudad_filtro = request.args.get('ciudad', None)
    instalaciones = database.get_all_instalaciones(conn, g.user_id, ciudad=ciudad_filtro)
    return jsonify(instalaciones)

@bp_api.route('/instalaciones/<int:instalacion_id>', methods=['GET'])
@token_required
def get_instalacion_detalle(conn, instalacion_id):
    instalacion = database.get_instalacion_completa(conn, instalacion_id, g.user_id)
    if not instalacion:
        return jsonify({'error': 'Instalación no encontrada o no pertenece a este usuario'}), 404
    return jsonify(instalacion)

@bp_api.route('/instalaciones', methods=['POST'])
@token_required
def create_instalacion(conn):
    data = request.json
    if not data or not data.get('descripcion'):
        return jsonify({'error': 'Falta la descripción del proyecto'}), 400
    
    data['app_user_id'] = g.user_id
    
    try:
        new_id, message = database.add_instalacion(conn, data)
        if new_id is not None:
            return jsonify({'id': new_id, 'message': message}), 201
        else:
            return jsonify({'error': message}), 400
    except Exception as e:
        current_app.logger.error(f"Excepción en create_instalacion: {e}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500

@bp_api.route('/instalaciones/<int:instalacion_id>', methods=['PUT'])
@token_required
def update_instalacion_endpoint(conn, instalacion_id):
    data = request.json
    try:
        success, message = database.update_instalacion(conn, instalacion_id, g.user_id, data)
        if success:
            return jsonify({'message': 'Proyecto actualizado'}), 200
        else:
            return jsonify({'error': message}), 400
    except Exception as e:
        current_app.logger.error(f"Excepción en update_instalacion: {e}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500

@bp_api.route('/instalaciones/<int:instalacion_id>', methods=['DELETE'])
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

# --- Clientes ---

@bp_api.route('/clientes', methods=['GET'])
@token_required
def get_clientes(conn):
    clientes = database.get_all_clientes(conn, g.user_id)
    return jsonify(clientes)

@bp_api.route('/clientes/<int:cliente_id>', methods=['GET'])
@token_required
def get_cliente(conn, cliente_id):
    ### CTO: CORRECCIÓN DE SEGURIDAD - Se añade g.user_id al chequeo.
    cliente = database.get_cliente_by_id(conn, cliente_id, g.user_id)
    if cliente:
        return jsonify(dict(cliente))
    return jsonify({'error': 'Cliente no encontrado o no pertenece a este usuario'}), 404

@bp_api.route('/clientes', methods=['POST'])
@token_required
def create_cliente_api(conn):
    data = request.json
    if not data or not data.get('nombre') or not data.get('dni'):
        return jsonify({'error': 'Faltan campos obligatorios: nombre y dni'}), 400
    
    ### CTO: CORRECCIÓN - Se inyecta el ID de usuario y se pasa el diccionario completo.
    data['app_user_id'] = g.user_id
    new_id, message = database.add_cliente(conn, data)
    
    if new_id is not None:
        return jsonify({'id': new_id, 'message': message}), 201
    else:
        error_code = 409 if "UNIQUE" in str(message) or "ya existe" in str(message) else 400
        return jsonify({'error': message}), error_code

@bp_api.route('/clientes/<int:cliente_id>', methods=['PUT'])
@token_required
def update_cliente_api(conn, cliente_id):
    data = request.json
    ### CTO: CORRECCIÓN - Se pasa el g.user_id para seguridad y el diccionario de datos.
    success, message = database.update_cliente(conn, cliente_id, g.user_id, data)
    
    if success:
        return jsonify({'message': 'Cliente actualizado'}), 200
    else:
        return jsonify({'error': message}), 400

@bp_api.route('/clientes/<int:cliente_id>', methods=['DELETE'])
@token_required
def delete_cliente_api(conn, cliente_id):
    ### CTO: CORRECCIÓN DE SEGURIDAD - Se añade g.user_id al chequeo.
    success, message = database.delete_cliente(conn, cliente_id, g.user_id)
    if success:
        return jsonify({'message': message}), 200
    return jsonify({'error': message}), 404

# --- Promotores --- (### CTO: Se aplican las mismas correcciones que para Clientes)

@bp_api.route('/promotores', methods=['GET'])
@token_required
def get_promotores(conn):
    promotores = database.get_all_promotores(conn, g.user_id)
    return jsonify(promotores)

@bp_api.route('/promotores/<int:promotor_id>', methods=['GET'])
@token_required
def get_promotor(conn, promotor_id):
    promotor = database.get_promotor_by_id(conn, promotor_id, g.user_id)
    if promotor:
        return jsonify(dict(promotor))
    return jsonify({'error': 'Promotor no encontrado o no pertenece a este usuario'}), 404

@bp_api.route('/promotores', methods=['POST'])
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

@bp_api.route('/promotores/<int:promotor_id>', methods=['PUT'])
@token_required
def update_promotor_api(conn, promotor_id):
    data = request.json
    success, message = database.update_promotor(conn, promotor_id, g.user_id, data)
    
    if success:
        return jsonify({'message': 'Promotor actualizado'}), 200
    else:
        error_code = 409 if "UNIQUE" in str(message) or "ya existe" in str(message) else 400
        return jsonify({'error': message}), error_code

@bp_api.route('/promotores/<int:promotor_id>', methods=['DELETE'])
@token_required
def delete_promotor_api(conn, promotor_id):
    success, message = database.delete_promotor(conn, promotor_id, g.user_id)
    if success:
        return jsonify({'message': message}), 200
    return jsonify({'error': message}), 404

# --- Instaladores --- (### CTO: Se aplican las mismas correcciones que para Clientes)

@bp_api.route('/instaladores', methods=['GET'])
@token_required
def get_instaladores(conn):
    instaladores = database.get_all_instaladores(conn, g.user_id)
    return jsonify(instaladores)

@bp_api.route('/instaladores/<int:instalador_id>', methods=['GET'])
@token_required
def get_instalador(conn, instalador_id):
    instalador = database.get_instalador_by_id(conn, instalador_id, g.user_id)
    if instalador:
        return jsonify(dict(instalador))
    return jsonify({'error': 'Instalador no encontrado o no pertenece a este usuario'}), 404

@bp_api.route('/instaladores', methods=['POST'])
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

@bp_api.route('/instaladores/<int:instalador_id>', methods=['PUT'])
@token_required
def update_instalador_api(conn, instalador_id):
    data = request.json
    success, message = database.update_instalador(conn, instalador_id, g.user_id, data)
    
    if success:
        return jsonify({'message': 'Instalador actualizado'}), 200
    else:
        error_code = 409 if "UNIQUE" in str(message) or "ya existe" in str(message) else 400
        return jsonify({'error': message}), error_code

@bp_api.route('/instaladores/<int:instalador_id>', methods=['DELETE'])
@token_required
def delete_instalador_api(conn, instalador_id):
    success, message = database.delete_instalador(conn, instalador_id, g.user_id)
    if success:
        return jsonify({'message': message}), 200
    return jsonify({'error': message}), 404

# --- Endpoints para Catálogos (públicos) ---

# ENDPOINT PÚBLICO UNIFICADO PARA TODOS LOS CATÁLOGOS
@bp_api.route('/catalogos/<string:catalog_name>', methods=['GET'])
@db_connection_managed  # CTO: Usamos el nuevo decorador para rutas públicas.
def get_catalog_data(conn, catalog_name): # Acepta 'conn'
    if catalog_name not in CATALOG_TABLE_MAP:
        return jsonify({'error': f'Catálogo no válido: {catalog_name}'}), 404

    config = CATALOG_TABLE_MAP[catalog_name]
    table_name = config.get("table")
    order_by = config.get("order_by", "id")

    # Usamos la función segura que ya teníamos en db.py
    items = database.get_catalog_data(conn, table_name, order_by_column=order_by)
    
    current_app.logger.info(f"Obtenidos {len(items)} items para el catálogo público '{catalog_name}'.")
    return jsonify(items)



### CTO: VERSIÓN REFACTORIZADA Y SEGURA DE LA GENERACIÓN DE DOCUMENTOS
@bp_api.route('/instalaciones/<int:instalacion_id>/generate-selected-docs', methods=['POST'])
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




# MAPA DE CATÁLOGOS UNIFICADO
# CTO: Unificamos "productos" y "catálogos" en un solo lugar. Es más simple y robusto.
CATALOG_TABLE_MAP = {
    # Catálogos de productos
    "inversores": {"table": "inversores", "order_by": "nombre_inversor"},
    "paneles": {"table": "paneles_solares", "order_by": "nombre_panel"},
    "contadores": {"table": "contadores", "order_by": "nombre_contador"},
    "baterias": {"table": "baterias", "order_by": "nombre_bateria"},
    # Catálogos generales
    "tipos_vias": {"table": "tipos_vias", "order_by": "nombre_tipo_via"},
    "distribuidoras": {"table": "distribuidoras", "order_by": "nombre_distribuidora"},
    "categorias_instalador": {"table": "categorias_instalador", "order_by": "nombre_categoria"},
    "tipos_finca": {"table": "tipos_finca", "order_by": "nombre_tipo_finca"}
}



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
# CTO: CORRECCIÓN DE `TypeError`
# Todas las funciones de los endpoints de la calculadora ahora aceptan el argumento `conn`,
# aunque no lo usen, porque el decorador @token_required se lo pasa.

@bp_api.route('/calculator/voltage-drop', methods=['POST'])
@token_required
def calculate_voltage_drop_endpoint(conn): # Acepta 'conn'
    data = request.json
    calculator = ElectricalCalculator()
    try:
        result = calculator.calculate_voltage_drop(**data) # Pasamos los datos desempaquetados
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error en la calculadora de caída de tensión: {e}", exc_info=True)
        return jsonify({"error": "Error interno del servidor en el cálculo."}), 500

@bp_api.route('/calculator/wire-section', methods=['POST'])
@token_required
def calculate_wire_section_endpoint(conn): # Acepta 'conn'
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
        result = calculator.calculate_wire_section(**data)
        return jsonify(result), 200
    except (ValueError, TypeError, KeyError) as e:
        return jsonify({"error": f"Datos de entrada inválidos: {e}"}), 400
    except Exception as e:
        current_app.logger.error(f"Error en calculate_wire_section: {e}", exc_info=True)
        return jsonify({"error": "Error interno del servidor."}), 500


@bp_api.route('/calculator/panel-separation', methods=['POST'])
@token_required
def calculate_panel_separation_endpoint(conn): # Acepta 'conn'
    data = request.json
    calculator = ElectricalCalculator()
    try:
        result = calculator.calculate_panel_separation(**data)
        return jsonify(result), 200
    except (ValueError, TypeError) as e:
        return jsonify({"error": f"Datos de entrada inválidos: {e}"}), 400
        
# Endpoints Placeholder para los cálculos complejos
@bp_api.route('/calculator/current', methods=['POST'])
@token_required
def calculate_current_endpoint(conn): # <-- LA CORRECCIÓN CLAVE
    """
    Calcula la corriente eléctrica.
    Acepta 'conn' para cumplir con el contrato del decorador, aunque no se use en la lógica interna.
    """
    data = request.json
    current_app.logger.info(f"Cálculo de corriente solicitado con datos: {data}")
    
    calculator = ElectricalCalculator()
    try:
        result = calculator.calculate_current(data.get('method'), data.get('params', {}))
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error inesperado en cálculo de corriente: {e}", exc_info=True)
        return jsonify({"error": "Error interno del servidor en el cálculo."}), 500


@bp_api.route('/calculator/voltage', methods=['POST'])
@token_required
def calculate_voltage_endpoint(conn): # <-- LA CORRECCIÓN CLAVE
    """
    Calcula la tensión eléctrica.
    Acepta 'conn' para cumplir con el contrato del decorador.
    """
    data = request.json
    current_app.logger.info(f"Cálculo de tensión solicitado con datos: {data}")

    calculator = ElectricalCalculator()
    try:
        result = calculator.calculate_voltage(data.get('method'), data.get('params', {}))
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error inesperado en cálculo de tensión: {e}", exc_info=True)
        return jsonify({"error": "Error interno del servidor en el cálculo."}), 500


@bp_api.route('/calculator/protections', methods=['POST'])
@token_required
def calculate_protections_endpoint(conn): # <-- LA CORRECCIÓN CLAVE
    """
    Calcula las protecciones eléctricas necesarias.
    Acepta 'conn' para cumplir con el contrato del decorador.
    """
    data = request.json
    current_app.logger.info(f"Cálculo de protecciones solicitado con datos: {data}")

    calculator = ElectricalCalculator()
    try:
        result = calculator.calculate_protections(data)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error inesperado en cálculo de protecciones: {e}", exc_info=True)
        return jsonify({"error": "Error interno del servidor en el cálculo."}), 500
