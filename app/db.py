# app/db.py
import os
import json
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor # Para que PostgreSQL devuelva dicts
import logging ### CTO: Importamos el módulo de logging profesional.


### CTO: Configuramos un logger básico. En una app más grande, esto iría en la configuración de Flask.
### Esto escribirá en la consola de Render con un formato claro [NIVEL]: mensaje
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')


# --- CONFIGURACIÓN Y CONEXIÓN ---

def connect_db():
    """
    Se conecta a PostgreSQL si la variable de entorno DATABASE_URL está definida.
    De lo contrario, se conecta a una base de datos SQLite local.
    """
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        try:
            conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
            logging.info("Conexión a PostgreSQL establecida con éxito.")
            return conn
        except psycopg2.OperationalError as e:
            logging.critical(f"FATAL: No se pudo conectar a la base de datos PostgreSQL: {e}")
            raise
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, 'instalaciones_local.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        logging.info(f"Conexión a SQLite local establecida con éxito: {db_path}")
        return conn

def is_postgres(conn):
    return hasattr(conn, 'get_backend_pid')

# --- CREACIÓN Y POBLACIÓN DE TABLAS ---

def translate_schema(sql_statement, target_db_type):
    """
    Traduce sentencias DDL (CREATE TABLE) de SQLite a PostgreSQL.
    """
    if target_db_type == 'postgres':
        # Reemplazos comunes de SQLite a PostgreSQL
        sql_statement = sql_statement.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        sql_statement = sql_statement.replace("TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "TIMESTAMPTZ DEFAULT NOW()")
        sql_statement = sql_statement.replace("TEXT", "TEXT") # TEXT es compatible
        sql_statement = sql_statement.replace("REAL", "NUMERIC") # NUMERIC es más preciso
        # SQLite no fuerza los tipos, así que UNIQUE en TEXT es suficiente. PostgreSQL es más estricto.
    return sql_statement

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

# --- FUNCIONES CRUD ADAPTADAS ---
# Cada función recibe la conexión y la usa. La lógica es casi idéntica,
# solo cambia el placeholder y el manejo de errores.

def _execute_insert(conn, sql, params):
    """Función de ayuda para inserciones, maneja la diferencia entre DBs."""
    db_type = 'postgres' if is_postgres(conn) else 'sqlite'
    placeholder = '%s' if db_type == 'postgres' else '?'
    sql = sql.replace('?', placeholder)
    
    # Para PostgreSQL, queremos que devuelva el ID de la nueva fila
    if db_type == 'postgres' and "RETURNING id" not in sql.upper():
        sql += " RETURNING id"

    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        new_id = cursor.fetchone()['id'] if db_type == 'postgres' else cursor.lastrowid
        conn.commit()
        logging.info(f"INSERT exitoso. Nueva ID: {new_id}. Tabla: {sql.split(' ')[2]}")
        return new_id, "Creado correctamente."
    except (psycopg2.IntegrityError, sqlite3.IntegrityError) as e:
        conn.rollback()
        ### CTO: Log de error específico para violaciones de integridad (ej. DNI duplicado).
        logging.warning(f"Error de integridad al ejecutar INSERT. SQL: {cursor.query if db_type == 'postgres' else sql}, PARAMS: {params}. Error: {e}")
        return None, f"Error de integridad: El registro ya existe o viola una restricción."
    except (Exception, psycopg2.Error, sqlite3.Error) as e:
        conn.rollback()
        ### CTO: Log de error genérico con toda la información para depurar.
        logging.error(f"Error de base de datos en INSERT. SQL: {cursor.query if db_type == 'postgres' else sql}, PARAMS: {params}. Error: {e}")
        return None, f"Error de base de datos: {e}"

def _execute_update_delete(conn, sql, params):
    """Función de ayuda para UPDATE/DELETE."""
    db_type = 'postgres' if is_postgres(conn) else 'sqlite'
    placeholder = '%s' if db_type == 'postgres' else '?'
    sql = sql.replace('?', placeholder)
    
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rowcount = cursor.rowcount
        conn.commit() # ### CTO: El commit debe estar aquí para que la operación se complete.
        cursor.close()
        if rowcount == 0:
            logging.warning(f"Operación UPDATE/DELETE no afectó a ninguna fila. SQL: {cursor.query if db_type == 'postgres' else sql}, PARAMS: {params}")
            return False, "Elemento no encontrado o los datos no cambiaron."

        logging.info(f"Operación UPDATE/DELETE exitosa. Filas afectadas: {rowcount}. Tabla: {sql.split(' ')[1]}")
        return True, "Operación completada con éxito."
    except (Exception, psycopg2.Error, sqlite3.Error) as e:
        conn.rollback()
        logging.error(f"Error de base de datos en UPDATE/DELETE. SQL: {cursor.query if db_type == 'postgres' else sql}, PARAMS: {params}. Error: {e}")
        return False, f"Error de base de datos: {e}"

def _execute_select(conn, sql, params=None, one=False):
    """Función de ayuda para sentencias SELECT."""
    db_type = 'postgres' if is_postgres(conn) else 'sqlite'
    placeholder = '%s' if db_type == 'postgres' else '?'
    sql = sql.replace('?', placeholder)
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params or ())
            results = cursor.fetchone() if one else cursor.fetchall()
            return results
    except (Exception, psycopg2.Error, sqlite3.Error) as e:
        ### CTO: Log de error detallado. Esto es crucial para la depuración en Render.
        logging.error(f"Error de base de datos en SELECT. SQL: {cursor.query if 'cursor' in locals() and db_type == 'postgres' else sql}, PARAMS: {params}. Error: {e}")
        return None if one else []

