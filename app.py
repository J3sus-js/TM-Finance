from datetime import datetime
from contextlib import contextmanager
import sqlite3
import os
import streamlit as st

DB_NAME = "control_gastos.db"

# ==========================================
# CONFIGURACIÓN DE ESTILO Y PÁGINA
# ==========================================
st.set_page_config(
    page_title="Control de Gastos Pro", 
    page_icon="💸", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados para mejorar la apariencia visual
st.markdown("""
    <style>
        .main {
            background-color: #f8f9fa;
        }
        .stMetric {
            background-color: #ffffff;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .css-1d391kg {
            background-color: #ffffff;
        }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# GESTIÓN DE BASE DE DATOS (Backend)
# ==========================================
@contextmanager
def obtener_conexion():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def inicializar_bd():
    with obtener_conexion() as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute('''
            CREATE TABLE IF NOT EXISTS gastos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL DEFAULT (date('now')),
                categoria TEXT NOT NULL,
                descripcion TEXT DEFAULT '',
                monto REAL NOT NULL CHECK(monto > 0),
                metodo_pago TEXT NOT NULL DEFAULT 'Efectivo'
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS presupuestos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                categoria TEXT UNIQUE NOT NULL,
                limite REAL NOT NULL CHECK(limite > 0)
            )
        ''')

inicializar_bd()

# ==========================================
# BARRA LATERAL (Sidebar)
# ==========================================
st.sidebar.markdown("### 🧭 Menú Principal")
menu = st.sidebar.radio(
    "Navegación",
    ["📊 Resumen y Gráficos", "➕ Registrar Gasto", "📋 Historial y Filtros", "🎯 Presupuestos", "⚙️ Administración"],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.info("💡 **Consejo:** Mantén tus presupuestos al día para recibir alertas automáticas.")

# ==========================================
# 1. RESUMEN Y GRÁFICOS
# ==========================================
if menu == "📊 Resumen y Gráficos":
    st.title("📊 Panel General de Finanzas")
    st.markdown("Visualiza el comportamiento histórico de tus finanzas personales de forma rápida.")
    
    with obtener_conexion() as conn:
        cursor = conn.execute("SELECT SUM(monto) AS total FROM gastos")
        total_hist = cursor.fetchone()["total"] or 0.0

        cursor_mes = conn.execute("SELECT SUM(monto) AS total FROM gastos WHERE strftime('%Y-%m', fecha) = ?", (datetime.now().strftime("%Y-%m"),))
        total_mes_actual = cursor_mes.fetchone()["total"] or 0.0

    # Tarjetas de métricas superiores
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.metric(label="💵 Gasto Total Histórico", value=f"${total_hist:,.2f}")
    with col_m2:
        st.metric(label="📅 Gastos del Mes Actual", value=f"${total_mes_actual:,.2f}")

    st.markdown("---")

    col1, col2 = st.columns([1.2, 0.8])

    with col1:
        st.subheader("📈 Distribución por Categoría")
        with obtener_conexion() as conn:
            cursor = conn.execute("SELECT categoria, SUM(monto) AS total FROM gastos GROUP BY categoria ORDER BY total DESC")
            datos_cat = [dict(row) for row in cursor.fetchall()]
        
        if datos_cat:
            chart_data = {row["categoria"]: row["total"] for row in datos_cat}
            st.bar_chart(chart_data)
        else:
            st.info("No hay datos suficientes para generar gráficos todavía.")

    with col2:
        st.subheader("🔍 Desglose Porcentual")
        if datos_cat:
            for cat in datos_cat:
                porcentaje = (cat["total"] / total_hist) * 100 if total_hist > 0 else 0
                st.markdown(f"**{cat['categoria']}**")
                st.text(f"${cat['total']:,.2f} ({porcentaje:.1f}%)")
                st.progress(porcentaje / 100)
        else:
            st.info("Sin registros para desglosar.")

# ==========================================
# 2. REGISTRAR GASTO
# ==========================================
elif menu == "➕ Registrar Gasto":
    st.title("➕ Registrar Nuevo Gasto")
    st.markdown("Ingresa los detalles del movimiento financiero.")

    with st.form("form_gasto", clear_on_submit=True):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            categoria = st.text_input("Categoría (Ej: Supermercado, Alquiler, Ocio)")
            monto = st.number_input("Monto ($)", min_value=0.01, format="%.2f", step=1.0)
        with col_f2:
            fecha = st.date_input("Fecha del Gasto", value=datetime.today())
            metodo_pago = st.selectbox("Método de Pago", ["Efectivo", "Tarjeta de Crédito", "Tarjeta de Débito", "Transferencia"])
        
        descripcion = st.text_area("Descripción (Opcional)", placeholder="Ej: Compra de víveres en el supermercado local...")
        
        submitted = st.form_submit_button("💾 Guardar Gasto en el Sistema", use_container_width=True)
        
        if submitted:
            if not categoria.strip():
                st.error("⚠️ La categoría es obligatoria.")
            else:
                try:
                    with obtener_conexion() as conn:
                        conn.execute('''
                            INSERT INTO gastos (fecha, categoria, descripcion, monto, metodo_pago)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (fecha.strftime("%Y-%m-%d"), categoria.strip(), descripcion.strip(), monto, metodo_pago))
                    st.success("¡Gasto registrado y almacenado con éxito!")
                except Exception as e:
                    st.error(f"Error al guardar en la base de datos: {e}")

# ==========================================
# 3. HISTORIAL Y FILTROS
# ==========================================
elif menu == "📋 Historial y Filtros":
    st.title("📋 Historial Detallado de Gastos")
    
    col_fil1, col_fil2 = st.columns(2)
    with col_fil1:
        cat_filtro = st.text_input("🔍 Filtrar por categoría:")
    with col_fil2:
        metodo_filtro = st.selectbox("💳 Filtrar por método de pago", ["Todos", "Efectivo", "Tarjeta de Crédito", "Tarjeta de Débito", "Transferencia"])
    
    query = "SELECT * FROM gastos WHERE 1=1"
    params = []
    
    if cat_filtro:
        query += " AND categoria COLLATE NOCASE LIKE ?"
        params.append(f"%{cat_filtro.strip()}%")
        
    if metodo_filtro != "Todos":
        query += " AND metodo_pago = ?"
        params.append(metodo_filtro)
        
    query += " ORDER BY fecha DESC, id DESC"
    
    with obtener_conexion() as conn:
        cursor = conn.execute(query, params)
        gastos = [dict(row) for row in cursor.fetchall()]
        
    if gastos:
        st.markdown(f"Mostrando **{len(gastos)}** registros encontrados:")
        
        for g in gastos:
            with st.container():
                cols = st.columns([1.5, 2, 2, 1.5, 1])
                cols[0].markdown(f"**📅 {g['fecha']}**")
                cols[1].markdown(f"🏷️ `{g['categoria']}`")
                cols[2].markdown(f"📝 *{g['descripcion'] if g['descripcion'] else 'Sin descripción'}*")
                cols[3].markdown(f"💰 **${g['monto']:,.2f}** ({g['metodo_pago']})")
                
                if cols[4].button("🗑️ Borrar", key=f"del_{g['id']}"):
                    with obtener_conexion() as conn:
                        conn.execute("DELETE FROM gastos WHERE id = ?", (g['id'],))
                    st.rerun()
                st.divider()
    else:
        st.info("No se encontraron registros que coincidan con los filtros seleccionados.")

# ==========================================
# 4. PRESUPUESTOS
# ==========================================
elif menu == "🎯 Presupuestos":
    st.title("🎯 Control y Gestión de Presupuestos")
    st.markdown("Define los límites máximos de gasto mensual por categoría.")

    with st.form("form_presupuesto", clear_on_submit=True):
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            cat_pres = st.text_input("Categoría a presupuestar")
        with col_p2:
            limite = st.number_input("Límite mensual ($)", min_value=0.01, format="%.2f", step=10.0)
            
        guardar_p = st.form_submit_button("💾 Guardar Presupuesto", use_container_width=True)
        
        if guardar_p:
            if cat_pres.strip():
                with obtener_conexion() as conn:
                    conn.execute('''
                        INSERT INTO presupuestos (categoria, limite) VALUES (?, ?)
                        ON CONFLICT(categoria) DO UPDATE SET limite = ?
                    ''', (cat_pres.strip(), limite, limite))
                st.success(f"¡Presupuesto para '{cat_pres}' actualizado correctamente!")
            else:
                st.error("Debes indicar una categoría válida.")

    st.markdown("---")
    st.subheader("📊 Estado Actual de los Presupuestos (Mes en curso)")
    
    with obtener_conexion() as conn:
        cursor = conn.execute("SELECT * FROM presupuestos")
        presupuestos = cursor.fetchall()
        
    if presupuestos:
        mes_actual = datetime.now().strftime("%Y-%m")
        for p in presupuestos:
            with obtener_conexion() as conn:
                cur_g = conn.execute('''
                    SELECT SUM(monto) as total FROM gastos 
                    WHERE categoria = ? AND strftime('%Y-%m', fecha) = ?
                ''', (p["categoria"], mes_actual))
                res_g = cur_g.fetchone()
                gastado = res_g["total"] if res_g and res_g["total"] else 0.0
                
            limite_p = p["limite"]
            porcentaje = (gastado / limite_p) if limite_p > 0 else 0
            
            st.markdown(f"**Categoría:** {p['categoria']} | **Gastado:** ${gastado:,.2f} / **Límite:** ${limite_p:,.2f}")
            st.progress(min(porcentaje, 1.0))
            
            if gastado > limite_p:
                st.error(f"⚠️ ¡Atención! Has superado el presupuesto por **${gastado - limite_p:,.2f}**.")
            elif gastado >= (limite_p * 0.8):
                st.warning(f"⚠️ ¡Cuidado! Estás cerca de alcanzar el límite (Has consumido el {porcentaje*100:.1f}%).")
            else:
                st.success("✅ Presupuesto bajo control.", icon="🟢")
            st.markdown("")
    else:
        st.info("Aún no has configurado ningún presupuesto mensual.")

# ==========================================
# 5. ADMINISTRACIÓN
# ==========================================
elif menu == "⚙️ Administración":
    st.title("⚙️ Opciones de Administración y Respaldo")
    
    st.subheader("📂 Copias de Seguridad")
    st.markdown("Genera un respaldo seguro de tu base de datos SQLite de forma inmediata.")
    if st.button("🔄 Crear Copia de Seguridad Ahora", use_container_width=True):
        os.makedirs("backups", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = os.path.join("backups", f"control_gastos_backup_{timestamp}.db")
        try:
            import shutil
            shutil.copy2(DB_NAME, backup_name)
            st.success(f"Copia de seguridad guardada con éxito en la ruta: `{backup_name}`")
        except Exception as e:
            st.error(f"Error al generar la copia: {e}")
            
    st.markdown("---")
    st.subheader("📊 Exportación de Datos")
    st.markdown("Descarga todos tus registros de gastos en un archivo estructurado CSV.")
    if st.button("📥 Exportar Datos a CSV", use_container_width=True):
        with obtener_conexion() as conn:
            cursor = conn.execute("SELECT * FROM gastos ORDER BY fecha DESC")
            filas = cursor.fetchall()
        
        import csv
        csv_filename = "reporte_gastos_web.csv"
        with open(csv_filename, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Fecha", "Categoría", "Descripción", "Monto", "Método de Pago"])
            for row in filas:
                writer.writerow([row["id"], row["fecha"], row["categoria"], row["descripcion"], row["monto"], row["metodo_pago"]])
        st.success(f"¡Archivo generado con éxito como `{csv_filename}` en la carpeta del proyecto!")
        