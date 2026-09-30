import sqlite3
import threading
from pathlib import Path
try:
    from config import DATABASE_PATH
except ImportError:
    from backend.config import DATABASE_PATH


_local = threading.local()
_initialized = False
_lock = threading.Lock()


def get_db_connection() -> sqlite3.Connection:
    """Returns a thread-local SQLite connection with Row factory and foreign keys enabled."""
    global _initialized
    if not hasattr(_local, "connection") or _local.connection is None:
        db_path = Path(DATABASE_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(
            str(db_path),
            check_same_thread=False,
            timeout=30.0
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 30000;")
        _local.connection = conn

    # Auto-initialize tables once
    with _lock:
        if not _initialized:
            from .schema import create_tables, seed_default_data
            create_tables(_local.connection)
            seed_default_data(_local.connection)
            _initialized = True

    return _local.connection


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """FastAPI dependency for obtaining a database connection."""
    conn = get_db_connection()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        pass



def init_db():
    """Initializes tables and seeds default demo data."""
    conn = get_db_connection()
    from .schema import create_tables, seed_default_data
    create_tables(conn)
    seed_default_data(conn)