# --- Clientes ---
def add_cliente(conn, data_dict):
    """Añade un nuevo cliente, asegurando que se asocia al usuario de la app."""
    sql = "INSERT INTO clientes (app_user_id, nombre, apellidos, dni, direccion) VALUES (?, ?, ?, ?, ?)"
    # Asumimos que data_dict ya contiene 'app_user_id' inyectado desde la API
    return _execute_insert(conn, sql, (data_dict['app_user_id'], data_dict.get('nombre'), data_dict.get('apellidos'), data_dict.get('dni'), data_dict.get('direccion')))

def get_all_clientes(conn, app_user_id):
    """Obtiene todos los clientes pertenecientes a un usuario de la app."""
    sql = "SELECT * FROM clientes WHERE app_user_id = ? ORDER BY nombre, apellidos"
    return _execute_select(conn, sql, (app_user_id,))

def get_cliente_by_id(conn, cliente_id, app_user_id):
    """Obtiene un cliente específico, verificando que pertenece al usuario de la app."""
    sql = "SELECT * FROM clientes WHERE id = ? AND app_user_id = ?"
    return _execute_select(conn, sql, (cliente_id, app_user_id), one=True)

def update_cliente(conn, cliente_id, app_user_id, data_dict):
    """Actualiza un cliente, verificando que pertenece al usuario de la app."""
    sql = "UPDATE clientes SET nombre = ?, apellidos = ?, dni = ?, direccion = ? WHERE id = ? AND app_user_id = ?"
    return _execute_update_delete(conn, sql, (data_dict.get('nombre'), data_dict.get('apellidos'), data_dict.get('dni'), data_dict.get('direccion'), cliente_id, app_user_id))

def delete_cliente(conn, cliente_id, app_user_id):
    """Elimina un cliente, verificando que pertenece al usuario de la app."""
    # Opcional: añadir una comprobación de si el cliente está en uso en alguna instalación
    sql = "DELETE FROM clientes WHERE id = ? AND app_user_id = ?"
    return _execute_update_delete(conn, sql, (cliente_id, app_user_id))


# --- Promotores ---

def add_promotor(conn, data_dict):
    """Añade un nuevo promotor."""
    sql = "INSERT INTO promotores (app_user_id, nombre_razon_social, apellidos, direccion_fiscal, dni_cif) VALUES (?, ?, ?, ?, ?)"
    return _execute_insert(conn, sql, (data_dict['app_user_id'], data_dict.get('nombre_razon_social'), data_dict.get('apellidos'), data_dict.get('direccion_fiscal'), data_dict.get('dni_cif')))

