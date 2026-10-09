from contextlib import contextmanager

import streamlit as st
from sqlalchemy import text


def get_connection():
    return st.connection("postgresql", type="sql")


@contextmanager
def _session():
    session = get_connection().session
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _rows(statement, params=None):
    with _session() as session:
        rows = session.execute(text(statement), params or {}).mappings().all()
    result = [dict(row) for row in rows]
    for row in result:
        for key in ("monto", "limite", "total", "total_categoria", "gastado"):
            if row.get(key) is not None:
                row[key] = float(row[key])
    return result


def _execute(statement, params=None):
    with _session() as session:
        return session.execute(text(statement), params or {})


@st.cache_resource
def initialize_database():
    with _session() as session:
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS categorias (
                nombre TEXT PRIMARY KEY
            )
        """))
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS gastos (
                id BIGSERIAL PRIMARY KEY,
                fecha DATE NOT NULL DEFAULT CURRENT_DATE,
                categoria TEXT NOT NULL,
                descripcion TEXT NOT NULL DEFAULT '',
                monto NUMERIC(12, 2) NOT NULL CHECK (monto > 0),
                metodo_pago TEXT NOT NULL DEFAULT 'Efectivo'
            )
        """))
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS presupuestos (
                id BIGSERIAL PRIMARY KEY,
                categoria TEXT UNIQUE NOT NULL REFERENCES categorias(nombre) ON DELETE CASCADE,
                limite NUMERIC(12, 2) NOT NULL CHECK (limite > 0)
            )
        """))
        session.execute(text("""
            INSERT INTO categorias (nombre)
            SELECT DISTINCT categoria FROM gastos WHERE BTRIM(categoria) <> ''
            ON CONFLICT (nombre) DO NOTHING
        """))


def listar_categorias():
    return [row["nombre"] for row in _rows("SELECT nombre FROM categorias ORDER BY nombre")]


def agregar_categoria(nombre):
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("La categoría no puede estar vacía.")
    _execute("INSERT INTO categorias (nombre) VALUES (:nombre) ON CONFLICT (nombre) DO NOTHING", {"nombre": nombre})


def eliminar_categoria(nombre):
    if _rows("SELECT 1 FROM gastos WHERE categoria = :nombre LIMIT 1", {"nombre": nombre}):
        raise ValueError("No se puede eliminar una categoría que tiene gastos asociados.")
    _execute("DELETE FROM categorias WHERE nombre = :nombre", {"nombre": nombre})


def registrar_gasto(fecha, categoria, descripcion, monto, metodo_pago):
    if monto <= 0:
        raise ValueError("El monto debe ser mayor a cero.")
    _execute("""
        INSERT INTO gastos (fecha, categoria, descripcion, monto, metodo_pago)
        VALUES (:fecha, :categoria, :descripcion, :monto, :metodo_pago)
    """, {
        "fecha": fecha,
        "categoria": categoria.strip(),
        "descripcion": descripcion.strip(),
        "monto": monto,
        "metodo_pago": metodo_pago,
    })


def listar_gastos(fecha_inicio=None, fecha_fin=None, categoria=None, metodo_pago=None):
    clauses = ["TRUE"]
    params = {}
    if fecha_inicio:
        clauses.append("fecha >= :fecha_inicio")
        params["fecha_inicio"] = fecha_inicio
    if fecha_fin:
        clauses.append("fecha <= :fecha_fin")
        params["fecha_fin"] = fecha_fin
    if categoria:
        clauses.append("categoria ILIKE :categoria")
        params["categoria"] = f"%{categoria.strip()}%"
    if metodo_pago and metodo_pago != "Todos":
        clauses.append("metodo_pago = :metodo_pago")
        params["metodo_pago"] = metodo_pago
    return _rows(f"""
        SELECT id, fecha, categoria, descripcion, monto, metodo_pago
        FROM gastos WHERE {' AND '.join(clauses)}
        ORDER BY fecha DESC, id DESC
    """, params)


def actualizar_gasto(gasto_id, fecha, categoria, descripcion, monto, metodo_pago):
    if monto <= 0:
        raise ValueError("El monto debe ser mayor a cero.")
    result = _execute("""
        UPDATE gastos
        SET fecha = :fecha, categoria = :categoria, descripcion = :descripcion,
            monto = :monto, metodo_pago = :metodo_pago
        WHERE id = :gasto_id
    """, {
        "gasto_id": gasto_id,
        "fecha": fecha,
        "categoria": categoria,
        "descripcion": descripcion,
        "monto": monto,
        "metodo_pago": metodo_pago,
    })
    if result.rowcount == 0:
        raise ValueError(f"No se encontró el gasto {gasto_id}.")


def eliminar_gasto(gasto_id):
    result = _execute("DELETE FROM gastos WHERE id = :gasto_id", {"gasto_id": gasto_id})
    if result.rowcount == 0:
        raise ValueError(f"No se encontró el gasto {gasto_id}.")


def obtener_resumen(mes_inicio, mes_siguiente):
    total = _rows("SELECT COALESCE(SUM(monto), 0) AS total FROM gastos")
    total_mes = _rows("""
        SELECT COALESCE(SUM(monto), 0) AS total FROM gastos
        WHERE fecha >= :inicio AND fecha < :siguiente
    """, {"inicio": mes_inicio, "siguiente": mes_siguiente})
    categorias = _rows("""
        SELECT categoria, SUM(monto) AS total
        FROM gastos GROUP BY categoria ORDER BY total DESC
    """)
    return total[0]["total"], total_mes[0]["total"], categorias


def guardar_presupuesto(categoria, limite):
    if limite <= 0:
        raise ValueError("El límite debe ser mayor a cero.")
    agregar_categoria(categoria)
    _execute("""
        INSERT INTO presupuestos (categoria, limite) VALUES (:categoria, :limite)
        ON CONFLICT (categoria) DO UPDATE SET limite = EXCLUDED.limite
    """, {"categoria": categoria.strip(), "limite": limite})


def listar_presupuestos(mes_inicio, mes_siguiente):
    return _rows("""
        SELECT p.categoria, p.limite, COALESCE(SUM(g.monto), 0) AS gastado
        FROM presupuestos p
        LEFT JOIN gastos g ON g.categoria = p.categoria
            AND g.fecha >= :inicio AND g.fecha < :siguiente
        GROUP BY p.categoria, p.limite ORDER BY p.categoria
    """, {"inicio": mes_inicio, "siguiente": mes_siguiente})


def borrar_datos():
    with _session() as session:
        session.execute(text("DELETE FROM gastos"))
        session.execute(text("DELETE FROM presupuestos"))


def exportar_gastos():
    return listar_gastos()