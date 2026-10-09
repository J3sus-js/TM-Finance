from datetime import date
import csv
import io
import streamlit as st
import database as db

METODOS_PAGO = ["Efectivo", "Tarjeta de Crédito", "Tarjeta de Débito", "Transferencia"]


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

def rango_mes_actual():
    hoy = date.today()
    inicio = date(hoy.year, hoy.month, 1)
    siguiente = date(hoy.year + (hoy.month == 12), hoy.month % 12 + 1, 1)
    return inicio, siguiente


db.initialize_database()

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
    
    mes_inicio, mes_siguiente = rango_mes_actual()
    total_hist, total_mes_actual, datos_cat = db.obtener_resumen(mes_inicio, mes_siguiente)

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
            fecha = st.date_input("Fecha del Gasto", value=date.today())
            metodo_pago = st.selectbox("Método de Pago", METODOS_PAGO)

        descripcion = st.text_area("Descripción (Opcional)", placeholder="Ej: Compra de víveres en el supermercado local...")
        
        submitted = st.form_submit_button("💾 Guardar Gasto en el Sistema", use_container_width=True)
        
        if submitted:
            if not categoria.strip():
                st.error("⚠️ La categoría es obligatoria.")
            else:
                try:
                    db.agregar_categoria(categoria)
                    db.registrar_gasto(fecha, categoria, descripcion, monto, metodo_pago)
                    st.success("¡Gasto registrado y almacenado con éxito!")
                except Exception as e:
                    st.error(f"Error al guardar en la base de datos: {e}")

# ==========================================
# 3. HISTORIAL Y FILTROS
# ==========================================
elif menu == "📋 Historial y Filtros":
    st.title("📋 Historial Detallado de Gastos")
    
    col_fil1, col_fil2, col_fil3 = st.columns(3)
    with col_fil1:
        cat_filtro = st.text_input("🔍 Filtrar por categoría:")
    with col_fil2:
        metodo_filtro = st.selectbox("💳 Filtrar por método de pago", ["Todos", *METODOS_PAGO])
    with col_fil3:
        filtrar_fechas = st.checkbox("Filtrar por fechas")
    fecha_inicio = fecha_fin = None
    if filtrar_fechas:
        col_fecha1, col_fecha2 = st.columns(2)
        fecha_inicio = col_fecha1.date_input("Desde", value=date.today().replace(day=1))
        fecha_fin = col_fecha2.date_input("Hasta", value=date.today())
    gastos = db.listar_gastos(fecha_inicio, fecha_fin, cat_filtro, metodo_filtro)
        
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
                    db.eliminar_gasto(g["id"])
                    st.rerun()
                with st.expander(f"Editar gasto #{g['id']}"):
                    with st.form(f"editar_{g['id']}"):
                        metodos_edicion = METODOS_PAGO.copy()
                        if g["metodo_pago"] not in metodos_edicion:
                            metodos_edicion.append(g["metodo_pago"])
                        categoria_edit = st.text_input("Categoría", value=g["categoria"], key=f"cat_{g['id']}")
                        descripcion_edit = st.text_input("Descripción", value=g["descripcion"], key=f"desc_{g['id']}")
                        fecha_edit = st.date_input("Fecha", value=g["fecha"], key=f"fecha_{g['id']}")
                        monto_edit = st.number_input("Monto ($)", min_value=0.01, value=float(g["monto"]), format="%.2f", key=f"monto_{g['id']}")
                        metodo_edit = st.selectbox("Método de pago", metodos_edicion, index=metodos_edicion.index(g["metodo_pago"]), key=f"metodo_{g['id']}")
                        if st.form_submit_button("Guardar cambios"):
                            if categoria_edit.strip():
                                db.agregar_categoria(categoria_edit)
                                db.actualizar_gasto(g["id"], fecha_edit, categoria_edit.strip(), descripcion_edit.strip(), monto_edit, metodo_edit)
                                st.rerun()
                            else:
                                st.error("La categoría es obligatoria.")
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
                db.guardar_presupuesto(cat_pres, limite)
                st.success(f"¡Presupuesto para '{cat_pres}' actualizado correctamente!")
            else:
                st.error("Debes indicar una categoría válida.")

    st.markdown("---")
    st.subheader("📊 Estado Actual de los Presupuestos (Mes en curso)")
    
    mes_inicio, mes_siguiente = rango_mes_actual()
    presupuestos = db.listar_presupuestos(mes_inicio, mes_siguiente)
    if presupuestos:
        for p in presupuestos:
            gastado = p["gastado"]
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
    st.title("⚙️ Administración")

    st.subheader("🏷️ Gestionar categorías")
    nueva_categoria = st.text_input("Nueva categoría")
    if st.button("Añadir categoría"):
        try:
            db.agregar_categoria(nueva_categoria)
            st.success("Categoría guardada.")
            st.rerun()
        except ValueError as error:
            st.error(str(error))
    categorias = db.listar_categorias()
    if categorias:
        categoria_eliminar = st.selectbox("Categoría para eliminar", categorias)
        if st.button("Eliminar categoría seleccionada"):
            try:
                db.eliminar_categoria(categoria_eliminar)
                st.success("Categoría eliminada.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))

    st.divider()
    st.subheader("📊 Exportar datos")
    filas = db.exportar_gastos()
    salida = io.StringIO()
    writer = csv.writer(salida)
    writer.writerow(["ID", "Fecha", "Categoría", "Descripción", "Monto", "Método de Pago"])
    for fila in filas:
        writer.writerow([fila["id"], fila["fecha"], fila["categoria"], fila["descripcion"], fila["monto"], fila["metodo_pago"]])
    st.download_button(
        "📥 Descargar CSV",
        data=salida.getvalue().encode("utf-8-sig"),
        file_name="reporte_gastos.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.divider()
    st.subheader("🧹 Restablecer datos")
    confirmar_reset = st.checkbox("Confirmo que quiero borrar todos los gastos y presupuestos")
    if st.button("Borrar datos", type="primary", disabled=not confirmar_reset):
        db.borrar_datos()
        st.success("Se eliminaron los gastos y presupuestos. Las categorías se conservaron.")
        st.rerun()
        