def get_all_promotores(conn, app_user_id):
    """Obtiene todos los promotores de un usuario."""
    sql = "SELECT * FROM promotores WHERE app_user_id = ? ORDER BY nombre_razon_social"
    return _execute_select(conn, sql, (app_user_id,))

def get_promotor_by_id(conn, promotor_id, app_user_id):
    """Obtiene un promotor específico de un usuario."""
    sql = "SELECT * FROM promotores WHERE id = ? AND app_user_id = ?"
    return _execute_select(conn, sql, (promotor_id, app_user_id), one=True)

def update_promotor(conn, promotor_id, app_user_id, data_dict):
    """Actualiza un promotor de un usuario."""
    sql = "UPDATE promotores SET nombre_razon_social = ?, apellidos = ?, direccion_fiscal = ?, dni_cif = ? WHERE id = ? AND app_user_id = ?"
    return _execute_update_delete(conn, sql, (data_dict.get('nombre_razon_social'), data_dict.get('apellidos'), data_dict.get('direccion_fiscal'), data_dict.get('dni_cif'), promotor_id, app_user_id))

def delete_promotor(conn, promotor_id, app_user_id):
    """Elimina un promotor de un usuario."""
    sql = "DELETE FROM promotores WHERE id = ? AND app_user_id = ?"
    return _execute_update_delete(conn, sql, (promotor_id, app_user_id))


# --- Instaladores ---

def add_instalador(conn, data_dict):
    """Añade un nuevo instalador."""
    sql = "INSERT INTO instaladores (app_user_id, nombre_empresa, direccion_empresa, cif_empresa, nombre_tecnico, competencia_tecnico) VALUES (?, ?, ?, ?, ?, ?)"
    return _execute_insert(conn, sql, (data_dict['app_user_id'], data_dict.get('nombre_empresa'), data_dict.get('direccion_empresa'), data_dict.get('cif_empresa'), data_dict.get('nombre_tecnico'), data_dict.get('competencia_tecnico')))

def get_all_instaladores(conn, app_user_id):
    """Obtiene todos los instaladores de un usuario."""
    sql = "SELECT * FROM instaladores WHERE app_user_id = ? ORDER BY nombre_empresa"
    return _execute_select(conn, sql, (app_user_id,))

def get_instalador_by_id(conn, instalador_id, app_user_id):
    """Obtiene un instalador específico de un usuario."""
    sql = "SELECT * FROM instaladores WHERE id = ? AND app_user_id = ?"
    return _execute_select(conn, sql, (instalador_id, app_user_id), one=True)

def update_instalador(conn, instalador_id, app_user_id, data_dict):
    """Actualiza un instalador de un usuario."""
    sql = "UPDATE instaladores SET nombre_empresa = ?, direccion_empresa = ?, cif_empresa = ?, nombre_tecnico = ?, competencia_tecnico = ? WHERE id = ? AND app_user_id = ?"
    return _execute_update_delete(conn, sql, (data_dict.get('nombre_empresa'), data_dict.get('direccion_empresa'), data_dict.get('cif_empresa'), data_dict.get('nombre_tecnico'), data_dict.get('competencia_tecnico'), instalador_id, app_user_id))

def delete_instalador(conn, instalador_id, app_user_id):
    """Elimina un instalador de un usuario."""
    sql = "DELETE FROM instaladores WHERE id = ? AND app_user_id = ?"
    return _execute_update_delete(conn, sql, (instalador_id, app_user_id))


# --- Instalaciones ---

def add_instalacion(conn, data_dict):
    """Añade una nueva instalación usando un diccionario de datos."""
    fields = [
        'app_user_id', 'descripcion', 'cliente_id', 'promotor_id', 'instalador_id',
        'direccion_emplazamiento', 'tipo_via', 'nombre_via', 'numero_via', 'piso_puerta',
        'codigo_postal', 'localidad', 'provincia', 'referencia_catastral', 'tipo_finca',
        'panel_solar', 'numero_paneles', 'inversor', 'numero_inversores', 'bateria',
        'numero_baterias', 'distribuidora', 'cups', 'potencia_contratada_w',
        'tipo_de_estructura', 'tipo_de_cubierta', 'material_cableado', 'longitud_cable_cc_string1',
        'seccion_cable_ac_mm2', 'longitud_cable_ac_m', 'protector_sobretensiones',
        'diferencial_a', 'sensibilidad_ma'
    ]
    columns_to_insert = [f for f in fields if f in data_dict]
    if 'app_user_id' not in columns_to_insert:
        return None, "Error crítico: Falta el app_user_id para crear la instalación."
    values_to_insert = [data_dict[f] for f in columns_to_insert]
    placeholders = ', '.join(['?'] * len(columns_to_insert))
    sql = f"INSERT INTO instalaciones ({', '.join(columns_to_insert)}) VALUES ({placeholders})"
    return _execute_insert(conn, sql, tuple(values_to_insert))

