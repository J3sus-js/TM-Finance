import os
import sqlite3
from contextlib import contextmanager

import pandas as pd


DB_PATH = "/data/control_gastos.db" if os.path.exists("/data") else "control_gastos.db"


def get_connection():
    """Abre una conexión SQLite con claves foráneas activadas."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def _connection():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _value(value):
    return value.isoformat() if hasattr(value, "isoformat") else value


def _rows(query, params=()):
    with _connection() as conn:
        return [dict(row) for row in conn.execute(query, tuple(_value(v) for v in params)).fetchall()]


def initialize_database():
    """Crea las tablas y actualiza columnas compatibles con la versión anterior."""
    with _connection() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS categorias (nombre TEXT PRIMARY KEY)")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS gastos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                monto REAL NOT NULL CHECK (monto > 0),
                categoria TEXT NOT NULL REFERENCES categorias(nombre),
                fecha TEXT NOT NULL,
                descripcion TEXT NOT NULL DEFAULT '',
                metodo_pago TEXT NOT NULL DEFAULT 'Efectivo'
            )
        """)
        gasto_columns = {row["name"] for row in conn.execute("PRAGMA table_info(gastos)")}
        if "metodo_pago" not in gasto_columns:
            conn.execute("ALTER TABLE gastos ADD COLUMN metodo_pago TEXT NOT NULL DEFAULT 'Efectivo'")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS presupuestos (
                categoria TEXT PRIMARY KEY REFERENCES categorias(nombre) ON DELETE CASCADE,
                monto_limite REAL NOT NULL CHECK (monto_limite > 0)
            )
        """)
        budget_columns = {row["name"] for row in conn.execute("PRAGMA table_info(presupuestos)")}
        if "monto_limite" in budget_columns:
            budget_column = "monto_limite"
        elif "limite" in budget_columns:
            budget_column = "limite"
        else:
            raise RuntimeError("La tabla presupuestos no contiene una columna de límite reconocida.")

        conn.execute(f"""
            INSERT OR IGNORE INTO categorias (nombre)
            SELECT DISTINCT categoria FROM gastos WHERE TRIM(COALESCE(categoria, '')) <> ''
        """)
        conn.execute(f"""
            INSERT OR IGNORE INTO categorias (nombre)
            SELECT DISTINCT categoria FROM presupuestos WHERE TRIM(COALESCE(categoria, '')) <> ''
        """)
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_gastos_fecha ON gastos(fecha)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_gastos_categoria ON gastos(categoria)")


def listar_categorias():
    return [row["nombre"] for row in _rows("SELECT nombre FROM categorias ORDER BY nombre")]


def agregar_categoria(nombre):
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("La categoría no puede estar vacía.")
    with _connection() as conn:
        conn.execute("INSERT OR IGNORE INTO categorias (nombre) VALUES (?)", (nombre,))


def eliminar_categoria(nombre):
    with _connection() as conn:
        if conn.execute("SELECT 1 FROM gastos WHERE categoria = ? LIMIT 1", (nombre,)).fetchone():
            raise ValueError("No se puede eliminar una categoría que tiene gastos asociados.")
        conn.execute("DELETE FROM categorias WHERE nombre = ?", (nombre,))


def registrar_gasto(fecha, categoria, descripcion, monto, metodo_pago="Efectivo"):
    if monto <= 0:
        raise ValueError("El monto debe ser mayor a cero.")
    categoria = categoria.strip()
    if not categoria:
        raise ValueError("La categoría es obligatoria.")
    agregar_categoria(categoria)
    with _connection() as conn:
        conn.execute("""
            INSERT INTO gastos (monto, categoria, fecha, descripcion, metodo_pago)
            VALUES (?, ?, ?, ?, ?)
        """, (monto, categoria, _value(fecha), descripcion.strip(), metodo_pago))


def listar_gastos(fecha_inicio=None, fecha_fin=None, categoria=None, metodo_pago=None):
    clauses = ["1 = 1"]
    params = []
    if fecha_inicio:
        clauses.append("fecha >= ?")
        params.append(_value(fecha_inicio))
    if fecha_fin:
        clauses.append("fecha <= ?")
        params.append(_value(fecha_fin))
    if categoria:
        clauses.append("LOWER(categoria) LIKE LOWER(?)")
        params.append(f"%{categoria.strip()}%")
    if metodo_pago and metodo_pago != "Todos":
        clauses.append("metodo_pago = ?")
        params.append(metodo_pago)
    return _rows(f"""
        SELECT id, fecha, categoria, descripcion, monto, metodo_pago
        FROM gastos WHERE {' AND '.join(clauses)}
        ORDER BY fecha DESC, id DESC
    """, params)


def actualizar_gasto(gasto_id, fecha, categoria, descripcion, monto, metodo_pago):
    categoria = categoria.strip()
    if not categoria:
        raise ValueError("La categoría es obligatoria.")
    if monto <= 0:
        raise ValueError("El monto debe ser mayor a cero.")
    agregar_categoria(categoria)
    with _connection() as conn:
        cursor = conn.execute("""
            UPDATE gastos
            SET fecha = ?, categoria = ?, descripcion = ?, monto = ?, metodo_pago = ?
            WHERE id = ?
        """, (_value(fecha), categoria, descripcion.strip(), monto, metodo_pago, gasto_id))
        if cursor.rowcount == 0:
            raise ValueError(f"No se encontró el gasto {gasto_id}.")


def eliminar_gasto(gasto_id):
    with _connection() as conn:
        cursor = conn.execute("DELETE FROM gastos WHERE id = ?", (gasto_id,))
        if cursor.rowcount == 0:
            raise ValueError(f"No se encontró el gasto {gasto_id}.")


def obtener_resumen(mes_inicio, mes_siguiente):
    total = _rows("SELECT COALESCE(SUM(monto), 0) AS total FROM gastos")[0]["total"]
    total_mes = _rows("""
        SELECT COALESCE(SUM(monto), 0) AS total FROM gastos
        WHERE fecha >= ? AND fecha < ?
    """, (mes_inicio, mes_siguiente))[0]["total"]
    categorias = _rows("""
        SELECT categoria, SUM(monto) AS total
        FROM gastos GROUP BY categoria ORDER BY total DESC
    """)
    return float(total), float(total_mes), categorias


def guardar_presupuesto(categoria, limite):
    categoria = categoria.strip()
    if not categoria:
        raise ValueError("La categoría es obligatoria.")
    if limite <= 0:
        raise ValueError("El límite debe ser mayor a cero.")
    agregar_categoria(categoria)
    with _connection() as conn:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(presupuestos)")}
        budget_column = "monto_limite" if "monto_limite" in columns else "limite"
        conn.execute(f"""
            INSERT INTO presupuestos (categoria, {budget_column}) VALUES (?, ?)
            ON CONFLICT(categoria) DO UPDATE SET {budget_column} = excluded.{budget_column}
        """, (categoria, limite))


def listar_presupuestos(mes_inicio, mes_siguiente):
    with _connection() as conn:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(presupuestos)")}
        budget_column = "monto_limite" if "monto_limite" in columns else "limite"
        rows = conn.execute(f"""
            SELECT p.categoria, p.{budget_column} AS limite,
                COALESCE(SUM(g.monto), 0) AS gastado
            FROM presupuestos p
            LEFT JOIN gastos g ON g.categoria = p.categoria
                AND g.fecha >= ? AND g.fecha < ?
            GROUP BY p.categoria, p.{budget_column}
            ORDER BY p.categoria
        """, (_value(mes_inicio), _value(mes_siguiente))).fetchall()
    return [{**dict(row), "limite": float(row["limite"]), "gastado": float(row["gastado"])} for row in rows]


def borrar_datos():
    with _connection() as conn:
        conn.execute("DELETE FROM gastos")
        conn.execute("DELETE FROM presupuestos")


def exportar_gastos():
    return listar_gastos()


def obtener_gastos():
    """Devuelve los gastos como DataFrame, además de la API usada por app.py."""
    with _connection() as conn:
        return pd.read_sql_query(
            "SELECT id, monto, categoria, fecha, descripcion, metodo_pago FROM gastos ORDER BY fecha DESC, id DESC",
            conn,
        )