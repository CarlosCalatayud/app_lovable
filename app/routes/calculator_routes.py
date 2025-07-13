# app/routes/calculator_routes.py

from flask import Blueprint, jsonify, request, current_app
from app.auth import token_required
# CTO: Importamos la clase desde su nueva ubicación en 'services'
from app.services.calculator_service import ElectricalCalculator

bp = Blueprint('calculator', __name__)

# --- Endpoints para la Calculadora Eléctrica ---

@bp.route('/voltage-drop', methods=['POST'])
@token_required
def calculate_voltage_drop_endpoint(conn):
    data = request.json
    calculator = ElectricalCalculator()
    try:
        result = calculator.calculate_voltage_drop(**data)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error en la calculadora: {e}", exc_info=True)
        return jsonify({"error": "Error interno"}), 500

@bp.route('/calculator/wire-section', methods=['POST'])
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


@bp.route('/calculator/panel-separation', methods=['POST'])
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
@bp.route('/calculator/current', methods=['POST'])
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


@bp.route('/calculator/voltage', methods=['POST'])
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


@bp.route('/calculator/protections', methods=['POST'])
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