def get_all_instalaciones(conn, app_user_id, ciudad=None):
    """Obtiene todas las instalaciones de un usuario, con filtrado opcional por ciudad."""
    params = [app_user_id]
    sql = "SELECT id, descripcion, fecha_creacion, provincia, localidad FROM instalaciones WHERE app_user_id = ?"
    if ciudad:
        sql += " AND lower(localidad) LIKE ?"
        params.append(f"%{ciudad.lower()}%")
    sql += " ORDER BY fecha_creacion DESC"
    return _execute_select(conn, sql, tuple(params))

def get_instalacion_completa(conn, instalacion_id, app_user_id):
    """Obtiene todos los datos de una instalación específica, verificando que pertenece al usuario."""
    sql = """
    SELECT
        I.*,
        U.nombre as cliente_nombre, U.apellidos as cliente_apellidos, U.dni as cliente_dni,
        P.nombre_razon_social as promotor_nombre, P.dni_cif as promotor_cif,
        INS.nombre_empresa as instalador_empresa, INS.cif_empresa as instalador_cif
    FROM instalaciones I
    LEFT JOIN clientes U ON I.cliente_id = U.id
    LEFT JOIN promotores P ON I.promotor_id = P.id
    LEFT JOIN instaladores INS ON I.instalador_id = INS.id
    WHERE I.id = ? AND I.app_user_id = ?
    """
    return _execute_select(conn, sql, (instalacion_id, app_user_id), one=True)

def update_instalacion(conn, instalacion_id, app_user_id, data_dict):
    """Actualiza una instalación, verificando que pertenece al usuario."""
    fields = [
        'descripcion', 'cliente_id', 'promotor_id', 'instalador_id',
        'direccion_emplazamiento', 'tipo_via', 'nombre_via', 'numero_via', 'piso_puerta',
        'codigo_postal', 'localidad', 'provincia', 'referencia_catastral', 'tipo_finca',
        'panel_solar', 'numero_paneles', 'inversor', 'numero_inversores', 'bateria',
        'numero_baterias', 'distribuidora', 'cups', 'potencia_contratada_w',
        'tipo_de_estructura', 'tipo_de_cubierta', 'material_cableado', 'longitud_cable_cc_string1',
        'seccion_cable_ac_mm2', 'longitud_cable_ac_m', 'protector_sobretensiones',
        'diferencial_a', 'sensibilidad_ma'
    ]
    fields_to_update = [f for f in fields if f in data_dict]
    if not fields_to_update:
        return False, "No se proporcionaron campos para actualizar."
    values = [data_dict[f] for f in fields_to_update]
    values.append(instalacion_id)
    values.append(app_user_id)
    set_clause = ', '.join([f"{field} = ?" for field in fields_to_update])
    sql = f"UPDATE instalaciones SET {set_clause} WHERE id = ? AND app_user_id = ?"
    return _execute_update_delete(conn, sql, tuple(values))

def delete_instalacion(conn, instalacion_id, app_user_id):
    """Elimina una instalación, verificando que pertenece al usuario."""
    sql = "DELETE FROM instalaciones WHERE id = ? AND app_user_id = ?"
    return _execute_update_delete(conn, sql, (instalacion_id, app_user_id))

