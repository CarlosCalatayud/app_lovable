# app/routes/utility_routes.py

import os
from flask import Blueprint, jsonify, current_app
# CTO: Importamos solo la función de conexión.
from app.database import connect_db
import logging

bp = Blueprint('utility', __name__)

# --- DATOS DE EJEMPLO PARA POBLAR LOS CATÁLOGOS ---
# CTO: Hemos movido la lógica de datos aquí para que sea más fácil de gestionar.
CATALOG_DATA = {
    'tipos_vias': [('ACCESO',), ('ACUEDUCTO',), ('AERODROMO',), ('AEROPUERTO',), ('ALAMEDA',), ('ALMACEN',),
                   ('ALTO',), ('APARTAMENTO',), ('ARROYO',), ('AUTOVIA',), ('AVENIDA',), ('BAJADA',),
                   ('BARRANCO',), ('BARRIADA',), ('BARRIO',), ('BASILICA',), ('BLOQUE',), ('BULEVAR',),
                   ('CALLE',), ('CALLEJA',), ('CALLEJON',), ('CAMINO',), ('CAMPAMENTO',), ('CANAL',),
                   ('CANTON',), ('CAÑADA',), ('CARRERA',), ('CARRETERA',), ('CARRIL',), ('CERRO',),
                   ('COLONIA',), ('COSTANILLA',), ('CUESTA',), ('DEHESA',), ('FINCA',), ('GLORIETA',),
                   ('GRAN VIA',), ('PARAJE',), ('PARCELA',), ('PARQUE',), ('PASADIZO',), ('PASAJE',),
                   ('PASEO',), ('PLAZA',), ('PLAZUELA',), ('POBLADO',), ('POLIGONO',), ('RINCON',),
                   ('RINCONADA',), ('RONDA',), ('ROTONDA',), ('SECTOR',), ('SENDA',), ('TRASERA',),
                   ('TRAVESIA',), ('URBANIZACION',), ('VEREDA',), ('VIA',)],
    'tipos_finca': [('Vivienda unifamiliar',), ('Vivienda adosada',), ('Edificio residencial',), ('Nave industrial',)],
    'categorias_instalador': [('Básica',), ('Especialista',)],
    'tipos_cable': [('Cable de CC',), ('Cable de CA',), ('Puesta a Tierra',)],
    'tipos_instalacion': [('coplanar',), ('triangular',), ('solarbloc',)],
    'tipos_cubierta': [('cubierta con inclinación',), ('cubierta plana',), ('suelo',)],
    'distribuidoras': [
        ('0021', 'I-DE REDES ELÉCTRICAS INTELIGENTES'),
        ('0022', 'UFD DISTRIBUCIÓN ELECTRICIDAD'),
        ('0026', 'HIDROCANTÁBRICO DISTRIBUCIÓN ELÉCTRICA'),
        ('0483', 'DISTRIBUCIÓN ELÉCTRICA DEL TAJUÑA'),
        ('0494', 'DISTRIBUCIÓN ELÉCTRICA EL POZO DEL TIO RAIMUNDO, S.L.U'),
        ('0314', 'HIDROELÉCTRICA VEGA, S.A.'),
        (None, 'ES UNA INSTALACIÓN AISLADA') # Usamos NULL para el código
    ],
    'paneles_solares': [
        ('Panel Genérico 450W', 450),
        ('Panel Premium 550W', 550),
        ('Panel Eco 400W', 400)
    ],
    'inversores': [
        ('Inversor Monofásico 3kW', 'monofasico'),
        ('Inversor Monofásico 5kW', 'monofasico'),
        ('Inversor Trifásico 10kW', 'trifasico')
    ],
    'baterias': [
        ('Batería LFP 5kWh', 5.0),
        ('Batería LFP 10kWh', 10.0),
        ('Sin Batería', 0.0)
    ]
}

def _populate_data(cursor, table_name, columns, data):
    """Función de ayuda para insertar datos de forma segura."""
    # ON CONFLICT DO NOTHING evita errores si los datos ya existen.
    placeholders = ', '.join(['%s'] * len(columns))
    sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
    cursor.executemany(sql, data)
    logging.info(f"Tabla '{table_name}' poblada/verificada.")

@bp.route('/setup/populate-all-catalogs/<path:secret_key>')
def setup_populate_catalogs_endpoint(secret_key):
    """
    Endpoint seguro para poblar TODAS las tablas de catálogo con datos de ejemplo.
    """
    expected_key = os.environ.get('SETUP_SECRET_KEY')
    if not expected_key or secret_key != expected_key:
        return jsonify({"error": "Clave secreta no válida."}), 403
    
    conn = None
    try:
        conn = connect_db()
        with conn.cursor() as cursor:
            _populate_data(cursor, 'tipos_vias', ['nombre_tipo_via'], CATALOG_DATA['tipos_vias'])
            _populate_data(cursor, 'tipos_instalacion', ['nombre'], CATALOG_DATA['tipos_instalacion'])
            _populate_data(cursor, 'tipos_cubierta', ['nombre'], CATALOG_DATA['tipos_cubierta'])
            _populate_data(cursor, 'distribuidoras', ['codigo_distribuidora', 'nombre_distribuidora'], CATALOG_DATA['distribuidoras'])
            _populate_data(cursor, 'tipos_finca', ['nombre_tipo_finca'], CATALOG_DATA['tipos_finca'])
            _populate_data(cursor, 'categorias_instalador', ['nombre_categoria'], CATALOG_DATA['categorias_instalador'])
            _populate_data(cursor, 'tipos_cable', ['nombre'], CATALOG_DATA['tipos_cable'])
            _populate_data(cursor, 'paneles_solares', ['nombre_panel', 'potencia_pico_w'], CATALOG_DATA['paneles_solares'])
            _populate_data(cursor, 'inversores', ['nombre_inversor', 'monofasico_trifasico'], CATALOG_DATA['inversores'])
            _populate_data(cursor, 'baterias', ['nombre_bateria', 'capacidad_kwh'], CATALOG_DATA['baterias'])
        
        conn.commit()
        return jsonify({"status": "success", "message": "Todos los catálogos han sido poblados con datos de ejemplo."}), 200

    except Exception as e:
        if conn: conn.rollback()
        current_app.logger.error(f"Error al poblar los catálogos: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if conn: conn.close()