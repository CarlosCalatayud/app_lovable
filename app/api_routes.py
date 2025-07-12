# app/api_routes.py
from flask import Blueprint, jsonify, request, current_app, send_file, g
import json
from . import db as database
from . import calc as calculations
from .generation import doc_generator
from .auth import token_required
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

@bp_api.route('/catalogos/<string:catalog_name>', methods=['GET'])
@token_required
def get_catalog_data(conn, catalog_name):
    ### CTO: Usamos la función segura que creamos en db.py
    items = database.get_catalog_data(conn, catalog_name)
    # La función get_catalog_data ya previene el acceso a tablas no permitidas.
    if items is None:
        return jsonify({'error': f'Catálogo no válido o error interno: {catalog_name}'}), 404
        
    current_app.logger.info(f"Obtenidos {len(items)} items para el catálogo '{catalog_name}'.")
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
    
    # --- LOGGING DE DEPURACIÓN ---
    current_app.logger.info("--- CÁLCULO DE CORRIENTE ---")
    current_app.logger.info(f"BODY RECIBIDO DE LOVABLE: {json.dumps(data, indent=2)}")
    # -----------------------------

    calculator = ElectricalCalculator()
    try:
        result = calculator.calculate_current(data.get('method'), data.get('params', {}))
        current_app.logger.info(f"RESULTADO DEL CÁLCULO: {result}")
        return jsonify(result)
        
    except ValueError as e:
        current_app.logger.error(f"Error de validación en cálculo de corriente: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error inesperado en cálculo de corriente: {e}", exc_info=True)
        return jsonify({"error": "Error interno del servidor en el cálculo."}), 500

@bp_api.route('/calculator/voltage', methods=['POST'])
@token_required
def calculate_voltage_endpoint():
    data = request.json

    # --- LOGGING DE DEPURACIÓN ---
    current_app.logger.info("--- CÁLCULO DE TENSIÓN ---")
    current_app.logger.info(f"BODY RECIBIDO DE LOVABLE: {json.dumps(data, indent=2)}")
    # -----------------------------

    calculator = ElectricalCalculator()
    try:
        result = calculator.calculate_voltage(data.get('method'), data.get('params', {}))
        current_app.logger.info(f"RESULTADO DEL CÁLCULO: {result}")
        return jsonify(result)

    except ValueError as e:
        current_app.logger.error(f"Error de validación en cálculo de tensión: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error inesperado en cálculo de tensión: {e}", exc_info=True)
        return jsonify({"error": "Error interno del servidor en el cálculo."}), 500

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
        result = calculator.calculate_protections(data)
        current_app.logger.info(f"RESULTADO DEL CÁLCULO: {result}")
        return jsonify(result)
        
    except ValueError as e:
        current_app.logger.error(f"Error de validación en cálculo de protecciones: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error inesperado en cálculo de protecciones: {e}", exc_info=True)
        return jsonify({"error": "Error interno del servidor en el cálculo."}), 500
