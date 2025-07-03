# app/db.py
import os
import json
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor # Para que PostgreSQL devuelva dicts

# --- CONFIGURACIÓN Y CONEXIÓN ---

def connect_db():
    """
    Se conecta a PostgreSQL si la variable de entorno DATABASE_URL está definida.
    De lo contrario, se conecta a una base de datos SQLite local.
    """
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        # Modo Producción (Render con PostgreSQL)
        try:
            # Usamos RealDictCursor para que las filas devueltas se comporten como diccionarios,
            # similar a conn.row_factory = sqlite3.Row
            conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
            return conn
        except psycopg2.OperationalError as e:
            print(f"FATAL: No se pudo conectar a la base de datos PostgreSQL: {e}")
            raise
    else:
        # Modo Local (Desarrollo con SQLite)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, 'instalaciones_local.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Permite acceder a las columnas por nombre
        return conn

def is_postgres(conn):
    """Función de ayuda para saber si la conexión es a PostgreSQL."""
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
        '''CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            apellidos TEXT NOT NULL,
            dni TEXT UNIQUE NOT NULL,
            direccion TEXT
        )''',
        '''CREATE TABLE IF NOT EXISTS promotores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_razon_social TEXT NOT NULL,
            apellidos TEXT,
            direccion_fiscal TEXT NOT NULL,
            dni_cif TEXT UNIQUE NOT NULL
        )''',
        '''CREATE TABLE IF NOT EXISTS instaladores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_empresa TEXT NOT NULL,
            direccion_empresa TEXT NOT NULL,
            cif_empresa TEXT UNIQUE NOT NULL,
            nombre_tecnico TEXT,
            competencia_tecnico TEXT
        )''',
        # Para PostgreSQL, el tipo JSONB es más eficiente que TEXT para JSON.
        f'''CREATE TABLE IF NOT EXISTS instalaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            descripcion TEXT,
            usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
            promotor_id INTEGER REFERENCES promotores(id) ON DELETE SET NULL,
            instalador_id INTEGER REFERENCES instaladores(id) ON DELETE SET NULL,
            datos_tecnicos_json {'JSONB' if db_type == 'postgres' else 'TEXT'}
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
        print("Tablas creadas o ya existentes.")
    except (Exception, psycopg2.Error) as error:
        print(f"Error al crear tablas: {error}")
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
        if db_type == 'postgres':
            new_id = cursor.fetchone()['id']
        else: # SQLite
            new_id = cursor.lastrowid
        # conn.commit()
        conn.commit()
        return new_id, "Creado correctamente."
    except (psycopg2.IntegrityError, sqlite3.IntegrityError) as e:
        return None, f"Error de integridad: El registro ya existe o viola una restricción. ({e})"
    except (Exception, psycopg2.Error, sqlite3.Error) as e:
        conn.rollback()
        return None, f"Error de base de datos: {e}"

def _execute_update_delete(conn, sql, params):
    """Función de ayuda para UPDATE/DELETE."""
    db_type = 'postgres' if is_postgres(conn) else 'sqlite'
    placeholder = '%s' if db_type == 'postgres' else '?'
    sql = sql.replace('?', placeholder)
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            rowcount = cursor.rowcount
            conn.commit()
            if rowcount == 0:
                return False, "Elemento no encontrado o los datos no cambiaron."
            return True, "Operación completada exitosamente."
    except (psycopg2.IntegrityError, sqlite3.IntegrityError) as e:
        conn.rollback()
        return False, f"Error de integridad: Viola una restricción. ({e})"
    except (Exception, psycopg2.Error, sqlite3.Error) as e:
        conn.rollback()
        return False, f"Error de base de datos: {e}"

def _execute_select(conn, sql, params=None, one=False):
    """Función de ayuda para sentencias SELECT."""
    db_type = 'postgres' if is_postgres(conn) else 'sqlite'
    placeholder = '%s' if db_type == 'postgres' else '?'
    sql = sql.replace('?', placeholder)
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params or ())
            if one:
                # Esto está bien, devuelve un objeto o None
                return cursor.fetchone()
            else:
                # Esto también está bien, devuelve una lista de objetos
                return cursor.fetchall()
    except (Exception, psycopg2.Error, sqlite3.Error) as e:
        # AQUÍ ESTÁ EL CAMBIO IMPORTANTE
        # Usamos print() porque el logger de Flask no está disponible aquí
        print(f"!!! ERROR EN _execute_select !!! SQL: {sql} | PARAMS: {params} | ERROR: {e}")
        # Si se esperan múltiples resultados, SIEMPRE devolver una lista vacía en caso de error.
        if one:
            return None
        else:
            return [] # NUNCA DEVOLVER None, SIEMPRE UNA LISTA VACÍA

# --- usuarios ---
def add_usuario(conn, nombre, apellidos, dni, direccion):
    sql = "INSERT INTO usuarios (nombre, apellidos, dni, direccion) VALUES (?, ?, ?, ?)"
    return _execute_insert(conn, sql, (nombre, apellidos, dni, direccion))

def get_all_usuarios(conn):
    return _execute_select(conn, "SELECT * FROM usuarios ORDER BY nombre, apellidos")

def update_usuario(conn, usuario_id, nombre, apellidos, dni, direccion):
    sql = "UPDATE usuarios SET nombre = ?, apellidos = ?, dni = ?, direccion = ? WHERE id = ?"
    return _execute_update_delete(conn, sql, (nombre, apellidos, dni, direccion, usuario_id))

def delete_usuario(conn, usuario_id):
    # Primero, comprobar dependencias
    count = _execute_select(conn, "SELECT COUNT(*) as c FROM instalaciones WHERE usuario_id = ?", (usuario_id,), one=True)
    if count and count['c'] > 0:
        return False, "El usuario está asignado a una o más instalaciones y no puede ser eliminado."
    return _execute_update_delete(conn, "DELETE FROM usuarios WHERE id = ?", (usuario_id,))

# ... (Repite el patrón para promotores, instaladores, etc.) ...
# --- promotores ---
def add_promotor(conn, nombre_razon_social, apellidos, direccion_fiscal, dni_cif):
    sql = "INSERT INTO promotores (nombre_razon_social, apellidos, direccion_fiscal, dni_cif) VALUES (?, ?, ?, ?)"
    return _execute_insert(conn, sql, (nombre_razon_social, apellidos, direccion_fiscal, dni_cif))
def get_promotor_by_id(conn, promotor_id):
    # Y esta...
    return _execute_select(conn, "SELECT * FROM promotores WHERE id = ?", (promotor_id,), one=True)
def get_all_promotores(conn):
    return _execute_select(conn, "SELECT * FROM promotores ORDER BY nombre_razon_social, apellidos")
def update_promotor(conn, promotor_id, nombre_razon_social, apellidos, direccion_fiscal, dni_cif):
    sql = "UPDATE promotores SET nombre_razon_social = ?, apellidos = ?, direccion_fiscal = ?, dni_cif = ? WHERE id = ?"
    return _execute_update_delete(conn, sql, (nombre_razon_social, apellidos, direccion_fiscal, dni_cif, promotor_id))
def delete_promotor(conn, promotor_id):
    # Primero, comprobar dependencias
    count = _execute_select(conn, "SELECT COUNT(*) as c FROM instalaciones WHERE promotor_id = ?", (promotor_id,), one=True)
    if count and count['c'] > 0:
        return False, "El promotor está asignado a una o más instalaciones y no puede ser eliminado."
    return _execute_update_delete(conn, "DELETE FROM promotores WHERE id = ?", (promotor_id,))

# --- instaladores ---
def add_instalador(conn, nombre_empresa, direccion_empresa, cif_empresa, nombre_tecnico, competencia_tecnico):
    sql = "INSERT INTO instaladores (nombre_empresa, direccion_empresa, cif_empresa, nombre_tecnico, competencia_tecnico) VALUES (?, ?, ?, ?, ?)"
    return _execute_insert(conn, sql, (nombre_empresa, direccion_empresa, cif_empresa, nombre_tecnico, competencia_tecnico))
def get_all_instaladores(conn):
    return _execute_select(conn, "SELECT * FROM instaladores ORDER BY nombre_empresa")
def update_instalador(conn, instalador_id, nombre_empresa, direccion_empresa, cif_empresa, nombre_tecnico, competencia_tecnico):
    sql = "UPDATE instaladores SET nombre_empresa = ?, direccion_empresa = ?, cif_empresa = ?, nombre_tecnico = ?, competencia_tecnico = ? WHERE id = ?"
    return _execute_update_delete(conn, sql, (nombre_empresa, direccion_empresa, cif_empresa, nombre_tecnico, competencia_tecnico, instalador_id))
def delete_instalador(conn, instalador_id):
    # Primero, comprobar dependencias
    count = _execute_select(conn, "SELECT COUNT(*) as c FROM instalaciones WHERE instalador_id = ?", (instalador_id,), one=True)
    if count and count['c'] > 0:
        return False, "El instalador está asignado a una o más instalaciones y no puede ser eliminado."
    return _execute_update_delete(conn, "DELETE FROM instaladores WHERE id = ?", (instalador_id,))

# --- instalaciones ---
def add_instalacion(conn, descripcion, usuario_id, promotor_id, instalador_id, datos_tecnicos_dict):
    datos_tecnicos_str = json.dumps(datos_tecnicos_dict)
    sql = "INSERT INTO instalaciones (descripcion, usuario_id, promotor_id, instalador_id, datos_tecnicos_json) VALUES (?, ?, ?, ?, ?)"
    return _execute_insert(conn, sql, (descripcion, usuario_id, promotor_id, instalador_id, datos_tecnicos_str))

def get_instalacion_completa(conn, instalacion_id):
    sql = """
    SELECT
        I.id as instalacion_id, I.fecha_creacion, I.descripcion, I.datos_tecnicos_json,
        I.usuario_id, U.nombre as usuario_nombre, U.apellidos as usuario_apellidos, U.dni as usuario_dni, U.direccion as usuario_direccion,
        I.promotor_id, P.nombre_razon_social as promotor_nombre, P.apellidos as promotor_apellidos, P.direccion_fiscal as promotor_direccion, P.dni_cif as promotor_cif,
        I.instalador_id, INS.nombre_empresa as instalador_empresa, INS.direccion_empresa as instalador_direccion, INS.cif_empresa as instalador_cif,
        INS.nombre_tecnico as instalador_tecnico_nombre, INS.competencia_tecnico as instalador_tecnico_competencia
    FROM instalaciones I
    LEFT JOIN usuarios U ON I.usuario_id = U.id
    LEFT JOIN promotores P ON I.promotor_id = P.id
    LEFT JOIN instaladores INS ON I.instalador_id = INS.id
    WHERE I.id = ?
    """
    data = _execute_select(conn, sql, (instalacion_id,), one=True)
    if data:
        # En PostgreSQL con JSONB, 'datos_tecnicos_json' ya podría ser un dict.
        # En SQLite, será un string. Normalizamos.
        json_field = data.get('datos_tecnicos_json')
        if isinstance(json_field, str):
            try:
                data['datos_tecnicos'] = json.loads(json_field)
            except (json.JSONDecodeError, TypeError):
                data['datos_tecnicos'] = {}
        elif isinstance(json_field, dict):
             data['datos_tecnicos'] = json_field
        else:
            data['datos_tecnicos'] = {}
    return data

def update_instalacion(conn, instalacion_id, descripcion, usuario_id, promotor_id, instalador_id, datos_tecnicos_dict):
    datos_tecnicos_str = json.dumps(datos_tecnicos_dict)
    sql = """
        UPDATE instalaciones SET descripcion = ?, usuario_id = ?, promotor_id = ?,
        instalador_id = ?, datos_tecnicos_json = ? WHERE id = ?
    """
    return _execute_update_delete(conn, sql, (descripcion, usuario_id, promotor_id, instalador_id, datos_tecnicos_str, instalacion_id))

def get_all_instalaciones(conn):
    """
    Obtiene una lista simplificada de todas las instalaciones para la vista principal.
    """
    # Usamos nuestra función de ayuda _execute_select
    # Asegúrate de que los nombres de tablas y columnas estén en minúsculas.
    sql = "SELECT id, descripcion, fecha_creacion FROM instalaciones ORDER BY fecha_creacion DESC"
    return _execute_select(conn, sql)


def get_all_from_table(conn, table_name, order_by_column="id", columns="*"):
    # Lista de validación para seguridad
    VALID_TABLES = ["inversores", "paneles_solares", "contadores", "baterias", "tipos_vias", "distribuidoras", "categorias_instalador", "usuarios", "promotores", "instaladores", "tipos_finca"]
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


# Punto de entrada para ejecutar la configuración inicial desde la línea de comandos
if __name__ == '__main__':
    print("Ejecutando configuración de la base de datos...")
    create_tables()
    populate_initial_data()
    print("Configuración completada.")