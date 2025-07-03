# app/db/database.py
import sqlite3
import psycopg2
import json
import os

# Obtener la ruta absoluta del directorio donde está este archivo (db/database.py)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Construir la ruta al archivo de la base de datos
DATABASE_PATH = os.path.join(BASE_DIR, 'instalaciones.db') # Renombrado para claridad

# NUEVA FUNCIÓN DE CONEXIÓN
def connect_db():
    """Se conecta a PostgreSQL si DATABASE_URL está definida, si no, a SQLite."""
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        # Estamos en producción (Render)
        try:
            conn = psycopg2.connect(database_url)
            # Para que devuelva dicts en lugar de tuplas, como sqlite3.Row
            # Necesitarás adaptar tus funciones o usar un cursor_factory
            # from psycopg2.extras import RealDictCursor
            # conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
            # ¡ATENCIÓN! El código que recupera datos podría necesitar ajustes
            # ya que el objeto cursor de psycopg2 es diferente al de sqlite3.
            # Por simplicidad, por ahora no usamos RealDictCursor, pero tenlo en mente.
            return conn
        except psycopg2.OperationalError as e:
            print(f"Error al conectar a PostgreSQL: {e}")
            raise
    else:
        # Estamos en local
        conn = sqlite3.connect('mi_base_de_datos.db')
        conn.row_factory = sqlite3.Row # Esto es lo que permite acceder por nombre de columna
        return conn

# Adapta el resto de tus funciones. La sintaxis SQL para SELECT/INSERT/UPDATE
# es mayormente compatible, PERO los placeholders cambian:
# SQLite usa:  ?
# psycopg2 usa: %s

# Ejemplo:
def add_usuario(conn, nombre, apellidos, dni, direccion):
    cursor = conn.cursor()
    sql_insert = """
        INSERT INTO Usuarios (nombre, apellidos, dni, direccion)
        VALUES (%s, %s, %s, %s) RETURNING id; 
    """ # Usamos %s y RETURNING id
    try:
        # El segundo argumento debe ser una tupla
        cursor.execute(sql_insert, (nombre, apellidos, dni, direccion))
        new_id = cursor.fetchone()[0]
        conn.commit()
        return new_id, "Usuario creado"
    except (Exception, psycopg2.Error) as error:
        print("Error al insertar usuario:", error)
        conn.rollback()
        return None, str(error)
    finally:
        cursor.close()