def get_all_from_table(conn, table_name, order_by_column="id", columns="*"):
    # Lista de validación para seguridad
    VALID_TABLES = ["inversores", "paneles_solares", "contadores", "baterias", "tipos_vias", "distribuidoras", "categorias_instalador", "clientes", "promotores", "instaladores", "tipos_finca"]
    if table_name not in VALID_TABLES:
        print(f"!!! INTENTO DE ACCESO A TABLA NO VÁLIDA: {table_name} !!!")
        # Devolvemos una lista vacía para no romper el frontend
        return []

    # Usamos la función de ayuda _execute_select que ya maneja errores
    # y devuelve [] en caso de fallo.
    sql = f"SELECT {columns} FROM {table_name} ORDER BY {order_by_column}"
    
    # La llamada a _execute_select ya es segura.
    # No necesitamos un try/except aquí.
    return _execute_select(conn, sql)

# ... (El resto de tus funciones CRUD pueden ser adaptadas usando las funciones de ayuda _execute_*)
# --- inversores ---
def add_inversor(conn, data_dict):
    fields = ['nombre_inversor', 'potencia_salida_va', 'largo_inversor_mm', 'ancho_inversor_mm',
              'profundo_inversor_mm', 'peso_inversor_kg', 'proteccion_ip_inversor',
              'potencia_max_paneles_w', 'tension_max_entrada_v', 'secciones_ca_recomendado_mm2',
              'monofasico_trifasico', 'corriente_maxima_salida_a', 'magnetotermico_a']
    placeholders = ', '.join(['?'] * len(fields))
    columns = ', '.join(fields)
    values = tuple(data_dict.get(f) for f in fields)
    sql = f"INSERT INTO inversores ({columns}) VALUES ({placeholders})"
    return _execute_insert(conn, sql, values)

def update_inversor(conn, inversor_id, data_dict):
    fields = ['nombre_inversor', 'potencia_salida_va', 'largo_inversor_mm', 'ancho_inversor_mm',
              'profundo_inversor_mm', 'peso_inversor_kg', 'proteccion_ip_inversor',
              'potencia_max_paneles_w', 'tension_max_entrada_v', 'secciones_ca_recomendado_mm2',
              'monofasico_trifasico', 'corriente_maxima_salida_a', 'magnetotermico_a']
    set_clause = ', '.join([f"{field} = ?" for field in fields])
    values = [data_dict.get(f) for f in fields]
    values.append(inversor_id)
    sql = f"UPDATE inversores SET {set_clause} WHERE id = ?"
    return _execute_update_delete(conn, sql, tuple(values))

# --- paneles_solares ---
def add_panel_solar(conn, data_dict):
    fields = ['nombre_panel', 'potencia_pico_w', 'largo_mm', 'ancho_mm', 'profundidad_mm',
              'peso_kg', 'eficiencia_panel_porcentaje', 'tension_circuito_abierto_voc',
              'tecnologia_panel_solar', 'numero_celdas_panel', 'tension_maximo_funcionamiento_v',
              'corriente_maxima_funcionamiento_a', 'fusible_cc_recomendada_a']
    placeholders = ', '.join(['?'] * len(fields))
    columns = ', '.join(fields)
    values = tuple(data_dict.get(f) for f in fields)
    sql = f"INSERT INTO paneles_solares ({columns}) VALUES ({placeholders})"
    return _execute_insert(conn, sql, values)

def update_panel_solar(conn, panel_id, data_dict):
    fields = ['nombre_panel', 'potencia_pico_w', 'largo_mm', 'ancho_mm', 'profundidad_mm',
              'peso_kg', 'eficiencia_panel_porcentaje', 'tension_circuito_abierto_voc',
              'tecnologia_panel_solar', 'numero_celdas_panel', 'tension_maximo_funcionamiento_v',
              'corriente_maxima_funcionamiento_a', 'fusible_cc_recomendada_a']
    set_clause = ', '.join([f"{field} = ?" for field in fields])
    values = [data_dict.get(f) for f in fields]
    values.append(panel_id)
    sql = f"UPDATE paneles_solares SET {set_clause} WHERE id = ?"
    return _execute_update_delete(conn, sql, tuple(values))

def get_panel_by_name(conn, nombre_panel):
    """Obtiene los detalles de un panel solar por su nombre."""
    sql = "SELECT * FROM paneles_solares WHERE nombre_panel = ?"
    return _execute_select(conn, sql, (nombre_panel,), one=True)

