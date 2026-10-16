from datetime import date, datetime, timedelta
import csv
import hashlib
import html
import hmac
import io
import os
import re
import secrets
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import quote

import pandas as pd
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

# Estilos alineados con la identidad visual de TM Finance.
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Sora:wght@500;600;700&display=swap');

        :root {
            color-scheme: light;
            --tm-ink: #26302b;
            --tm-muted: #747e78;
            --tm-accent: #b84837;
            --tm-accent-dark: #963a2d;
            --tm-canvas: #f5f7f4;
            --tm-line: #e3e7df;
            --tm-control-line: #d8e0d7;
            --tm-shadow: rgba(35, 48, 43, .045);
            --tm-positive: #17724c;
            --tm-negative: #b83c34;
            --tm-white: #ffffff;
        }

        html, body, [class*="css"], [data-testid="stAppViewContainer"] {
            font-family: 'Inter', sans-serif;
            color: var(--tm-ink);
        }
        .stApp {
            background: var(--tm-canvas);
        }
        [data-testid="stHeader"] {
            background: transparent;
        }
        [data-testid="stSidebar"] {
            background: var(--tm-white);
            border-right: 1px solid var(--tm-line);
        }
        [data-testid="stSidebar"] > div:first-child {
            padding-top: 1.5rem;
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
            font-family: 'Sora', sans-serif;
            color: var(--tm-ink);
            font-size: 1rem;
            margin-bottom: .75rem;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] label {
            color: var(--tm-muted);
            font-size: .9rem;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] {
            gap: .25rem;
        }
        [data-testid="stMetric"] {
            background: var(--tm-white);
            border: 1px solid var(--tm-line);
            border-radius: 8px;
            padding: 1.05rem 1.15rem;
            box-shadow: 0 5px 18px var(--tm-shadow);
        }
        [data-testid="stMetricLabel"] p {
            color: var(--tm-muted);
            font-size: .82rem;
            font-weight: 500;
        }
        [data-testid="stMetricValue"] {
            color: var(--tm-ink);
            font-family: 'Sora', sans-serif;
            font-size: 1.7rem;
        }
        h1, h2, h3 {
            color: var(--tm-ink);
            font-family: 'Sora', sans-serif !important;
            letter-spacing: 0 !important;
        }
        h1 {
            font-size: 1.85rem !important;
            font-weight: 600 !important;
        }
        h2, h3 {
            font-weight: 600 !important;
        }
        [data-testid="stMarkdownContainer"] p {
            color: var(--tm-muted);
        }
        [data-testid="stBaseButton-primary"] {
            background: var(--tm-accent);
            border-color: var(--tm-accent);
            color: var(--tm-white);
        }
        [data-testid="stBaseButton-primary"]:hover {
            background: var(--tm-accent-dark);
            border-color: var(--tm-accent-dark);
            color: var(--tm-white);
        }
        [data-testid="stBaseButton-secondary"] {
            border-color: var(--tm-control-line);
            color: var(--tm-ink);
            border-radius: 6px;
        }
        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stDateInput"] input,
        [data-testid="stSelectbox"] [data-baseweb="select"] > div,
        [data-testid="stTextArea"] textarea {
            border-color: var(--tm-control-line);
            border-radius: 6px;
            background: var(--tm-white);
            color: var(--tm-ink);
        }
        [data-testid="stProgress"] > div > div > div > div {
            background: var(--tm-accent);
        }
        [data-testid="stAlert"] {
            border-radius: 6px;
        }
        hr {
            border-color: var(--tm-line);
        }
        .tm-brand {
            display: flex;
            align-items: center;
            gap: .7rem;
            margin: 0 .15rem 1.7rem;
        }
        .tm-brand-mark {
            display: grid;
            width: 2.3rem;
            height: 2.3rem;
            place-items: center;
            border-radius: 7px;
            background: var(--tm-accent);
            color: white;
            font: 700 1rem 'Sora', sans-serif;
        }
        .tm-brand-name {
            color: var(--tm-ink);
            font: 600 .9rem 'Sora', sans-serif;
        }
        .tm-brand-caption {
            margin-top: .08rem;
            color: var(--tm-muted);
            font-size: .7rem;
        }
        .tm-page-kicker {
            margin-bottom: .35rem;
            color: var(--tm-accent);
            font-size: .72rem;
            font-weight: 700;
            letter-spacing: .08em;
            text-transform: uppercase;
        }
        .tm-page-subtitle {
            margin: -.3rem 0 1.25rem;
            color: var(--tm-muted);
            font-size: .95rem;
        }
        .tm-auth-brand {
            margin: 2rem 0 .5rem;
            text-align: center;
        }
        .tm-auth-brand .tm-brand-mark {
            width: 2.7rem;
            height: 2.7rem;
            margin: auto auto .75rem;
            font-size: 1.15rem;
        }
        .tm-auth-brand-name {
            color: var(--tm-ink);
            font: 600 1rem 'Sora', sans-serif;
        }
        .tm-auth-caption {
            margin: .3rem 0 1.25rem;
            color: var(--tm-muted);
            font-size: .88rem;
            text-align: center;
        }
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-color: var(--tm-line);
            border-radius: 8px;
            background: var(--tm-white);
        }
        .tm-positive { color: var(--tm-positive); font-weight: 600; }
        .tm-negative { color: var(--tm-negative); font-weight: 600; }
        .tm-muted { color: var(--tm-muted); font-size: .82rem; }

        @media (prefers-color-scheme: dark) {
            :root {
                color-scheme: dark;
                --tm-ink: #edf2ed;
                --tm-muted: #a6b2a9;
                --tm-accent: #ed846d;
                --tm-accent-dark: #d56a55;
                --tm-canvas: #111a16;
                --tm-line: #2d3a32;
                --tm-control-line: #415047;
                --tm-shadow: rgba(0, 0, 0, .2);
                --tm-positive: #66d39b;
                --tm-negative: #ff8b80;
                --tm-white: #1a2520;
            }
            [data-testid="stVegaLiteChart"] svg text {
                fill: var(--tm-muted) !important;
            }
        }

        @media (max-width: 700px) {
            h1 { font-size: 1.55rem !important; }
            [data-testid="stMetricValue"] { font-size: 1.35rem; }
        }
    </style>
