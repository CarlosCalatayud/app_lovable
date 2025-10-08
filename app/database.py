# app/database.py
import os, logging, time, random
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from contextlib import contextmanager

import psycopg2
from psycopg2 import OperationalError, InterfaceError, DatabaseError
from psycopg2.extras import RealDictCursor
from psycopg2 import pool as psycopool

# pool global (se crea Lazy, tras el fork de gunicorn)
_connection_pool = None

def _ensure_params(dsn: str) -> str:
    """Garantiza sslmode, timeouts y keepalives en la DSN (si faltan)."""
    u = urlparse(dsn)
    q = parse_qs(u.query)

    q.setdefault("sslmode", ["require"])
    q.setdefault("connect_timeout", [os.getenv("DB_CONNECT_TIMEOUT", "5")])
    q.setdefault("application_name", [os.getenv("DB_APP_NAME", "sims-backend")])

    # TCP keepalives
    q.setdefault("keepalives", ["1"])
    q.setdefault("keepalives_idle", [os.getenv("DB_KEEPALIVES_IDLE", "30")])
    q.setdefault("keepalives_interval", [os.getenv("DB_KEEPALIVES_INTERVAL", "10")])
    q.setdefault("keepalives_count", [os.getenv("DB_KEEPALIVES_COUNT", "5")])

    new_q = urlencode(q, doseq=True)
    return urlunparse((u.scheme, u.netloc, u.path, u.params, new_q, u.fragment))

def _init_session(conn):
    """Aplica políticas de sesión para evitar queries/locks interminables."""
    with conn.cursor() as cur:
        cur.execute("SET statement_timeout = '30s'")
        cur.execute("SET idle_in_transaction_session_timeout = '60s'")
        cur.execute("SET lock_timeout = '5s'")

def _create_pool():
    """Crea el pool con reintentos y smoke test (SELECT 1)."""
    global _connection_pool
    if _connection_pool:
        return _connection_pool

    dsn_env = os.environ.get("DATABASE_URL")
    if not dsn_env:
        raise RuntimeError("DATABASE_URL no definido")
    dsn = _ensure_params(dsn_env)

    min_conn = int(os.getenv("DB_POOL_MIN", "1"))
    max_conn = int(os.getenv("DB_POOL_MAX", "8"))
    max_attempts = int(os.getenv("DB_INIT_ATTEMPTS", "6"))

    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            logging.info(f"[DB] Inicializando pool {min_conn}-{max_conn} (intento {attempt}/{max_attempts})…")
            _connection_pool = psycopool.ThreadedConnectionPool(
                min_conn, max_conn, dsn=dsn, cursor_factory=RealDictCursor
            )
            # Smoke test + init de sesión
            conn = _connection_pool.getconn()
            try:
                _init_session(conn)
                with conn.cursor() as cur:
                    cur.execute("SELECT 1;")
                    cur.fetchone()
                logging.info("[DB] Pool inicializado y verificado con SELECT 1")
                return _connection_pool
            finally:
                _connection_pool.putconn(conn)

        except Exception as e:
            last_error = e
            backoff = min(2 ** attempt, 10) + random.uniform(0, 0.5)
            logging.warning(f"[DB] Fallo inicializando pool: {e.__class__.__name__}: {e} → reintento en {backoff:.1f}s")
            time.sleep(backoff)

    raise RuntimeError(f"No se pudo inicializar el pool tras {max_attempts} intentos: {last_error}")

def get_pool():
    return _create_pool()

def get_conn():
    """
    Obtiene una conexión “sana”, reciclando si la del pool está rota.
    Realiza un SELECT 1 de verificación y aplica init de sesión.
    """
    p = get_pool()
    for _ in range(2):  # un reintento rápido si la conexión sale corrupta
        conn = p.getconn()
        try:
            _init_session(conn)
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
            return conn
        except (OperationalError, InterfaceError, DatabaseError) as e:
            logging.warning(f"[DB] Conexión inválida del pool, reciclando: {e}")
            try:
                conn.close()
            except Exception:
                pass
            p.putconn(conn, close=True)
            time.sleep(0.2)
    # último intento (debería ser sano)
    return p.getconn()

def release_conn(conn):
    if conn:
        try:
            get_pool().putconn(conn)
        except Exception as e:
            logging.warning(f"[DB] Error devolviendo conexión al pool: {e}")

def close_pool():
    global _connection_pool
    if _connection_pool:
        try:
            _connection_pool.closeall()
            logging.info("[DB] Pool cerrado")
        finally:
            _connection_pool = None

@contextmanager
def db_cursor():
    """
    Context manager para usar cursor con commit/rollback automático.
    Uso:
      with db_cursor() as cur:
          cur.execute("SELECT 1;")
          row = cur.fetchone()
    """
    conn = None
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        release_conn(conn)