def connect_db(): # No necesita el argumento db_path si DATABASE_PATH es global aquí
    """Conecta a la base de datos SQLite."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row # Para acceder a las columnas por nombre
    return conn

def create_tables():
    """Crea las tablas si no existen."""
    # (Tu código de create_tables aquí, sin cambios significativos,
    # solo asegúrate que llama a connect_db() sin argumentos)
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        apellidos TEXT NOT NULL,
        dni TEXT UNIQUE NOT NULL,
        direccion TEXT
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Promotores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_razon_social TEXT NOT NULL,
        apellidos TEXT, -- Opcional si es empresa
        direccion_fiscal TEXT NOT NULL,
        dni_cif TEXT UNIQUE NOT NULL
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Instaladores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_empresa TEXT NOT NULL,
        direccion_empresa TEXT NOT NULL,
        cif_empresa TEXT UNIQUE NOT NULL,
        nombre_tecnico TEXT,
        competencia_tecnico TEXT
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Instalaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        descripcion TEXT,
        usuario_id INTEGER,
        promotor_id INTEGER,
        instalador_id INTEGER,
        datos_tecnicos_json TEXT,
        FOREIGN KEY (usuario_id) REFERENCES Usuarios(id) ON DELETE SET NULL, -- Opcional: ON DELETE SET NULL o RESTRICT
        FOREIGN KEY (promotor_id) REFERENCES Promotores(id) ON DELETE SET NULL,
        FOREIGN KEY (instalador_id) REFERENCES Instaladores(id) ON DELETE SET NULL
    )''') # Añadido ON DELETE SET NULL como ejemplo, decide la política

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Inversores (
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
    )''')

    # cursor.execute('''DROP TABLE IF EXISTS PanelesSolares''') # Considera si siempre quieres dropear
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS PanelesSolares (
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
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Contadores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_contador TEXT NOT NULL UNIQUE
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Baterias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_bateria TEXT NOT NULL UNIQUE,
        capacidad_kwh REAL
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS TiposVias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_tipo_via TEXT NOT NULL UNIQUE
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Distribuidoras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_distribuidora TEXT,
        nombre_distribuidora TEXT NOT NULL UNIQUE
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS CategoriasInstalador (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_categoria TEXT NOT NULL UNIQUE
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS TiposFinca (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_tipo_finca TEXT NOT NULL UNIQUE
    )''')

    conn.commit()
    conn.close()
    populate_initial_product_data()
    print("Tablas creadas o ya existentes.")


def populate_initial_product_data():
    """Puebla las tablas de catálogo con datos iniciales si es necesario."""
    # (Tu código de populate_initial_product_data aquí, sin cambios significativos,
    # solo asegúrate que llama a connect_db() sin argumentos)
    conn = connect_db()
    cursor = conn.cursor()

    inversores_data = [
        ('Huawei SUN2000-2KTL-L1', 2000, 365, 365, 156, 12, 'IP65', 3000, 600, 2.5, 'Monofásico', 8.695652174, 10),
        ('Huawei SUN2000-3KTL-L1', 3000, 365, 365, 156, 12, 'IP65', 4500, 600, 4, 'Monofásico', 13.04347826, 16),
        ('Huawei SUN2000-4KTL-L1', 4000, 365, 365, 156, 12, 'IP65', 6000, 600, 6, 'Monofásico', 17.39130435, 20),
        ('Huawei SUN2000-5KTL-L1', 5000, 365, 365, 156, 12, 'IP65', 7500, 600, 10, 'Monofásico', 21.73913043, 25),
        ('Huawei SUN2000-6KTL-L1', 6000, 365, 365, 156, 12, 'IP65', 9000, 600, 10, 'Monofásico', 26.08695652, 32),
        ('SAJ H1 6kW', 6000, 470, 470, 190, 23, 'IP65', 9000, 600, 10, 'Monofásico', 26.08695652, 32),
        ('Huawei SUN2000-3KTL-M1', 3000, 525, 470, 146.5, 17, 'IP65', 4500, 1100, 2.5, 'Trifásico', 4.330127019, 10),
        ('Huawei SUN2000-4KTL-M1', 4000, 525, 470, 146.5, 17, 'IP65', 6000, 1100, 2.5, 'Trifásico', 5.773502692, 10),
        ('Huawei SUN2000-5KTL-M1', 5000, 525, 470, 146.5, 17, 'IP65', 7500, 1100, 2.5, 'Trifásico', 7.216878365, 10),
        ('Huawei SUN2000-6KTL-M1', 6000, 525, 470, 146.5, 17, 'IP65', 9000, 1100, 2.5, 'Trifásico', 8.660254038, 10),
        ('Huawei SUN2000-8KTL-M1', 8000, 525, 470, 146.5, 17, 'IP65', 12000, 1100, 4, 'Trifásico', 11.54700538, 16),
        ('Huawei SUN2000-10KTL-M1', 10000, 525, 470, 146.5, 17, 'IP65', 15000, 1100, 4, 'Trifásico', 14.43375673, 16),
        ('Huawei SUN2000-20KTL-M5', 20000, 546, 460, 228, 21, 'IP66', 30000, 1100, 10, 'Trifásico', 28.86751346, 32)
    ]
    for inv_data in inversores_data:
        try:
            cursor.execute('''INSERT OR IGNORE INTO Inversores (nombre_inversor, potencia_salida_va, largo_inversor_mm, ancho_inversor_mm, profundo_inversor_mm, peso_inversor_kg, proteccion_ip_inversor, potencia_max_paneles_w, tension_max_entrada_v, secciones_ca_recomendado_mm2, monofasico_trifasico, corriente_maxima_salida_a, magnetotermico_a) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', inv_data)
        except sqlite3.Error as e: print(f"Error al insertar inversor {inv_data[0]}: {e}")

    paneles_solares_data = [
        ('Jinergy 450Wp', 450, 2094, 1038, 35, 23.3, 22.0, 49.90, 'Monocristalino', 144, 41.35, 10.89, 16),
        ('Jinergy 550Wp', 550, 2278, 1134, 35, 27.2, 21.29, 49.97, 'Monocristalino', 144, 41.98, 13.12, 16),
        ('Risen Black 450Wp', 450, 1800, 1134, 30, 22, 22.3, 38.05, 'Monocristalino', 108, 31.44, 13.08, 16),
        ('Jinko Oficial 550Wp', 550, 2278, 1134, 30, 32, 21.29, 50.11, 'Monocristalino', 144, 41.51, 13.25, 16),
        ('Jinko Monstar C2 450W', 450, 1722, 1134, 30, 20.5, 23, 40.69, 'Monocristalino', 108, 33.7, 13.26, 16)
    ]
    for panel_data in paneles_solares_data:
        try:
            cursor.execute('''INSERT OR IGNORE INTO PanelesSolares (nombre_panel, potencia_pico_w, largo_mm, ancho_mm, profundidad_mm, peso_kg, eficiencia_panel_porcentaje, tension_circuito_abierto_voc, tecnologia_panel_solar, numero_celdas_panel, tension_maximo_funcionamiento_v, corriente_maxima_funcionamiento_a, fusible_cc_recomendada_a) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', panel_data)
        except sqlite3.Error as e: print(f"Error al insertar panel solar {panel_data[0]}: {e}")

    contadores_data = [
        ('DDSU666-H',), ('DDSU666',), ('DTSU666-H',), ('DTSU666',)
    ]
    for cont_data in contadores_data:
        try:
            cursor.execute('''INSERT OR IGNORE INTO Contadores (nombre_contador) VALUES (?)''', cont_data)
        except sqlite3.Error as e: print(f"Error al insertar contador {cont_data[0]}: {e}")

    baterias_data = [
        ('No hay almacenamiento', 0), ('Pylontech UP2500', 2.84), ('Pylontech US2000', 2.4),
        ('Pylontech US3000C', 3.552), ('Pylontech US5000', 4.8), ('Luna 5kWh', 5),
        ('Luna 10kWh', 10), ('Luna 15kWh', 15)
    ]
    for bat_data in baterias_data:
        try:
            cursor.execute('''INSERT OR IGNORE INTO Baterias (nombre_bateria, capacidad_kwh) VALUES (?, ?)''', bat_data)
        except sqlite3.Error as e: print(f"Error al insertar batería {bat_data[0]}: {e}")

    tipos_vias_data = [
        ('CALLE',), ('ACCESO',), ('ACUEDUCTO',), ('AERODROMO',), ('AEROPUERTO',), ('ALAMEDA',),
        ('ALMACEN',), ('ALTO',), ('APARTAMENTO',), ('ARROYO',), ('AUTOVIA',), ('AVENIDA',),
        ('BAJADA',), ('BARRANCO',), ('BARRIADA',), ('BARRIO',), ('BASILICA',), ('BLOQUE',),
        ('BULEVAR',), ('CALLEJA',), ('CALLEJON',), ('CAMINO',), ('CAMPAMENTO',), ('CANAL',),
        ('CANTON',), ('CAÑADA',), ('CARRETERA',), ('CARRIL',), ('CERRO',), ('COLONIA',),
        ('COSTANILLA',), ('CUESTA',), ('DEHESA',), ('FINCA',), ('GLORIETA',), ('GRAN VIA',),
        ('PARAJE',), ('PARCELA',), ('PARQUE',), ('PASADIZO',), ('PASAJE',), ('PASEO',),
        ('PLAZA',), ('PLAZUELA',), ('POBLADO',), ('POLIGONO',), ('RINCON',), ('RINCONADA',),
        ('RONDA',), ('ROTONDA',), ('SECTOR',), ('SENDA',), ('TRASERA',), ('TRAVESIA',),
        ('URBANIZACION',), ('VEREDA',), ('VIA',)
    ]
    for via_data in tipos_vias_data:
        try:
            cursor.execute('''INSERT OR IGNORE INTO TiposVias (nombre_tipo_via) VALUES (?)''', via_data)
        except sqlite3.Error as e: print(f"Error al insertar tipo de vía {via_data[0]}: {e}")

    distribuidoras_data = [
        ('0021', 'I-DE REDES ELÉCTRICAS INTELIGENTES'), ('0022', 'LFD DISTRIBUCIÓN ELECTRICIDAD'),
        ('0026', 'HIDROCANTÁBRICO DISTRIBUCIÓN ELÉCTRICA'), ('0483', 'DISTRIBUCIÓN ELÉCTRICA DEL TAJUÑA'),
        ('0494', 'DISTRIBUCIÓN ELÉCTRICA DEL POZO DEL TIO RAIMUNDO, S.L.U'),
        ('0514', 'HIDROELÉCTRICA VEGA, S.A.'), (None, 'ES UNA INSTALACIÓN AISLADA')
    ]

    for dist_data in distribuidoras_data:
        try:
            cursor.execute('''INSERT OR IGNORE INTO Distribuidoras (codigo_distribuidora, nombre_distribuidora) VALUES (?, ?)''', dist_data)
        except sqlite3.Error as e: print(f"Error al insertar distribuidora {dist_data[1]}: {e}")

    categorias_instalador_data = [
        ('Básica',), ('Especialista',)
    ]
    for cat_data in categorias_instalador_data:
        try:
            cursor.execute('''INSERT OR IGNORE INTO CategoriasInstalador (nombre_categoria) VALUES (?)''', cat_data)
        except sqlite3.Error as e: print(f"Error al insertar categoría de instalador {cat_data[0]}: {e}")

        tipos_finca_data = [
        ('Vivienda unifamiliar',),
        ('Vivienda plurifamiliar (bloque)',),
        ('Nave industrial',),
        ('Edificio de oficinas',),
        ('Local comercial',),
        ('Explotación agrícola/ganadera',),
        ('Terreno/Solar (Huerto Solar)',),
        ('Otro',),
    ]
    for tf_data in tipos_finca_data:
        try:
            cursor.execute('''INSERT OR IGNORE INTO TiposFinca (nombre_tipo_finca) VALUES (?)''', tf_data)
        except sqlite3.Error as e: print(f"Error al insertar tipo de finca {tf_data[0]}: {e}")

    conn.commit()
    conn.close()
    print("Datos iniciales de productos poblados (si no existían).")

# --- Funciones CRUD ---
# Todas las funciones CRUD ahora aceptarán 'conn' como primer argumento
# y no llamarán a connect_db() internamente. La conexión se manejará
# desde los endpoints de la API.

# --- Usuarios ---
def add_usuario(conn, nombre, apellidos, dni, direccion):
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Usuarios (nombre, apellidos, dni, direccion) VALUES (?, ?, ?, ?)",
                       (nombre, apellidos, dni, direccion))
        conn.commit()
        return cursor.lastrowid, "Usuario creado correctamente."
    except sqlite3.IntegrityError:
        return None, f"El DNI {dni} ya existe."
    except sqlite3.Error as e:
        return None, f"Error de base de datos: {e}"

def get_all_usuarios(conn):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Usuarios ORDER BY nombre, apellidos") # Devolver todos los campos
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Error al obtener usuarios: {e}")
        return []

def get_usuario_by_id(conn, usuario_id):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Usuarios WHERE id = ?", (usuario_id,))
        usuario = cursor.fetchone()
        return dict(usuario) if usuario else None
    except sqlite3.Error as e:
        print(f"Error al obtener usuario por ID: {e}")
        return None

def update_usuario(conn, usuario_id, nombre, apellidos, dni, direccion):
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE Usuarios SET nombre = ?, apellidos = ?, dni = ?, direccion = ? WHERE id = ?",
                       (nombre, apellidos, dni, direccion, usuario_id))
        conn.commit()
        if cursor.rowcount == 0:
            return False, "Usuario no encontrado o datos sin cambios."
        return True, "Usuario actualizado correctamente."
    except sqlite3.IntegrityError:
        return False, f"El DNI {dni} ya existe para otro usuario."
    except sqlite3.Error as e:
        return False, f"Error de base de datos: {e}"

def delete_usuario(conn, usuario_id):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Instalaciones WHERE usuario_id = ?", (usuario_id,))
        if cursor.fetchone()[0] > 0:
            return False, "El usuario está asignado a una o más instalaciones y no puede ser eliminado."
        cursor.execute("DELETE FROM Usuarios WHERE id = ?", (usuario_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return False, "Usuario no encontrado."
        return True, "Usuario eliminado correctamente."
    except sqlite3.Error as e:
        return False, f"Error de base de datos: {e}"

# --- Promotores ---
def add_promotor(conn, nombre_razon_social, apellidos, direccion_fiscal, dni_cif):
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Promotores (nombre_razon_social, apellidos, direccion_fiscal, dni_cif) VALUES (?, ?, ?, ?)",
                       (nombre_razon_social, apellidos, direccion_fiscal, dni_cif))
        conn.commit()
        return cursor.lastrowid, "Promotor creado correctamente."
    except sqlite3.IntegrityError:
        return None, f"El DNI/CIF {dni_cif} ya existe."
    except sqlite3.Error as e:
        return None, f"Error de base de datos: {e}"

def get_all_promotores(conn):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Promotores ORDER BY nombre_razon_social")
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Error al obtener promotores: {e}")
        return []

def get_promotor_by_id(conn, promotor_id):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Promotores WHERE id = ?", (promotor_id,))
        promotor = cursor.fetchone()
        return dict(promotor) if promotor else None
    except sqlite3.Error as e:
        print(f"Error al obtener promotor por ID: {e}")
        return None

def update_promotor(conn, promotor_id, nombre_razon_social, apellidos, direccion_fiscal, dni_cif):
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE Promotores SET nombre_razon_social = ?, apellidos = ?, direccion_fiscal = ?, dni_cif = ? WHERE id = ?",
                       (nombre_razon_social, apellidos, direccion_fiscal, dni_cif, promotor_id))
        conn.commit()
        if cursor.rowcount == 0:
            return False, "Promotor no encontrado o datos sin cambios."
        return True, "Promotor actualizado correctamente."
    except sqlite3.IntegrityError:
        return False, f"El DNI/CIF {dni_cif} ya existe para otro promotor."
    except sqlite3.Error as e:
        return False, f"Error de base de datos: {e}"

def delete_promotor(conn, promotor_id):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Instalaciones WHERE promotor_id = ?", (promotor_id,))
        if cursor.fetchone()[0] > 0:
            return False, "El promotor está asignado a una o más instalaciones y no puede ser eliminado."
        cursor.execute("DELETE FROM Promotores WHERE id = ?", (promotor_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return False, "Promotor no encontrado."
        return True, "Promotor eliminado correctamente."
    except sqlite3.Error as e:
        return False, f"Error de base de datos: {e}"

# --- Instaladores ---
def add_instalador(conn, nombre_empresa, direccion_empresa, cif_empresa, nombre_tecnico, competencia_tecnico):
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Instaladores (nombre_empresa, direccion_empresa, cif_empresa, nombre_tecnico, competencia_tecnico) VALUES (?, ?, ?, ?, ?)",
                       (nombre_empresa, direccion_empresa, cif_empresa, nombre_tecnico, competencia_tecnico))
        conn.commit()
        return cursor.lastrowid, "Instalador creado correctamente."
    except sqlite3.IntegrityError:
        return None, f"El CIF {cif_empresa} ya existe."
    except sqlite3.Error as e:
        return None, f"Error de base de datos: {e}"

def get_all_instaladores(conn):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Instaladores ORDER BY nombre_empresa")
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Error al obtener instaladores: {e}")
        return []

def get_instalador_by_id(conn, instalador_id):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Instaladores WHERE id = ?", (instalador_id,))
        instalador = cursor.fetchone()
        return dict(instalador) if instalador else None
    except sqlite3.Error as e:
        print(f"Error al obtener instalador por ID: {e}")
        return None

def update_instalador(conn, instalador_id, nombre_empresa, direccion_empresa, cif_empresa, nombre_tecnico, competencia_tecnico):
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE Instaladores SET nombre_empresa = ?, direccion_empresa = ?, cif_empresa = ?, nombre_tecnico = ?, competencia_tecnico = ? WHERE id = ?",
                       (nombre_empresa, direccion_empresa, cif_empresa, nombre_tecnico, competencia_tecnico, instalador_id))
        conn.commit()
        if cursor.rowcount == 0:
            return False, "Instalador no encontrado o datos sin cambios."
        return True, "Instalador actualizado correctamente."
    except sqlite3.IntegrityError:
        return False, f"El CIF {cif_empresa} ya existe para otro instalador."
    except sqlite3.Error as e:
        return False, f"Error de base de datos: {e}"

def delete_instalador(conn, instalador_id):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Instalaciones WHERE instalador_id = ?", (instalador_id,))
        if cursor.fetchone()[0] > 0:
            return False, "El instalador está asignado a una o más instalaciones y no puede ser eliminado."
        cursor.execute("DELETE FROM Instaladores WHERE id = ?", (instalador_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return False, "Instalador no encontrado."
        return True, "Instalador eliminado correctamente."
    except sqlite3.Error as e:
        return False, f"Error de base de datos: {e}"

# --- Instalaciones ---
def add_instalacion(conn, descripcion, usuario_id, promotor_id, instalador_id, datos_tecnicos_dict):
    try:
        cursor = conn.cursor()
        datos_tecnicos_str = json.dumps(datos_tecnicos_dict)
        cursor.execute("INSERT INTO Instalaciones (descripcion, usuario_id, promotor_id, instalador_id, datos_tecnicos_json) VALUES (?, ?, ?, ?, ?)",
                       (descripcion, usuario_id, promotor_id, instalador_id, datos_tecnicos_str))
        conn.commit()
        return cursor.lastrowid, "Instalación creada correctamente."
    except sqlite3.Error as e:
        return None, f"Error de base de datos al añadir instalación: {e}"

def get_all_instalaciones(conn): # Para la lista principal
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, descripcion, fecha_creacion FROM Instalaciones ORDER BY fecha_creacion DESC")
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Error al obtener instalaciones: {e}")
        return []

def get_instalacion_completa(conn, instalacion_id):
    try:
        cursor = conn.cursor()
        query = """
        SELECT
            I.id as instalacion_id, I.fecha_creacion, I.descripcion, I.datos_tecnicos_json,
            I.usuario_id, U.nombre as usuario_nombre, U.apellidos as usuario_apellidos, U.dni as usuario_dni, U.direccion as usuario_direccion,
            I.promotor_id, P.nombre_razon_social as promotor_nombre, P.apellidos as promotor_apellidos, P.direccion_fiscal as promotor_direccion, P.dni_cif as promotor_cif,
            I.instalador_id, INS.nombre_empresa as instalador_empresa, INS.direccion_empresa as instalador_direccion, INS.cif_empresa as instalador_cif,
            INS.nombre_tecnico as instalador_tecnico_nombre, INS.competencia_tecnico as instalador_tecnico_competencia
        FROM Instalaciones I
        LEFT JOIN Usuarios U ON I.usuario_id = U.id
        LEFT JOIN Promotores P ON I.promotor_id = P.id
        LEFT JOIN Instaladores INS ON I.instalador_id = INS.id
        WHERE I.id = ?
        """
        cursor.execute(query, (instalacion_id,))
        data = cursor.fetchone()
        if data:
            datos_dict = dict(data)
            if datos_dict.get('datos_tecnicos_json'):
                try:
                    datos_dict['datos_tecnicos'] = json.loads(datos_dict['datos_tecnicos_json'])
                except json.JSONDecodeError:
                    datos_dict['datos_tecnicos'] = {}
            else:
                datos_dict['datos_tecnicos'] = {}
            return datos_dict
        return None
    except sqlite3.Error as e:
        print(f"Error al obtener instalación completa: {e}")
        return None

def update_instalacion(conn, instalacion_id, descripcion, usuario_id, promotor_id, instalador_id, datos_tecnicos_dict):
    try:
        cursor = conn.cursor()
        datos_tecnicos_str = json.dumps(datos_tecnicos_dict)
        cursor.execute("""
            UPDATE Instalaciones 
            SET descripcion = ?, 
                usuario_id = ?, 
                promotor_id = ?,
                instalador_id = ?, 
                datos_tecnicos_json = ?
            WHERE id = ? 
        """, (descripcion, usuario_id, promotor_id, instalador_id, datos_tecnicos_str, instalacion_id))
        # conn.commit() se hará en api_routes.py después de esta llamada
        
        if cursor.rowcount == 0:
            # Esto puede significar que el ID no existía, o que los datos enviados eran idénticos a los existentes
            # y la BD no consideró que hubiera una "actualización".
            # Para ser más precisos, podrías primero verificar si el ID existe.
            cursor.execute("SELECT 1 FROM Instalaciones WHERE id = ?", (instalacion_id,))
            if not cursor.fetchone():
                 return False, f"Instalación con ID {instalacion_id} no encontrada."
            return False, "Datos no cambiaron o instalación no encontrada." # Mensaje un poco ambiguo
        return True, "Instalación actualizada correctamente."
    except sqlite3.Error as e: # Ser más específico con el error de SQLite
        print(f"Error de base de datos al actualizar instalación ID {instalacion_id}: {e}")
        return False, f"Error de base de datos: {e}"
    except Exception as e: # Captura genérica por si json.dumps falla u otro error
        print(f"Error inesperado al actualizar instalación ID {instalacion_id}: {e}")
        return False, f"Error inesperado: {e}"

def delete_instalacion(conn, instalacion_id):
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Instalaciones WHERE id = ?", (instalacion_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return False, "Instalación no encontrada."
        return True, "Instalación eliminada correctamente."
    except sqlite3.Error as e:
        return False, f"Error de base de datos: {e}"


# --- Funciones Genéricas para Productos/Catálogos ---
def get_all_from_table(conn, table_name, order_by_column="id", columns="*"):
    # Validar table_name y columns para seguridad si provienen de input no confiable.
    # Aquí asumimos que son controlados internamente.
    VALID_TABLES = ["Inversores", "PanelesSolares", "Contadores", "Baterias", "TiposVias", "Distribuidoras", "CategoriasInstalador", "Usuarios", "Promotores", "Instaladores"] # Añadí Usuarios, Promotores, Instaladores por si acaso
    if table_name not in VALID_TABLES:
        raise ValueError(f"Tabla no permitida: {table_name}")
    # Validación simple para columns (más robusta podría ser necesaria)
    if not all(c.isalnum() or c == '_' or c == '*' for c in columns.replace(',', ' ').split()):
        raise ValueError(f"Nombres de columna no válidos: {columns}")

    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT {columns} FROM {table_name} ORDER BY {order_by_column}")
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Error al obtener todos de {table_name}: {e}")
        return []

def get_all_db_tipos_finca(conn):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre_tipo_finca FROM TiposFinca ORDER BY nombre_tipo_finca")
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Error al obtener tipos de finca: {e}")
        return []

def get_item_by_id_from_table(conn, table_name, item_id):
    VALID_TABLES_FOR_ID_LOOKUP = ["Inversores", "PanelesSolares", "Contadores", "Baterias"] # tablas con CRUD completo
    if table_name not in VALID_TABLES_FOR_ID_LOOKUP:
        raise ValueError(f"Búsqueda por ID no permitida para tabla: {table_name}")
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name} WHERE id = ?", (item_id,))
        item = cursor.fetchone()
        return dict(item) if item else None
    except sqlite3.Error as e:
        print(f"Error al obtener item por ID de {table_name}: {e}")
        return None

def delete_item_from_table(conn, table_name, item_id):
    VALID_TABLES_FOR_DELETE = ["Inversores", "PanelesSolares", "Contadores", "Baterias"]
    if table_name not in VALID_TABLES_FOR_DELETE:
        # Podrías retornar un error o simplemente no hacer nada si no es una tabla "eliminable"
        return False, f"Eliminación no permitida para la tabla {table_name}."
    try:
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {table_name} WHERE id = ?", (item_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return False, f"Elemento no encontrado en {table_name}."
        return True, f"Elemento de {table_name} eliminado correctamente."
    except sqlite3.Error as e:
        return False, f"Error de BD al eliminar de {table_name}: {e}"

# --- CRUD específico para Productos ---
# Inversores
def add_inversor(conn, data_dict):
    # (Tu add_db_inversor adaptado para tomar un diccionario y devolver (id/None, mensaje))
    fields = ['nombre_inversor', 'potencia_salida_va', 'largo_inversor_mm', 'ancho_inversor_mm',
              'profundo_inversor_mm', 'peso_inversor_kg', 'proteccion_ip_inversor',
              'potencia_max_paneles_w', 'tension_max_entrada_v', 'secciones_ca_recomendado_mm2',
              'monofasico_trifasico', 'corriente_maxima_salida_a', 'magnetotermico_a']
    try:
        cursor = conn.cursor()
        placeholders = ', '.join(['?'] * len(fields))
        columns = ', '.join(fields)
        values = [data_dict.get(f) for f in fields]
        cursor.execute(f"INSERT INTO Inversores ({columns}) VALUES ({placeholders})", values)
        conn.commit()
        return cursor.lastrowid, "Inversor creado."
    except sqlite3.IntegrityError: return None, f"El inversor '{data_dict.get('nombre_inversor')}' ya existe."
    except sqlite3.Error as e: return None, f"Error de BD: {e}"

def update_inversor(conn, inversor_id, data_dict):
    fields = ['nombre_inversor', 'potencia_salida_va', 'largo_inversor_mm', 'ancho_inversor_mm',
              'profundo_inversor_mm', 'peso_inversor_kg', 'proteccion_ip_inversor',
              'potencia_max_paneles_w', 'tension_max_entrada_v', 'secciones_ca_recomendado_mm2',
              'monofasico_trifasico', 'corriente_maxima_salida_a', 'magnetotermico_a']
    try:
        cursor = conn.cursor()
        set_clause = ', '.join([f"{field} = ?" for field in fields])
        values = [data_dict.get(f) for f in fields]
        values.append(inversor_id)
        cursor.execute(f"UPDATE Inversores SET {set_clause} WHERE id = ?", values)
        conn.commit()
        if cursor.rowcount == 0: return False, "Inversor no encontrado o datos sin cambios."
        return True, "Inversor actualizado."
    except sqlite3.IntegrityError: return False, f"El nombre de inversor '{data_dict.get('nombre_inversor')}' ya existe para otro."
    except sqlite3.Error as e: return False, f"Error de BD: {e}"

# PanelesSolares
def add_panel_solar(conn, data_dict):
    fields = ['nombre_panel', 'potencia_pico_w', 'largo_mm', 'ancho_mm', 'profundidad_mm',
              'peso_kg', 'eficiencia_panel_porcentaje', 'tension_circuito_abierto_voc',
              'tecnologia_panel_solar', 'numero_celdas_panel', 'tension_maximo_funcionamiento_v',
              'corriente_maxima_funcionamiento_a', 'fusible_cc_recomendada_a']
    try:
        cursor = conn.cursor()
        placeholders = ', '.join(['?'] * len(fields))
        columns = ', '.join(fields)
        values = [data_dict.get(f) for f in fields]
        cursor.execute(f"INSERT INTO PanelesSolares ({columns}) VALUES ({placeholders})", values)
        conn.commit()
        return cursor.lastrowid, "Panel solar creado."
    except sqlite3.IntegrityError: return None, f"El panel '{data_dict.get('nombre_panel')}' ya existe."
    except sqlite3.Error as e: return None, f"Error de BD: {e}"

def update_panel_solar(conn, panel_id, data_dict):
    fields = ['nombre_panel', 'potencia_pico_w', 'largo_mm', 'ancho_mm', 'profundidad_mm',
              'peso_kg', 'eficiencia_panel_porcentaje', 'tension_circuito_abierto_voc',
              'tecnologia_panel_solar', 'numero_celdas_panel', 'tension_maximo_funcionamiento_v',
              'corriente_maxima_funcionamiento_a', 'fusible_cc_recomendada_a']
    try:
        cursor = conn.cursor()
        set_clause = ', '.join([f"{field} = ?" for field in fields])
        values = [data_dict.get(f) for f in fields]
        values.append(panel_id)
        cursor.execute(f"UPDATE PanelesSolares SET {set_clause} WHERE id = ?", values)
        conn.commit()
        if cursor.rowcount == 0: return False, "Panel no encontrado o datos sin cambios."
        return True, "Panel solar actualizado."
    except sqlite3.IntegrityError: return False, f"El nombre de panel '{data_dict.get('nombre_panel')}' ya existe para otro."
    except sqlite3.Error as e: return False, f"Error de BD: {e}"

# Contadores
def add_contador(conn, data_dict):
    nombre = data_dict.get('nombre_contador')
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Contadores (nombre_contador) VALUES (?)", (nombre,))
        conn.commit()
        return cursor.lastrowid, "Contador creado."
    except sqlite3.IntegrityError: return None, f"El contador '{nombre}' ya existe."
    except sqlite3.Error as e: return None, f"Error de BD: {e}"

def update_contador(conn, contador_id, data_dict):
    nombre = data_dict.get('nombre_contador')
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE Contadores SET nombre_contador = ? WHERE id = ?", (nombre, contador_id))
        conn.commit()
        if cursor.rowcount == 0: return False, "Contador no encontrado o datos sin cambios."
        return True, "Contador actualizado."
    except sqlite3.IntegrityError: return False, f"El nombre de contador '{nombre}' ya existe para otro."
    except sqlite3.Error as e: return False, f"Error de BD: {e}"

# Baterias
def add_bateria(conn, data_dict):
    nombre = data_dict.get('nombre_bateria')
    capacidad = data_dict.get('capacidad_kwh')
    try:
        # Validar capacidad como float
        capacidad_float = float(str(capacidad).replace(",", "."))
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Baterias (nombre_bateria, capacidad_kwh) VALUES (?, ?)", (nombre, capacidad_float))
        conn.commit()
        return cursor.lastrowid, "Batería creada."
    except ValueError: return None, f"Capacidad '{capacidad}' no es un número válido."
    except sqlite3.IntegrityError: return None, f"La batería '{nombre}' ya existe."
    except sqlite3.Error as e: return None, f"Error de BD: {e}"

def update_bateria(conn, bateria_id, data_dict):
    nombre = data_dict.get('nombre_bateria')
    capacidad = data_dict.get('capacidad_kwh')
    try:
        capacidad_float = float(str(capacidad).replace(",", "."))
        cursor = conn.cursor()
        cursor.execute("UPDATE Baterias SET nombre_bateria = ?, capacidad_kwh = ? WHERE id = ?", (nombre, capacidad_float, bateria_id))
        conn.commit()
        if cursor.rowcount == 0: return False, "Batería no encontrada o datos sin cambios."
        return True, "Batería actualizada."
    except ValueError: return False, f"Capacidad '{capacidad}' no es un número válido."
    except sqlite3.IntegrityError: return False, f"El nombre de batería '{nombre}' ya existe para otro."
    except sqlite3.Error as e: return False, f"Error de BD: {e}"

if __name__ == '__main__':
    create_tables()
    # Aquí puedes añadir llamadas para probar tus funciones
    # conn_test = connect_db()
    # print(get_all_usuarios(conn_test))
    # conn_test.close()