def get_inversor_by_name(conn, nombre_inversor):
    """Obtiene los detalles de un inversor por su nombre."""
    sql = "SELECT * FROM inversores WHERE nombre_inversor = ?"
    return _execute_select(conn, sql, (nombre_inversor,), one=True)

def get_bateria_by_name(conn, nombre_bateria):
    """Obtiene los detalles de una batería por su nombre."""
    sql = "SELECT * FROM baterias WHERE nombre_bateria = ?"
    return _execute_select(conn, sql, (nombre_bateria,), one=True)

def get_contador_by_name(conn, nombre_contador):
    """Obtiene los detalles de un contador por su nombre."""
    sql = "SELECT * FROM contadores WHERE nombre_contador = ?"
    return _execute_select(conn, sql, (nombre_contador,), one=True)
# ... (añade funciones similares para batería si es necesario)
# --- contadores ---
def add_contador(conn, data_dict):
    nombre = data_dict.get('nombre_contador')
    sql = "INSERT INTO contadores (nombre_contador) VALUES (?)"
    return _execute_insert(conn, sql, (nombre,))

def update_contador(conn, contador_id, data_dict):
    nombre = data_dict.get('nombre_contador')
    sql = "UPDATE contadores SET nombre_contador = ? WHERE id = ?"
    return _execute_update_delete(conn, sql, (nombre, contador_id))

# --- baterias ---
def add_bateria(conn, data_dict):
    nombre = data_dict.get('nombre_bateria')
    capacidad = data_dict.get('capacidad_kwh')
    try:
        capacidad_float = float(str(capacidad).replace(",", "."))
    except (ValueError, TypeError):
        return None, f"Capacidad '{capacidad}' no es un número válido."
    sql = "INSERT INTO baterias (nombre_bateria, capacidad_kwh) VALUES (?, ?)"
    return _execute_insert(conn, sql, (nombre, capacidad_float))

def update_bateria(conn, bateria_id, data_dict):
    nombre = data_dict.get('nombre_bateria')
    capacidad = data_dict.get('capacidad_kwh')
    try:
        capacidad_float = float(str(capacidad).replace(",", "."))
    except (ValueError, TypeError):
        return False, f"Capacidad '{capacidad}' no es un número válido."
    sql = "UPDATE baterias SET nombre_bateria = ?, capacidad_kwh = ? WHERE id = ?"
    return _execute_update_delete(conn, sql, (nombre, capacidad_float, bateria_id))

def get_catalog_data(conn, catalog_name, order_by_column="id", columns="*"):
    """
    Obtiene todos los datos de una tabla de CATÁLOGO (pública).
    Esta función está restringida a tablas que no contienen datos de usuario.
    """
    # Lista de validación de tablas de CATÁLOGO permitidas.
    VALID_CATALOG_TABLES = [
        "inversores", "paneles_solares", "contadores", "baterias", 
        "tipos_vias", "distribuidoras", "categorias_instalador", "tipos_finca"
    ]
    
    if catalog_name not in VALID_CATALOG_TABLES:
        logging.error(f"SEGURIDAD: Intento de acceso a tabla no catalogada '{catalog_name}' con get_catalog_data.")
        return [] # Devolver lista vacía para prevenir errores en el frontend.

    # Sanitización básica de columnas y ordenación para evitar inyección SQL
    if not all(c.isalnum() or c == '_' or c == '*' for c in columns.replace(',', ' ').split()):
        logging.error(f"SEGURIDAD: Intento de inyección SQL en parámetro 'columns': {columns}")
        return []
        
    if not (order_by_column.isalnum() or order_by_column == '_'):
        logging.error(f"SEGURIDAD: Intento de inyección SQL en parámetro 'order_by_column': {order_by_column}")
        return []

    sql = f"SELECT {columns} FROM {catalog_name} ORDER BY {order_by_column}"
    
    # Usamos nuestra función de ayuda segura que ya maneja errores y logging.
    return _execute_select(conn, sql)



# Punto de entrada para ejecutar la configuración inicial desde la línea de comandos
if __name__ == '__main__':
    logging.info("Ejecutando configuración de la base de datos desde línea de comandos...")
    create_tables()
    populate_initial_data()
    logging.info("Configuración completada.")