""", unsafe_allow_html=True)

def rango_mes_actual():
    hoy = date.today()
    inicio = date(hoy.year, hoy.month, 1)
    siguiente = date(hoy.year + (hoy.month == 12), hoy.month % 12 + 1, 1)
    return inicio, siguiente


PASSWORD_ITERATIONS = 310_000
CATEGORIAS_BASE = ["Comida", "Transporte", "Vivienda", "Salud", "Entretenimiento", "Educación", "Servicios", "Otros"]


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PASSWORD_ITERATIONS).hex()
    return f"pbkdf2_sha256${salt}${digest}"


def verificar_password(password, encoded):
    try:
        algorithm, salt, expected = encoded.split("$", 2)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PASSWORD_ITERATIONS).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def enviar_correo_restauracion(email, token):
    host = os.getenv("SMTP_HOST")
    sender = os.getenv("SMTP_FROM") or os.getenv("SMTP_USER")
    base_url = os.getenv("APP_BASE_URL")
    if not host or not sender or not base_url:
        raise RuntimeError("La recuperación requiere configurar SMTP_HOST, SMTP_FROM y APP_BASE_URL.")

    message = EmailMessage()
    message["Subject"] = "Restablece tu contraseña de TM Finance"
    message["From"] = sender
    message["To"] = email
    link = f"{base_url.rstrip('/')}?reset={quote(token)}"
    message.set_content(f"Usa este enlace para cambiar tu contraseña. Vence en una hora:\n\n{link}\n")

    port = int(os.getenv("SMTP_PORT", "587"))
    if port == 465:
        server = smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=20)
    else:
        server = smtplib.SMTP(host, port, timeout=20)
    with server:
        if port != 465:
            server.starttls(context=ssl.create_default_context())
        username = os.getenv("SMTP_USER")
        password = os.getenv("SMTP_PASSWORD")
        if username and password:
            server.login(username, password)
        server.send_message(message)


def iniciar_sesion(usuario):
    st.session_state["user_id"] = usuario["id"]
    st.session_state["username"] = usuario["username"]


def mostrar_autenticacion():
    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "signup" if db.contar_usuarios() == 0 else "login"

    reset_token = st.query_params.get("reset")
    left, center, right = st.columns([1, 1.15, 1])
    with center:
        st.markdown("""
            <div class="tm-auth-brand">
                <div class="tm-brand-mark">T</div>
                <div class="tm-auth-brand-name">TM Finance</div>
            </div>
            """, unsafe_allow_html=True)

        if reset_token:
            reset_user = db.obtener_usuario_por_token(
                hashlib.sha256(reset_token.encode()).hexdigest(), datetime.utcnow().isoformat()
            )
            with st.container(border=True):
                st.subheader("Nueva contraseña")
                if not reset_user:
                    st.error("El enlace venció o ya fue utilizado. Solicita uno nuevo.")
                    if st.button("Volver al inicio de sesión", use_container_width=True):
                        st.query_params.clear()
                        st.session_state.auth_mode = "login"
                        st.rerun()
                else:
                    with st.form("reset_password"):
                        password = st.text_input("Nueva contraseña", type="password")
                        confirmation = st.text_input("Confirmar contraseña", type="password")
                        submitted = st.form_submit_button("Guardar contraseña", type="primary", use_container_width=True)
                    if submitted:
                        if len(password) < 8:
                            st.error("La contraseña debe tener al menos 8 caracteres.")
                        elif password != confirmation:
                            st.error("Las contraseñas no coinciden.")
                        else:
                            db.cambiar_password(reset_user["id"], hash_password(password))
                            st.query_params.clear()
                            st.session_state.auth_mode = "login"
                            st.success("Contraseña actualizada. Ya puedes iniciar sesión.")
                            st.rerun()
            return

        mode = st.session_state.auth_mode
        if mode == "signup":
            st.markdown('<div class="tm-auth-caption">Crea tu espacio financiero personal</div>', unsafe_allow_html=True)
            with st.container(border=True):
                st.subheader("Crear cuenta")
                with st.form("signup_form"):
                    username = st.text_input("Nombre de usuario", max_chars=40)
                    email = st.text_input("Correo electrónico")
                    password = st.text_input("Contraseña", type="password")
                    confirmation = st.text_input("Confirmar contraseña", type="password")
                    submitted = st.form_submit_button("Crear cuenta", type="primary", use_container_width=True)
                if submitted:
                    if len(username.strip()) < 2:
                        st.error("El nombre de usuario debe tener al menos 2 caracteres.")
                    elif not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email.strip()):
                        st.error("Escribe un correo electrónico válido.")
                    elif len(password) < 8:
                        st.error("La contraseña debe tener al menos 8 caracteres.")
                    elif password != confirmation:
                        st.error("Las contraseñas no coinciden.")
                    else:
                        try:
                            usuario = db.crear_usuario(username, email, hash_password(password))
                            iniciar_sesion(usuario)
                            st.rerun()
                        except ValueError as error:
                            st.error(str(error))
            if st.button("¿Ya tienes cuenta? Inicia sesión", use_container_width=True):
                st.session_state.auth_mode = "login"
                st.rerun()
            return

        if mode == "forgot":
            st.markdown('<div class="tm-auth-caption">Te enviaremos un enlace de un solo uso</div>', unsafe_allow_html=True)
            with st.container(border=True):
                st.subheader("Recuperar contraseña")
                with st.form("forgot_password"):
                    email = st.text_input("Correo electrónico")
                    submitted = st.form_submit_button("Enviar enlace", type="primary", use_container_width=True)
                if submitted:
                    usuario = db.obtener_usuario_por_email(email)
                    try:
                        if usuario:
                            token = secrets.token_urlsafe(32)
                            db.guardar_token_restauracion(
                                usuario["id"], hashlib.sha256(token.encode()).hexdigest(),
                                (datetime.utcnow() + timedelta(hours=1)).isoformat(),
                            )
                            enviar_correo_restauracion(usuario["email"], token)
                        st.success("Si el correo está registrado, recibirás un enlace para restablecer la contraseña.")
                    except (RuntimeError, OSError, smtplib.SMTPException, ValueError) as error:
                        st.error(str(error))
            if st.button("Volver al inicio de sesión", use_container_width=True):
                st.session_state.auth_mode = "login"
                st.rerun()
            return

        st.markdown('<div class="tm-auth-caption">Ingresa para ver tus finanzas</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.subheader("Iniciar sesión")
            with st.form("login_form"):
                email = st.text_input("Correo electrónico")
                password = st.text_input("Contraseña", type="password")
                remember = st.checkbox("Recordarme")
                submitted = st.form_submit_button("Ingresar", type="primary", use_container_width=True)
            if submitted:
                usuario = db.obtener_usuario_por_email(email)
                if usuario and verificar_password(password, usuario["password_hash"]):
                    iniciar_sesion(usuario)
                    st.session_state["remember_me"] = remember
                    st.rerun()
                else:
                    st.error("Correo o contraseña incorrectos.")
        first, second = st.columns(2)
        with first:
            if st.button("¿Olvidaste tu contraseña?", use_container_width=True):
                st.session_state.auth_mode = "forgot"
                st.rerun()
        with second:
            if st.button("Crear cuenta", use_container_width=True):
                st.session_state.auth_mode = "signup"
                st.rerun()


def mostrar_movimiento(transaccion, usuario_id, editable=False):
    tipo = transaccion["tipo"]
    amount_class = "tm-positive" if tipo == "Ingreso" else "tm-negative"
    sign = "+" if tipo == "Ingreso" else "−"
    description = html.escape(transaccion["descripcion"] or tipo)
    category = html.escape(transaccion["categoria"])
    fecha = html.escape(str(transaccion["fecha"]))
    with st.container(border=True):
        columns = st.columns([2.2, 1.5, 1.4, 1.2] if editable else [2.5, 1.6, 1.3, 1.4])
        columns[0].markdown(f"**{description}**<br><span class='tm-muted'>{category}</span>", unsafe_allow_html=True)
        columns[1].markdown(f"<span class='tm-muted'>{fecha}</span>", unsafe_allow_html=True)
        columns[2].markdown(f"<span class='{amount_class}'>{sign} ${transaccion['monto']:,.2f}</span>", unsafe_allow_html=True)
        if editable:
            if columns[3].button("Eliminar", key=f"delete_{transaccion['id']}"):
                db.eliminar_transaccion(usuario_id, transaccion["id"])
                st.rerun()
            with st.expander("Editar movimiento"):
                with st.form(f"edit_{transaccion['id']}"):
                    tipo_edit = st.selectbox("Tipo", ["Gasto", "Ingreso"], index=["Gasto", "Ingreso"].index(tipo))
                    category_edit = st.text_input("Categoría", value=transaccion["categoria"])
                    description_edit = st.text_input("Descripción", value=transaccion["descripcion"])
                    date_edit = st.date_input("Fecha", value=date.fromisoformat(str(transaccion["fecha"])))
                    amount_edit = st.number_input("Monto", min_value=0.01, value=float(transaccion["monto"]), step=1.0)
                    payment_options = METODOS_PAGO.copy()
                    if transaccion["metodo_pago"] not in payment_options:
                        payment_options.append(transaccion["metodo_pago"])
                    payment_edit = st.selectbox("Método de pago", payment_options, index=payment_options.index(transaccion["metodo_pago"]))
                    if st.form_submit_button("Guardar cambios"):
                        db.actualizar_transaccion(
                            usuario_id, transaccion["id"], date_edit, category_edit, description_edit,
                            amount_edit, payment_edit, tipo_edit,
                        )
                        st.rerun()


def mostrar_presupuestos(usuario_id, mes_inicio, mes_siguiente):
    budgets = db.listar_presupuestos_usuario(usuario_id, mes_inicio, mes_siguiente)
    if not budgets:
        st.info("Aún no has configurado presupuestos mensuales.")
        return
    for budget in budgets:
        spent = float(budget["gastado"])
        limit = float(budget["limite"])
        percentage = spent / limit if limit else 0
        st.markdown(f"**{html.escape(budget['categoria'])}** · ${spent:,.2f} de ${limit:,.2f}")
        st.progress(min(percentage, 1.0))
        if percentage >= 1:
            st.error(f"Límite superado por ${spent - limit:,.2f}.")
        elif percentage >= .8:
            st.warning(f"Has usado el {percentage * 100:.0f}% del presupuesto.")


db.initialize_database()

if "user_id" in st.session_state:
    current_user = db.obtener_usuario_por_id(st.session_state.user_id)
    if not current_user:
        st.session_state.clear()
        st.rerun()
else:
    current_user = None

if not current_user:
    mostrar_autenticacion()
    st.stop()

usuario_id = current_user["id"]
mes_inicio, mes_siguiente = rango_mes_actual()
resumen = db.obtener_resumen_financiero(usuario_id, mes_inicio, mes_siguiente)
categorias = db.listar_categorias() or CATEGORIAS_BASE

st.sidebar.markdown("""
    <div class="tm-brand">
        <div class="tm-brand-mark">T</div>
        <div><div class="tm-brand-name">TM Finance</div><div class="tm-brand-caption">Control de gastos</div></div>
    </div>
    """, unsafe_allow_html=True)
st.sidebar.markdown(f"Hola, **{html.escape(current_user['username'])}**")
menu = st.sidebar.radio("Navegación", ["Resumen", "Movimientos", "Presupuestos", "Administración"], label_visibility="collapsed", key="menu")
if st.sidebar.button("Cerrar sesión", use_container_width=True):
    st.session_state.pop("user_id", None)
    st.session_state.pop("username", None)
    st.session_state.pop("remember_me", None)
    st.session_state.auth_mode = "login"
    st.rerun()

if menu == "Resumen":
    st.markdown('<div class="tm-page-kicker">Tu dinero, en perspectiva</div>', unsafe_allow_html=True)
    st.title("Resumen financiero")
    st.markdown('<div class="tm-page-subtitle">Balance y actividad de tus finanzas personales.</div>', unsafe_allow_html=True)
    kpi_balance, kpi_income, kpi_expenses = st.columns(3)
    kpi_balance.metric("Balance total", f"${resumen['balance']:,.2f}")
    kpi_income.metric("🟢 Total ingresos", f"${resumen['ingresos']:,.2f}")
    kpi_expenses.metric("🔴 Total gastos", f"${resumen['gastos']:,.2f}")

    form_column, history_column = st.columns([.9, 1.1], gap="large")
    with form_column:
        st.subheader("Agregar transacción")
        with st.container(border=True):
            with st.form("add_transaction", clear_on_submit=True):
                tipo = st.selectbox("Tipo", ["Gasto", "Ingreso"])
                amount = st.number_input("Monto", min_value=0.01, value=0.01, step=1.0, format="%.2f")
                category = st.selectbox("Categoría", [*categorias, "Nueva categoría..."])
                if category == "Nueva categoría...":
                    category = st.text_input("Nombre de la categoría")
                transaction_date = st.date_input("Fecha", value=date.today())
                description = st.text_input("Descripción", max_chars=120)
                payment_method = st.selectbox("Método de pago", METODOS_PAGO)
                submitted = st.form_submit_button("Agregar transacción", type="primary", use_container_width=True)
            if submitted:
                try:
                    db.registrar_transaccion(usuario_id, tipo, transaction_date, category, description, amount, payment_method)
                    st.success("Transacción agregada.")
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))

    with history_column:
        st.subheader("Movimientos recientes")
        recent = db.listar_transacciones(usuario_id, limite=6)
        if recent:
            for transaction in recent:
                mostrar_movimiento(transaction, usuario_id)
        else:
            st.info("Tus movimientos aparecerán aquí.")
        if st.button("Ver todos los movimientos", use_container_width=True):
            st.session_state["menu"] = "Movimientos"
            st.rerun()

    chart_column, budget_column = st.columns([1.1, .9], gap="large")
    with chart_column:
        st.subheader("Gastos por categoría")
        if resumen["categorias"]:
            chart_data = pd.DataFrame(resumen["categorias"])
            st.vega_lite_chart(chart_data, {
                "mark": {"type": "arc", "innerRadius": 54},
                "encoding": {
                    "theta": {"field": "total", "type": "quantitative"},
                    "color": {"field": "categoria", "type": "nominal", "scale": {"range": ["#17724c", "#d49a25", "#b84837", "#548eb6", "#82934e", "#81728d"]}},
                    "tooltip": [{"field": "categoria", "type": "nominal"}, {"field": "total", "type": "quantitative", "format": "$,.2f"}],
                },
                "view": {"stroke": None},
            }, width="stretch")
        else:
            st.info("Registra gastos para ver el desglose por categoría.")
    with budget_column:
        st.subheader("Presupuestos del mes")
        mostrar_presupuestos(usuario_id, mes_inicio, mes_siguiente)

elif menu == "Movimientos":
    st.markdown('<div class="tm-page-kicker">Historial de actividad</div>', unsafe_allow_html=True)
    st.title("Movimientos")
    filters = st.columns([1.2, 1, 1, 1])
    search_category = filters[0].text_input("Categoría")
    type_filter = filters[1].selectbox("Tipo", ["Todos", "Ingreso", "Gasto"])
    date_filter = filters[2].checkbox("Filtrar por fechas")
    date_from = date_to = None
    if date_filter:
        dates = st.columns(2)
        date_from = dates[0].date_input("Desde", value=mes_inicio)
        date_to = dates[1].date_input("Hasta", value=date.today())
    transactions = db.listar_transacciones(usuario_id, date_from, date_to, search_category, type_filter)
    st.caption(f"{len(transactions)} movimientos")
    if transactions:
        for transaction in transactions:
            mostrar_movimiento(transaction, usuario_id, editable=True)
    else:
        st.info("No hay movimientos para esos filtros.")

elif menu == "Presupuestos":
    st.markdown('<div class="tm-page-kicker">Planifica el mes</div>', unsafe_allow_html=True)
    st.title("Presupuestos")
    with st.container(border=True):
        with st.form("save_budget", clear_on_submit=True):
            category = st.text_input("Categoría")
            limit = st.number_input("Límite mensual", min_value=0.01, step=10.0, format="%.2f")
            submitted = st.form_submit_button("Guardar presupuesto", type="primary")
        if submitted:
            try:
                db.guardar_presupuesto_usuario(usuario_id, category, limit)
                st.success("Presupuesto guardado.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))
    st.subheader("Estado del mes")
    mostrar_presupuestos(usuario_id, mes_inicio, mes_siguiente)

else:
    st.markdown('<div class="tm-page-kicker">Tu cuenta</div>', unsafe_allow_html=True)
    st.title("Administración")
    with st.container(border=True):
        st.subheader("Categorías")
        with st.form("add_category", clear_on_submit=True):
            new_category = st.text_input("Nueva categoría")
            add_category = st.form_submit_button("Añadir categoría")
        if add_category:
            try:
                db.agregar_categoria(new_category)
                st.success("Categoría añadida.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))

    st.subheader("Exportar movimientos")
    export_rows = db.listar_transacciones(usuario_id)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Tipo", "Fecha", "Categoría", "Descripción", "Monto", "Método de pago"])
    for row in export_rows:
        writer.writerow([row["tipo"], row["fecha"], row["categoria"], row["descripcion"], row["monto"], row["metodo_pago"]])
    st.download_button("Descargar CSV", output.getvalue().encode("utf-8-sig"), "movimientos.csv", "text/csv")

    st.divider()
    st.subheader("Borrar mis datos")
    confirm_delete = st.checkbox("Confirmo borrar todos mis movimientos y presupuestos")
    if st.button("Borrar mis datos", type="primary", disabled=not confirm_delete):
        db.borrar_datos_usuario(usuario_id)
        st.success("Se borraron tus movimientos y presupuestos.")
        st.rerun()
        