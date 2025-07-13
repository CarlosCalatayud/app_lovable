# app/database.py

import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

def connect_db():
    """Se conecta a la BD (PostgreSQL en producción, SQLite en local)."""
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        try:
            conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
            logging.info("Conexión a PostgreSQL establecida con éxito.")
            return conn
        except psycopg2.OperationalError as e:
            logging.critical(f"FATAL: No se pudo conectar a PostgreSQL: {e}")
            raise
    else:
        db_path = os.path.join(os.path.dirname(__file__), 'instalaciones_local.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        logging.info(f"Conexión a SQLite local establecida: {db_path}")
        return conn

def is_postgres(conn):
    """Comprueba si la conexión es a PostgreSQL."""
    return hasattr(conn, 'get_backend_pid')

def create_tables():
    """Crea las tablas si no existen, adaptando la sintaxis para SQLite o PostgreSQL."""
    conn = connect_db()
    db_type = 'postgres' if is_postgres(conn) else 'sqlite'
    
    tables_sql = [
        '''CREATE TABLE IF NOT EXISTS clientes (
            id SERIAL PRIMARY KEY,
            app_user_id TEXT NOT NULL, -- ID del usuario de la app (Supabase) que es dueño de este cliente
            nombre TEXT NOT NULL,
            apellidos TEXT NOT NULL,
            dni TEXT UNIQUE NOT NULL, -- La unicidad del DNI ahora es por cliente, no por usuario global
            direccion TEXT
        )''',
        '''CREATE TABLE IF NOT EXISTS promotores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_user_id TEXT NOT NULL, -- ID del usuario de la app (Supabase) que es dueño de este cliente
            nombre_razon_social TEXT NOT NULL,
            apellidos TEXT,
            direccion_fiscal TEXT NOT NULL,
            dni_cif TEXT UNIQUE NOT NULL
        )''',
        '''CREATE TABLE IF NOT EXISTS instaladores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_user_id TEXT NOT NULL, -- ID del usuario de la app (Supabase) que es dueño de este cliente
            nombre_empresa TEXT NOT NULL,
            direccion_empresa TEXT NOT NULL,
            cif_empresa TEXT UNIQUE NOT NULL,
            nombre_tecnico TEXT,
            competencia_tecnico TEXT
        )''',
        # Para PostgreSQL, el tipo JSONB es más eficiente que TEXT para JSON.
        f'''CREATE TABLE IF NOT EXISTS instalaciones (
            id SERIAL PRIMARY KEY,
            app_user_id TEXT NOT NULL,
            fecha_creacion TIMESTAMPTZ DEFAULT NOW(),
            descripcion TEXT,
            cliente_id INTEGER REFERENCES clientes(id) ON DELETE SET NULL,
            promotor_id INTEGER REFERENCES promotores(id) ON DELETE SET NULL,
            instalador_id INTEGER REFERENCES instaladores(id) ON DELETE SET NULL,
            
            -- Datos de Emplazamiento (ya los teníamos)
            direccion_emplazamiento TEXT,
            tipo_via TEXT,
            nombre_via TEXT,
            numero_via TEXT,
            piso_puerta TEXT,
            codigo_postal TEXT,
            localidad TEXT,
            provincia TEXT,
            referencia_catastral TEXT,
            tipo_finca TEXT,
            
            -- Selección de Equipos (ya los teníamos)
            panel_solar TEXT,
            numero_paneles INTEGER,
            inversor TEXT,
            numero_inversores INTEGER,
            bateria TEXT,
            numero_baterias INTEGER,
            distribuidora TEXT,
            cups TEXT,
            potencia_contratada_w INTEGER,

            -- NUEVAS COLUMNAS BASADAS EN LA PLANTILLA --
            tipo_de_estructura TEXT,
            tipo_de_cubierta TEXT,
            material_cableado TEXT,
            longitud_cable_cc_string1 NUMERIC,
            seccion_cable_ac_mm2 NUMERIC,
            longitud_cable_ac_m NUMERIC,
            protector_sobretensiones TEXT,
            diferencial_a INTEGER,
            sensibilidad_ma INTEGER
        )''',

        '''CREATE TABLE IF NOT EXISTS inversores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_inversor TEXT NOT NULL UNIQUE,
            potencia_salida_va INTEGER,
            largo_inversor_mm INTEGER,
            ancho_inversor_mm INTEGER,
            profundo_inversor_mm REAL,
            peso_inversor_kg REAL,
            proteccion_ip_inversor TEXT,
            potencia_max_paneles_w INTEGER,
            tension_max_entrada_v INTEGER,
            secciones_ca_recomendado_mm2 REAL,
            monofasico_trifasico TEXT,
            corriente_maxima_salida_a REAL,
            magnetotermico_a INTEGER
        )''',
        '''CREATE TABLE IF NOT EXISTS paneles_solares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_panel TEXT NOT NULL UNIQUE,
            potencia_pico_w INTEGER,
            largo_mm INTEGER,
            ancho_mm INTEGER,
            profundidad_mm INTEGER,
            peso_kg REAL,
            eficiencia_panel_porcentaje REAL,
            tension_circuito_abierto_voc REAL,
            tecnologia_panel_solar TEXT,
            numero_celdas_panel INTEGER,
            tension_maximo_funcionamiento_v REAL,
            corriente_maxima_funcionamiento_a REAL,
            fusible_cc_recomendada_a INTEGER
        )''',
        # Catálogos
        '''CREATE TABLE IF NOT EXISTS contadores (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre_contador TEXT NOT NULL UNIQUE)''',
        '''CREATE TABLE IF NOT EXISTS baterias (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre_bateria TEXT NOT NULL UNIQUE, capacidad_kwh REAL)''',
        '''CREATE TABLE IF NOT EXISTS tipos_vias (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre_tipo_via TEXT NOT NULL UNIQUE)''',
        '''CREATE TABLE IF NOT EXISTS distribuidoras (id INTEGER PRIMARY KEY AUTOINCREMENT, codigo_distribuidora TEXT, nombre_distribuidora TEXT NOT NULL UNIQUE)''',
        '''CREATE TABLE IF NOT EXISTS categorias_instalador (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre_categoria TEXT NOT NULL UNIQUE)''',
        '''CREATE TABLE IF NOT EXISTS tipos_finca (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre_tipo_finca TEXT NOT NULL UNIQUE)'''
    ]

    try:
        with conn.cursor() as cursor:
            for table_sql in tables_sql:
                translated_sql = translate_schema(table_sql, db_type)
                cursor.execute(translated_sql)
        conn.commit()
        logging.info("Comprobación/Creación de tablas completada.")

    except (Exception, psycopg2.Error) as error:
        logging.error(f"Error al crear tablas: {error}")

        conn.rollback()
    finally:
        conn.close()


def populate_initial_data():
    """Puebla las tablas de catálogo con datos iniciales si es necesario."""
    conn = connect_db()
    db_type = 'postgres' if is_postgres(conn) else 'sqlite'
    
    # Sintaxis de inserción (cambia placeholders y manejo de conflictos)
    placeholder = '%s' if db_type == 'postgres' else '?'
    conflict_clause = 'ON CONFLICT DO NOTHING' if db_type == 'postgres' else 'OR IGNORE'

    try:
        with conn.cursor() as cursor:
            # Diccionario de datos para poblar
            all_data = {
                "inversores": {
                    "sql": f"INSERT INTO inversores (nombre_inversor, potencia_salida_va, largo_inversor_mm, ancho_inversor_mm, profundo_inversor_mm, peso_inversor_kg, proteccion_ip_inversor, potencia_max_paneles_w, tension_max_entrada_v, secciones_ca_recomendado_mm2, monofasico_trifasico, corriente_maxima_salida_a, magnetotermico_a) VALUES ({', '.join([placeholder]*13)}) {conflict_clause}",
                    "data": [('Huawei SUN2000-2KTL-L1', 2000, 365, 365, 156, 12, 'IP65', 3000, 600, 2.5, 'Monofásico', 8.695652174, 10), ('Huawei SUN2000-3KTL-L1', 3000, 365, 365, 156, 12, 'IP65', 4500, 600, 4, 'Monofásico', 13.04347826, 16)] # ... Añade el resto
                },
                "paneles_solares": {
                    "sql": f"INSERT INTO paneles_solares (nombre_panel, potencia_pico_w, largo_mm, ancho_mm, profundidad_mm, peso_kg, eficiencia_panel_porcentaje, tension_circuito_abierto_voc, tecnologia_panel_solar, numero_celdas_panel, tension_maximo_funcionamiento_v, corriente_maxima_funcionamiento_a, fusible_cc_recomendada_a) VALUES ({', '.join([placeholder]*13)}) {conflict_clause}",
                    "data": [('Jinergy 450Wp', 450, 2094, 1038, 35, 23.3, 22.0, 49.90, 'Monocristalino', 144, 41.35, 10.89, 16), ('Jinergy 550Wp', 550, 2278, 1134, 35, 27.2, 21.29, 49.97, 'Monocristalino', 144, 41.98, 13.12, 16)] # ... Añade el resto
                },
                "contadores": {"sql": f"INSERT INTO contadores (nombre_contador) VALUES ({placeholder}) {conflict_clause}", "data": [('DDSU666-H',), ('DDSU666',), ('DTSU666-H',), ('DTSU666',)]},
                "baterias": {"sql": f"INSERT INTO baterias (nombre_bateria, capacidad_kwh) VALUES ({placeholder}, {placeholder}) {conflict_clause}", "data": [('No hay almacenamiento', 0), ('Pylontech UP2500', 2.84)]}, # ... Añade el resto
                "tipos_vias": {"sql": f"INSERT INTO tipos_vias (nombre_tipo_via) VALUES ({placeholder}) {conflict_clause}", "data": [('CALLE',), ('AVENIDA',), ('PLAZA',)]}, # ... Añade el resto
                "distribuidoras": {"sql": f"INSERT INTO distribuidoras (codigo_distribuidora, nombre_distribuidora) VALUES ({placeholder}, {placeholder}) {conflict_clause}", "data": [('0021', 'I-DE REDES ELÉCTRICAS INTELIGENTES'), ('0022', 'LFD DISTRIBUCIÓN ELECTRICIDAD')]}, # ... Añade el resto
                "categorias_instalador": {"sql": f"INSERT INTO categorias_instalador (nombre_categoria) VALUES ({placeholder}) {conflict_clause}", "data": [('Básica',), ('Especialista',)]},
                "tipos_finca": {"sql": f"INSERT INTO tipos_finca (nombre_tipo_finca) VALUES ({placeholder}) {conflict_clause}", "data": [('Vivienda unifamiliar',), ('Nave industrial',)]} # ... Añade el resto
            }
            
            for table_name, info in all_data.items():
                for record in info["data"]:
                    # psycopg2 no soporta executemany con ON CONFLICT, así que iteramos
                    cursor.execute(info["sql"], record if isinstance(record, tuple) else (record,))
            
            conn.commit()
            print("Datos iniciales poblados (si no existían).")
    except (Exception, psycopg2.Error) as error:
        print(f"Error al poblar datos: {error}")
        conn.rollback()
    finally:
        conn.close()
