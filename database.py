import os
import sqlite3
from contextlib import contextmanager
from math import isfinite
from numbers import Real

import pandas as pd


DB_PATH = os.getenv("TM_FINANCE_DB_PATH", "/data/control_gastos.db" if os.path.exists("/data") else "control_gastos.db")


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


def _validar_monto_positivo(monto, mensaje):
    if (
        isinstance(monto, bool)
        or not isinstance(monto, Real)
        or not isfinite(monto)
        or monto <= 0
    ):
        raise ValueError(mensaje)


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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transacciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
                tipo TEXT NOT NULL CHECK (tipo IN ('Ingreso', 'Gasto')),
                monto REAL NOT NULL CHECK (monto > 0),
                categoria TEXT NOT NULL,
                fecha TEXT NOT NULL,
                descripcion TEXT NOT NULL DEFAULT '',
                metodo_pago TEXT NOT NULL DEFAULT 'Efectivo'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS presupuestos_usuario (
                usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
                categoria TEXT NOT NULL,
                monto_limite REAL NOT NULL CHECK (monto_limite > 0),
                PRIMARY KEY (usuario_id, categoria)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tokens_restauracion (
                usuario_id INTEGER PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
                token_hash TEXT NOT NULL UNIQUE,
                vence_en TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_transacciones_usuario_fecha ON transacciones(usuario_id, fecha DESC, id DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_transacciones_usuario_tipo ON transacciones(usuario_id, tipo)")
        conn.executemany(
            "INSERT OR IGNORE INTO categorias (nombre) VALUES (?)",
            [(nombre,) for nombre in ("Comida", "Transporte", "Vivienda", "Salud", "Entretenimiento", "Educación", "Servicios", "Otros")],
        )


def crear_usuario(username, email, password_hash):
    username = username.strip()
    email = email.strip().lower()
    if not username or not email or not password_hash:
        raise ValueError("Todos los campos de la cuenta son obligatorios.")
    with _connection() as conn:
        primera_cuenta = conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] == 0
        try:
            cursor = conn.execute(
                "INSERT INTO usuarios (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, password_hash),
            )
        except sqlite3.IntegrityError as error:
            raise ValueError("Ese nombre de usuario o correo ya está registrado.") from error
        usuario_id = cursor.lastrowid
        if primera_cuenta:
            _migrar_datos_heredados(conn, usuario_id)
    return obtener_usuario_por_id(usuario_id)


def _migrar_datos_heredados(conn, usuario_id):
    conn.execute("""
        INSERT INTO transacciones (usuario_id, tipo, monto, categoria, fecha, descripcion, metodo_pago)
        SELECT ?, 'Gasto', monto, categoria, fecha, descripcion, metodo_pago FROM gastos
    """, (usuario_id,))
    budget_columns = {row["name"] for row in conn.execute("PRAGMA table_info(presupuestos)")}
    budget_column = "monto_limite" if "monto_limite" in budget_columns else "limite"
    conn.execute(f"""
        INSERT OR IGNORE INTO presupuestos_usuario (usuario_id, categoria, monto_limite)
        SELECT ?, categoria, {budget_column} FROM presupuestos
    """, (usuario_id,))


def obtener_o_crear_usuario_google(email, nombre, password_hash):
    email = email.strip().lower()
    nombre = nombre.strip()
    if not email or not nombre or not password_hash:
        raise ValueError("Google no proporcionó los datos necesarios para crear la cuenta.")

    with _connection() as conn:
        usuario = conn.execute(
            "SELECT id FROM usuarios WHERE email = ? COLLATE NOCASE", (email,)
        ).fetchone()
        if usuario:
            usuario_id = usuario["id"]
        else:
            primera_cuenta = conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] == 0
            nombre_base = nombre[:40]
            nombre_usuario = nombre_base
            sufijo = 2
            while conn.execute(
                "SELECT 1 FROM usuarios WHERE username = ? COLLATE NOCASE",
                (nombre_usuario,),
            ).fetchone():
                marca = f" {sufijo}"
                nombre_usuario = f"{nombre_base[:40 - len(marca)]}{marca}"
                sufijo += 1

            try:
                cursor = conn.execute(
                    "INSERT INTO usuarios (username, email, password_hash) VALUES (?, ?, ?)",
                    (nombre_usuario, email, password_hash),
                )
            except sqlite3.IntegrityError as error:
                usuario = conn.execute(
                    "SELECT id FROM usuarios WHERE email = ? COLLATE NOCASE", (email,)
                ).fetchone()
                if not usuario:
                    raise ValueError("No se pudo crear la cuenta de Google.") from error
                usuario_id = usuario["id"]
            else:
                usuario_id = cursor.lastrowid
                if primera_cuenta:
                    _migrar_datos_heredados(conn, usuario_id)

    return obtener_usuario_por_id(usuario_id)


def obtener_usuario_por_email(email):
    rows = _rows(
        "SELECT id, username, email, password_hash FROM usuarios WHERE email = ? COLLATE NOCASE",
        (email.strip(),),
    )
    return rows[0] if rows else None


def obtener_usuario_por_id(usuario_id):
    rows = _rows("SELECT id, username, email FROM usuarios WHERE id = ?", (usuario_id,))
    return rows[0] if rows else None


def contar_usuarios():
    return _rows("SELECT COUNT(*) AS total FROM usuarios")[0]["total"]


def guardar_token_restauracion(usuario_id, token_hash, vence_en):
    with _connection() as conn:
        conn.execute("""
            INSERT INTO tokens_restauracion (usuario_id, token_hash, vence_en) VALUES (?, ?, ?)
            ON CONFLICT(usuario_id) DO UPDATE SET token_hash = excluded.token_hash, vence_en = excluded.vence_en
        """, (usuario_id, token_hash, _value(vence_en)))


def obtener_usuario_por_token(token_hash, ahora):
    rows = _rows("""
        SELECT u.id, u.email FROM usuarios u
        JOIN tokens_restauracion t ON t.usuario_id = u.id
        WHERE t.token_hash = ? AND t.vence_en > ?
    """, (token_hash, ahora))
    return rows[0] if rows else None


def cambiar_password(usuario_id, password_hash):
    with _connection() as conn:
        conn.execute("UPDATE usuarios SET password_hash = ? WHERE id = ?", (password_hash, usuario_id))
        conn.execute("DELETE FROM tokens_restauracion WHERE usuario_id = ?", (usuario_id,))


def registrar_transaccion(usuario_id, tipo, fecha, categoria, descripcion, monto, metodo_pago="Efectivo"):
    if tipo not in ("Ingreso", "Gasto"):
        raise ValueError("El tipo debe ser Ingreso o Gasto.")
    _validar_monto_positivo(monto, "El monto debe ser mayor a cero.")
    categoria = categoria.strip()
    if not categoria:
        raise ValueError("La categoría es obligatoria.")
    agregar_categoria(categoria)
    with _connection() as conn:
        conn.execute("""
            INSERT INTO transacciones (usuario_id, tipo, fecha, categoria, descripcion, monto, metodo_pago)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (usuario_id, tipo, _value(fecha), categoria, descripcion.strip(), monto, metodo_pago))


def listar_transacciones(usuario_id, fecha_inicio=None, fecha_fin=None, categoria=None, tipo=None, limite=None):
    if limite is not None and (
        isinstance(limite, bool) or not isinstance(limite, int) or limite < 0
    ):
        raise ValueError("El límite debe ser un entero mayor o igual a cero.")
    clauses = ["usuario_id = ?"]
    params = [usuario_id]
    if fecha_inicio:
        clauses.append("fecha >= ?")
        params.append(_value(fecha_inicio))
    if fecha_fin:
        clauses.append("fecha <= ?")
        params.append(_value(fecha_fin))
    if categoria:
        clauses.append("LOWER(categoria) LIKE LOWER(?)")
        params.append(f"%{categoria.strip()}%")
    if tipo and tipo != "Todos":
        clauses.append("tipo = ?")
        params.append(tipo)
    limit_sql = " LIMIT ?" if limite is not None else ""
    if limite is not None:
        params.append(limite)
    return _rows(f"""
        SELECT id, tipo, monto, categoria, fecha, descripcion, metodo_pago
        FROM transacciones WHERE {' AND '.join(clauses)}
        ORDER BY fecha DESC, id DESC{limit_sql}
    """, params)


def actualizar_transaccion(usuario_id, transaccion_id, fecha, categoria, descripcion, monto, metodo_pago, tipo="Gasto"):
    categoria = categoria.strip()
    if not categoria or tipo not in ("Ingreso", "Gasto"):
        raise ValueError("Indica una categoría y un tipo válido.")
    _validar_monto_positivo(monto, "El monto debe ser mayor a cero.")
    agregar_categoria(categoria)
    with _connection() as conn:
        cursor = conn.execute("""
            UPDATE transacciones
            SET fecha = ?, categoria = ?, descripcion = ?, monto = ?, metodo_pago = ?, tipo = ?
            WHERE id = ? AND usuario_id = ?
        """, (_value(fecha), categoria, descripcion.strip(), monto, metodo_pago, tipo, transaccion_id, usuario_id))
        if cursor.rowcount == 0:
            raise ValueError("No se encontró esa transacción.")


def eliminar_transaccion(usuario_id, transaccion_id):
    with _connection() as conn:
        cursor = conn.execute(
            "DELETE FROM transacciones WHERE id = ? AND usuario_id = ?",
            (transaccion_id, usuario_id),
        )
        if cursor.rowcount == 0:
            raise ValueError("No se encontró esa transacción.")


def obtener_resumen_financiero(usuario_id, mes_inicio, mes_siguiente):
    resumen = _rows("""
        SELECT
            COALESCE(SUM(CASE WHEN tipo = 'Ingreso' THEN monto ELSE 0 END), 0) AS ingresos,
            COALESCE(SUM(CASE WHEN tipo = 'Gasto' THEN monto ELSE 0 END), 0) AS gastos,
            COALESCE(SUM(CASE WHEN tipo = 'Ingreso' AND fecha >= ? AND fecha < ? THEN monto ELSE 0 END), 0) AS ingresos_mes,
            COALESCE(SUM(CASE WHEN tipo = 'Gasto' AND fecha >= ? AND fecha < ? THEN monto ELSE 0 END), 0) AS gastos_mes
        FROM transacciones WHERE usuario_id = ?
    """, (mes_inicio, mes_siguiente, mes_inicio, mes_siguiente, usuario_id))[0]
    categorias = _rows("""
        SELECT categoria, SUM(monto) AS total
        FROM transacciones WHERE usuario_id = ? AND tipo = 'Gasto'
        GROUP BY categoria ORDER BY total DESC
    """, (usuario_id,))
    return {
        **resumen,
        "balance": float(resumen["ingresos"] - resumen["gastos"]),
        "categorias": categorias,
    }


def guardar_presupuesto_usuario(usuario_id, categoria, limite):
    categoria = categoria.strip()
    if not categoria:
        raise ValueError("Indica una categoría y un límite mayor a cero.")
    _validar_monto_positivo(limite, "Indica una categoría y un límite mayor a cero.")
    agregar_categoria(categoria)
    with _connection() as conn:
        conn.execute("""
            INSERT INTO presupuestos_usuario (usuario_id, categoria, monto_limite) VALUES (?, ?, ?)
            ON CONFLICT(usuario_id, categoria) DO UPDATE SET monto_limite = excluded.monto_limite
        """, (usuario_id, categoria, limite))


def listar_presupuestos_usuario(usuario_id, mes_inicio, mes_siguiente):
    return _rows("""
        SELECT p.categoria, p.monto_limite AS limite,
            COALESCE(SUM(t.monto), 0) AS gastado
        FROM presupuestos_usuario p
        LEFT JOIN transacciones t ON t.usuario_id = p.usuario_id
            AND t.categoria = p.categoria AND t.tipo = 'Gasto'
            AND t.fecha >= ? AND t.fecha < ?
        WHERE p.usuario_id = ?
        GROUP BY p.categoria, p.monto_limite ORDER BY p.categoria
    """, (mes_inicio, mes_siguiente, usuario_id))


def borrar_datos_usuario(usuario_id):
    with _connection() as conn:
        conn.execute("DELETE FROM transacciones WHERE usuario_id = ?", (usuario_id,))
        conn.execute("DELETE FROM presupuestos_usuario WHERE usuario_id = ?", (usuario_id,))


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
    _validar_monto_positivo(monto, "El monto debe ser mayor a cero.")
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
    _validar_monto_positivo(monto, "El monto debe ser mayor a cero.")
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
    _validar_monto_positivo(limite, "El límite debe ser mayor a cero.")
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