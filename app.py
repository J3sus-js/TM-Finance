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
import google_auth

METODOS_PAGO = ["Efectivo", "Tarjeta de Crédito", "Tarjeta de Débito", "Transferencia"]


# ==========================================
# CONFIGURACIÓN DE ESTILO Y PÁGINA
# ==========================================
st.set_page_config(
    page_title="Gastos · Control personal",
    page_icon="💸", 
    layout="wide",
    initial_sidebar_state="auto"
)
st.session_state.setdefault("appearance", "Claro")

# Estilos claros y compactos inspirados en la referencia de Gastos.
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Sora:wght@500;600;700&display=swap');

        :root {
            color-scheme: light;
            --tm-ink: #17211d;
            --tm-muted: #59665e;
            --tm-accent: #006b4d;
            --tm-accent-dark: #00553d;
            --tm-canvas: #f7f9f8;
            --tm-line: #e9eeeb;
            --tm-control-line: #dce5e0;
            --tm-shadow: rgba(23, 48, 38, .055);
            --tm-positive: #087a53;
            --tm-negative: #d84b4b;
            --tm-white: #ffffff;
            --tm-input: #ffffff;
            --tm-soft: #f3f8f5;
            --tm-track: #e8efeb;
            --tm-avatar: #e7f3ed;
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
            padding-top: 1.25rem;
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
            gap: .35rem;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] label {
            min-height: 2.8rem;
            padding: .15rem .55rem;
            border-radius: 10px;
            transition: background .18s ease, color .18s ease;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
            background: var(--tm-accent);
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p {
            color: #ffffff;
            font-weight: 600;
        }
        [data-testid="stMetric"] {
            background: var(--tm-white);
            border: 1px solid var(--tm-line);
            border-radius: 16px;
            padding: 1.05rem 1.15rem;
            box-shadow: 0 8px 24px var(--tm-shadow);
            transition: transform .2s cubic-bezier(.2, .8, .2, 1), box-shadow .2s ease, border-color .2s ease;
        }
        [data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            border-color: #c4d9cf;
            box-shadow: 0 12px 28px var(--tm-shadow);
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
            color: #ffffff;
            font-weight: 700;
            box-shadow: 0 4px 12px rgba(0, 107, 77, .16);
            transition: transform .18s ease, box-shadow .18s ease, background .18s ease;
        }
        [data-testid="stBaseButton-primary"]:hover {
            background: var(--tm-accent-dark);
            border-color: var(--tm-accent-dark);
            color: #ffffff;
            transform: translateY(-1px);
            box-shadow: 0 7px 16px rgba(0, 107, 77, .2);
        }
        [data-testid="stBaseButton-secondary"] {
            border-color: var(--tm-control-line);
            color: var(--tm-ink);
            border-radius: 9px;
            background: #ffffff;
            transition: transform .18s ease, border-color .18s ease, background .18s ease;
        }
        [data-testid="stBaseButton-secondary"]:hover {
            transform: translateY(-1px);
            border-color: var(--tm-accent);
            background: var(--tm-soft);
        }
        [data-testid="stBaseButton-primary"]:active,
        [data-testid="stBaseButton-secondary"]:active {
            transform: scale(.98);
        }
        [data-testid="stBaseButton-primary"]:focus-visible,
        [data-testid="stBaseButton-secondary"]:focus-visible,
        [data-testid="stLinkButton"] a:focus-visible,
        [data-testid="stTextInput"] input:focus-visible,
        [data-testid="stNumberInput"] input:focus-visible,
        [data-testid="stDateInput"] input:focus-visible,
        [data-testid="stSelectbox"] [data-baseweb="select"]:focus-within,
        [data-testid="stCheckbox"] input:focus-visible {
            outline: 3px solid color-mix(in srgb, var(--tm-accent) 55%, transparent);
            outline-offset: 2px;
        }
        .st-key-theme_toggle {
            position: fixed;
            top: 1.1rem;
            right: 1.25rem;
            z-index: 1000;
            width: 3.15rem;
        }
        .st-key-theme_toggle button {
            position: relative;
            display: grid;
            width: 3rem;
            height: 3rem;
            min-height: 3rem;
            padding: 0;
            place-items: center;
            overflow: visible;
            border: 1px solid var(--tm-line);
            border-radius: 50%;
            background: var(--tm-white);
            color: var(--tm-accent);
            box-shadow: 0 6px 20px var(--tm-shadow);
            font-size: 1.3rem;
            transition: transform .2s cubic-bezier(.2, .8, .2, 1), background .2s ease, box-shadow .2s ease;
        }
        .st-key-theme_toggle button:hover {
            transform: translateY(-2px);
            background: var(--tm-soft);
            box-shadow: 0 9px 24px var(--tm-shadow);
        }
        .st-key-theme_toggle button:active {
            transform: translateY(0) scale(.97);
        }
        .st-key-theme_toggle button:focus-visible {
            outline: 3px solid color-mix(in srgb, var(--tm-accent) 42%, transparent);
            outline-offset: 4px;
        }
        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stDateInput"] input,
        [data-testid="stSelectbox"] [data-baseweb="select"] > div,
        [data-testid="stTextArea"] textarea {
            border-color: var(--tm-control-line);
            border-radius: 6px;
            background: var(--tm-input);
            color: var(--tm-ink);
        }
        [data-testid="stProgress"] > div > div > div > div {
            background: var(--tm-accent);
        }
        [data-testid="stProgress"] > div {
            background: var(--tm-track);
            border-radius: 999px;
        }
        [data-testid="stAlert"] {
            border-radius: 10px;
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
            border-radius: 9px;
            background: var(--tm-accent);
            color: #ffffff;
            font: 700 1rem 'Sora', sans-serif;
        }
        .tm-brand-name {
            color: var(--tm-ink);
            font: 700 .95rem 'Sora', sans-serif;
        }
        .tm-brand-caption {
            margin-top: .08rem;
            color: var(--tm-muted);
            font-size: .8rem;
        }
        .tm-page-kicker {
            margin-bottom: .35rem;
            color: var(--tm-muted);
            font-size: .8rem;
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
            margin: 1.25rem 0 .5rem;
            text-align: center;
        }
        .tm-auth-icon {
            display: grid;
            width: 3rem;
            height: 3rem;
            margin: 0 auto .9rem;
            place-items: center;
            border-radius: 14px;
            background: var(--tm-avatar);
            color: var(--tm-accent);
            font-size: 1.5rem;
            font-weight: 700;
        }
        .tm-auth-brand-name {
            color: var(--tm-ink);
            font: 700 1rem 'Sora', sans-serif;
        }
        .tm-auth-title {
            margin: .75rem 0 .3rem;
            color: var(--tm-ink);
            font: 700 1.65rem 'Sora', sans-serif;
            text-align: center;
        }
        .tm-auth-caption {
            margin: .3rem 0 1.15rem;
            color: var(--tm-muted);
            font-size: .88rem;
            text-align: center;
        }
        [data-testid="stLinkButton"] a {
            min-height: 2.75rem;
            border: 1px solid var(--tm-control-line);
            border-radius: 10px;
            background: #ffffff;
            color: var(--tm-ink);
            font-weight: 600;
            transition: border-color .18s ease, background .18s ease;
        }
        [data-testid="stLinkButton"] a:hover {
            border-color: var(--tm-accent);
            background: #f7faf8;
            color: var(--tm-ink);
        }
        .tm-auth-separator {
            display: flex;
            align-items: center;
            gap: .8rem;
            margin: .9rem 0;
            color: var(--tm-muted);
            font-size: .8rem;
        }
        .tm-auth-separator::before,
        .tm-auth-separator::after {
            height: 1px;
            flex: 1;
            background: var(--tm-line);
            content: "";
        }
        .tm-auth-footer {
            margin: .9rem 0 0;
            color: var(--tm-muted);
            font-size: .85rem;
            text-align: center;
        }
        .tm-auth-hint {
            margin: -.5rem 0 .5rem;
            color: var(--tm-muted);
            font-size: .8rem;
        }
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-color: var(--tm-line);
            border-radius: 16px;
            background: var(--tm-white);
            box-shadow: 0 8px 24px var(--tm-shadow);
            transition:
                transform .22s cubic-bezier(.2, .8, .2, 1),
                box-shadow .22s ease,
                border-color .22s ease;
        }
        .tm-hero-card {
            margin: .5rem 0 1.25rem;
            padding: 1.65rem 1.8rem;
            border: 1px solid rgba(255, 255, 255, .12);
            border-radius: 18px;
            background: linear-gradient(120deg, #006b4d, #087a58);
            box-shadow: 0 12px 26px rgba(0, 107, 77, .16);
            color: #ffffff;
        }
        .tm-hero-label {
            color: rgba(255, 255, 255, .78);
            font-size: .88rem;
            font-weight: 500;
        }
        .tm-hero-value {
            margin: .4rem 0;
            color: #ffffff;
            font: 700 clamp(2rem, 5vw, 2.8rem) 'Sora', sans-serif;
            letter-spacing: -.04em;
        }
        .tm-hero-caption {
            color: rgba(255, 255, 255, .76);
            font-size: .82rem;
        }
        .tm-hero-breakdown {
            display: flex;
            flex-wrap: wrap;
            gap: .5rem 1.5rem;
            margin-top: 1rem;
        }
        .tm-hero-breakdown-item {
            display: flex;
            flex-direction: column;
            gap: .15rem;
        }
        .tm-hero-breakdown-label {
            color: rgba(255, 255, 255, .82);
            font-size: .8rem;
        }
        .tm-hero-breakdown-value {
            color: #ffffff;
            font-size: 1rem;
            font-weight: 700;
        }
        .tm-hero-comparison {
            margin-top: .9rem;
            color: #ffffff;
            font-size: .9rem;
            font-weight: 600;
        }
        .tm-profile {
            display: flex;
            align-items: center;
            gap: .7rem;
            margin: 1.2rem 0 .25rem;
            padding: .85rem .65rem;
            border-top: 1px solid var(--tm-line);
        }
        .tm-avatar {
            display: grid;
            width: 2.45rem;
            height: 2.45rem;
            flex: 0 0 2.45rem;
            place-items: center;
            border-radius: 50%;
            background: #e7f3ed;
            color: var(--tm-accent);
            font-weight: 700;
        }
        .tm-profile-name {
            color: var(--tm-ink);
            font-size: .84rem;
            font-weight: 600;
        }
        .tm-profile-email {
            overflow: hidden;
            color: var(--tm-muted);
            font-size: .8rem;
            text-overflow: ellipsis;
        }
        [data-testid="stVerticalBlockBorderWrapper"]:hover {
            border-color: color-mix(in srgb, var(--tm-accent) 17%, var(--tm-line));
            box-shadow: 0 12px 30px var(--tm-shadow);
            transform: translateY(-2px);
        }
        .tm-hero-card {
            position: relative;
            overflow: hidden;
            animation: tm-rise-in .42s cubic-bezier(.2, .8, .2, 1) both;
        }
        .tm-hero-card::after {
            position: absolute;
            inset: 0;
            background: linear-gradient(110deg, transparent 30%, rgba(255, 255, 255, .12) 50%, transparent 70%);
            content: "";
            pointer-events: none;
            opacity: 0;
            transform: translateX(-100%);
            animation: tm-sheen .8s .12s ease-out both;
        }
        .tm-positive { color: var(--tm-positive); font-weight: 600; }
        .tm-negative { color: var(--tm-negative); font-weight: 600; }
        .tm-muted { color: var(--tm-muted); font-size: .82rem; }

        @keyframes tm-rise-in {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @keyframes tm-sheen {
            0% { opacity: 0; transform: translateX(-100%); }
            20% { opacity: 1; }
            100% { opacity: 0; transform: translateX(100%); }
        }

        @media (max-width: 768px) {
            [data-testid="stAppViewContainer"] .block-container {
                padding: 1.25rem 1rem 2.5rem;
            }
            [data-testid="stHorizontalBlock"] {
                flex-direction: column;
                gap: .75rem;
            }
            [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
                width: 100% !important;
                flex: 1 1 100%;
            }
            .st-key-movement_filters [data-testid="stHorizontalBlock"] {
                flex-direction: row;
                flex-wrap: wrap;
                gap: .5rem;
            }
            .st-key-movement_filters [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
                width: calc(50% - .25rem) !important;
                min-width: 0;
                flex: 1 1 calc(50% - .25rem) !important;
            }
            .tm-hero-card {
                padding: 1.3rem 1.25rem;
                border-radius: 15px;
            }
            .st-key-theme_toggle {
                top: .65rem;
                right: .7rem;
                width: 2.8rem;
            }
            .st-key-theme_toggle button {
                width: 2.65rem;
                height: 2.65rem;
                min-height: 2.65rem;
                font-size: 1.15rem;
            }
            [data-testid="stMetric"] {
                padding: .85rem .9rem;
                border-radius: 12px;
            }
            [data-testid="stMetricValue"] {
                font-size: clamp(1.05rem, 5vw, 1.4rem);
                overflow-wrap: anywhere;
            }
            [data-testid="stSidebar"] [data-testid="stRadio"] label {
                display: flex;
                min-height: 44px;
                align-items: center;
            }
            [data-testid="stBaseButton-primary"],
            [data-testid="stBaseButton-secondary"],
            [data-testid="stDownloadButton"] button {
                min-height: 44px;
            }
            [data-testid="stTextInput"] input,
            [data-testid="stNumberInput"] input,
            [data-testid="stDateInput"] input,
            [data-testid="stSelectbox"] [data-baseweb="select"] > div,
            [data-testid="stTextArea"] textarea {
                min-height: 44px;
                border-radius: 9px;
            }
            [data-testid="stDataFrame"],
            [data-testid="stVegaLiteChart"] {
                max-width: 100%;
                overflow-x: auto;
            }
            h1 { font-size: 1.55rem !important; }
        }

        @media (max-width: 480px) {
            [data-testid="stAppViewContainer"] .block-container {
                padding: 1rem .75rem 2rem;
            }
            [data-testid="stMetricLabel"] p {
                font-size: .8rem;
            }
            .tm-page-subtitle {
                font-size: .88rem;
            }
            .tm-profile {
                padding-right: .25rem;
                padding-left: .25rem;
            }
            .tm-hero-breakdown {
                gap: .75rem 1rem;
            }
        }

        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                scroll-behavior: auto !important;
                animation-duration: .01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: .01ms !important;
            }
        }
    </style>
""", unsafe_allow_html=True)

if st.session_state.get("appearance") == "Oscuro":
    st.markdown("""
        <style>
            :root {
                color-scheme: dark;
                --tm-ink: #edf4ef;
                --tm-muted: #a0ada6;
                --tm-accent: #24a875;
                --tm-accent-dark: #087a53;
                --tm-canvas: #111714;
                --tm-line: #2b3932;
                --tm-control-line: #405147;
                --tm-shadow: rgba(0, 0, 0, .22);
                --tm-positive: #55cc94;
                --tm-negative: #ff8585;
                --tm-white: #1b2520;
                --tm-input: #151e19;
                --tm-soft: #223229;
                --tm-track: #304138;
                --tm-avatar: #293d31;
            }
            [data-testid="stVegaLiteChart"] svg text,
            [data-testid="stArrowVegaLiteChart"] svg text {
                fill: var(--tm-muted) !important;
            }
            [data-testid="stDataFrame"] {
                color-scheme: dark;
            }
            [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
                background: var(--tm-accent-dark);
            }
            [data-testid="stBaseButton-primary"] {
                color: #10231a;
            }
            [data-testid="stBaseButton-primary"]:hover {
                color: #ffffff;
            }
        </style>
    """, unsafe_allow_html=True)

if st.button(
    "🌙" if st.session_state["appearance"] == "Claro" else "☀️",
    key="theme_toggle",
    help=(
        "Cambiar a modo oscuro"
        if st.session_state["appearance"] == "Claro"
        else "Cambiar a modo claro"
    ),
    type="tertiary",
):
    st.session_state["appearance"] = (
        "Oscuro" if st.session_state["appearance"] == "Claro" else "Claro"
    )
    st.rerun()

def rango_mes_actual():
    hoy = date.today()
    inicio = date(hoy.year, hoy.month, 1)
    siguiente = date(hoy.year + (hoy.month == 12), hoy.month % 12 + 1, 1)
    return inicio, siguiente


MESES = (
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
)
MESES_CORTOS = ("Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")


def desplazar_mes(fecha, cantidad):
    indice = fecha.year * 12 + fecha.month - 1 + cantidad
    return date(indice // 12, indice % 12 + 1, 1)


def formato_moneda(monto):
    valor = f"{monto:,.2f}"
    valor = valor.replace(",", "\0").replace(".", ",").replace("\0", ".")
    return f"USD {valor}"


def solicitar_nuevo_movimiento():
    st.session_state["menu"] = "Resumen"
    st.session_state["show_add_transaction"] = True


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


def obtener_configuracion(nombre, predeterminado=None):
    valor = os.getenv(nombre)
    if valor:
        return valor
    try:
        return st.secrets.get(nombre, predeterminado)
    except Exception:
        return predeterminado


def enviar_correo_restauracion(email, token):
    host = obtener_configuracion("SMTP_HOST")
    username = obtener_configuracion("SMTP_USER")
    sender = obtener_configuracion("SMTP_FROM") or username
    base_url = obtener_configuracion("APP_BASE_URL")
    if not host or not sender or not base_url:
        raise RuntimeError(
            "Configura SMTP_HOST, APP_BASE_URL y un remitente (SMTP_FROM o SMTP_USER) "
            "en las variables de entorno o en los secretos de Streamlit."
        )

    message = EmailMessage()
    message["Subject"] = "Restablece tu contraseña de TM Finance"
    message["From"] = sender
    message["To"] = email
    link = f"{base_url.rstrip('/')}?reset={quote(token)}"
    message.set_content(f"Usa este enlace para cambiar tu contraseña. Vence en una hora:\n\n{link}\n")

    port = int(obtener_configuracion("SMTP_PORT", "587"))
    if port == 465:
        server = smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=20)
    else:
        server = smtplib.SMTP(host, port, timeout=20)
    with server:
        if port != 465:
            server.starttls(context=ssl.create_default_context())
        password = obtener_configuracion("SMTP_PASSWORD")
        if username and password:
            server.login(username, password)
        server.send_message(message)


def iniciar_sesion(usuario):
    st.session_state["user_id"] = usuario["id"]
    st.session_state["username"] = usuario["username"]


def configuracion_google():
    return tuple(
        str(obtener_configuracion(key, "") or "").strip()
        for key in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REDIRECT_URI")
    )


def procesar_callback_google():
    provider_error = st.query_params.get("error")
    code = st.query_params.get("code")
    state = st.query_params.get("state")
    if not provider_error and not code and not state:
        return None, None

    st.query_params.clear()
    try:
        code_verifier = google_auth.consume_authorization_request(
            st.session_state, state
        )
    except google_auth.GoogleAuthError as error:
        return None, str(error)

    if provider_error:
        return None, "No se completó el acceso con Google."
    if not code or not state:
        return None, "La respuesta de Google está incompleta. Inténtalo de nuevo."

    client_id, client_secret, redirect_uri = configuracion_google()
    try:
        profile = google_auth.user_profile(
            code, state, code_verifier, client_id, client_secret, redirect_uri
        )
        usuario = db.obtener_o_crear_usuario_google(
            profile["email"],
            profile["name"],
            hash_password(secrets.token_urlsafe(48)),
        )
    except (google_auth.GoogleAuthError, ValueError) as error:
        return None, str(error)

    iniciar_sesion(usuario)
    return usuario, None


def mostrar_acceso_google(label):
    client_id, client_secret, redirect_uri = configuracion_google()
    if client_id and client_secret and redirect_uri:
        try:
            url, state, code_verifier = google_auth.authorization_request(
                client_id, client_secret, redirect_uri
            )
        except google_auth.GoogleAuthError as error:
            st.error(str(error))
        else:
            st.session_state["google_oauth_transaction"] = {
                "state": state,
                "code_verifier": code_verifier,
            }
            st.link_button(f"G   {label}", url, use_container_width=True)
    else:
        st.button(f"G   {label}", disabled=True, use_container_width=True)
        st.caption("Configura las credenciales de Google para activar este acceso.")
    st.markdown('<div class="tm-auth-separator">o</div>', unsafe_allow_html=True)


def mostrar_autenticacion(error_google=None):
    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "signup" if db.contar_usuarios() == 0 else "login"

    reset_token = st.query_params.get("reset")
    left, center, right = st.columns([1, 1.3, 1])
    with center:
        if error_google:
            st.error(error_google)

        mode = st.session_state.auth_mode
        icon, title, subtitle = {
            "signup": ("＋", "Crear una cuenta", "Regístrate para empezar hoy mismo"),
            "forgot": ("↻", "Recuperar contraseña", "Te enviaremos un enlace de un solo uso"),
        }.get(mode, ("↪", "Bienvenido de nuevo", "Inicia sesión en tu cuenta"))
        st.markdown(f"""
            <div class="tm-auth-brand">
                <div class="tm-auth-icon">{icon}</div>
                <div class="tm-auth-brand-name">Gastos · Control personal</div>
                <div class="tm-auth-title">{title}</div>
                <div class="tm-auth-caption">{subtitle}</div>
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

        if mode == "signup":
            mostrar_acceso_google("Registrarse con Google")
            with st.container(border=True):
                with st.form("signup_form"):
                    username = st.text_input(
                        "Nombre completo", max_chars=40, placeholder="Escribe tu nombre y apellido"
                    )
                    email = st.text_input("Correo electrónico", placeholder="tú@ejemplo.com")
                    password = st.text_input("Contraseña", type="password", placeholder="••••••••")
                    st.markdown(
                        '<div class="tm-auth-hint">Debe tener al menos 8 caracteres</div>',
                        unsafe_allow_html=True,
                    )
                    confirmation = st.text_input(
                        "Confirmar contraseña", type="password", placeholder="••••••••"
                    )
                    submitted = st.form_submit_button(
                        "Registrarse", type="primary", use_container_width=True
                    )
                if submitted:
                    if len(username.strip()) < 2:
                        st.error("Escribe tu nombre completo.")
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
            st.markdown(
                '<div class="tm-auth-footer">¿Ya tienes una cuenta?</div>',
                unsafe_allow_html=True,
            )
            if st.button("Inicia sesión", use_container_width=True):
                st.session_state.auth_mode = "login"
                st.rerun()
            return

        if mode == "forgot":
            with st.container(border=True):
                with st.form("forgot_password"):
                    email = st.text_input("Correo electrónico", placeholder="tú@ejemplo.com")
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

        mostrar_acceso_google("Continuar con Google")
        with st.container(border=True):
            with st.form("login_form"):
                email = st.text_input("Correo electrónico", placeholder="tú@ejemplo.com")
                password_column, forgot_column = st.columns([1.5, 1])
                with password_column:
                    password = st.text_input(
                        "Contraseña", type="password", placeholder="••••••••"
                    )
                with forgot_column:
                    st.markdown("<div style='height:1.95rem'></div>", unsafe_allow_html=True)
                    forgot = st.form_submit_button("¿Has olvidado tu contraseña?")
                remember = st.checkbox("Recordarme")
                submitted = st.form_submit_button("Acceso", type="primary", use_container_width=True)
            if forgot:
                st.session_state.auth_mode = "forgot"
                st.rerun()
            elif submitted:
                usuario = db.obtener_usuario_por_email(email)
                if usuario and verificar_password(password, usuario["password_hash"]):
                    iniciar_sesion(usuario)
                    st.session_state["remember_me"] = remember
                    st.rerun()
                else:
                    st.error("Correo o contraseña incorrectos.")
        st.markdown(
            '<div class="tm-auth-footer">¿No tienes una cuenta?</div>',
            unsafe_allow_html=True,
        )
        if st.button("Crea una", use_container_width=True):
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
        columns[2].markdown(
            f"<span class='{amount_class}'>{sign} {formato_moneda(float(transaccion['monto']))}</span>",
            unsafe_allow_html=True,
        )
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
        st.info(
            "Aún no hay presupuestos. Añade uno arriba para empezar a controlar tus gastos por categoría."
        )
        return
    for budget in budgets:
        spent = float(budget["gastado"])
        limit = float(budget["limite"])
        percentage = spent / limit if limit else 0
        st.markdown(
            f"**{html.escape(budget['categoria'])}** · "
            f"{formato_moneda(spent)} de {formato_moneda(limit)}"
        )
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
    google_user, google_error = procesar_callback_google()
    if google_user:
        st.rerun()
    mostrar_autenticacion(google_error)
    st.stop()

usuario_id = current_user["id"]
mes_inicio, mes_siguiente = rango_mes_actual()
categorias = db.listar_categorias() or CATEGORIAS_BASE

st.sidebar.markdown("""
    <div class="tm-brand">
        <div class="tm-brand-mark">$</div>
        <div><div class="tm-brand-name">Gastos</div><div class="tm-brand-caption">Control personal</div></div>
    </div>
    """, unsafe_allow_html=True)
if st.sidebar.button("＋  Nuevo gasto", type="primary", use_container_width=True):
    solicitar_nuevo_movimiento()
    st.rerun()

menu_labels = {
    "Resumen": "⌂   Inicio",
    "Movimientos": "↗   Gastos",
    "Presupuestos": "◷   Presupuestos",
    "Administración": "▦   Categorías",
}
menu = st.sidebar.radio(
    "Navegación",
    list(menu_labels),
    format_func=menu_labels.get,
    label_visibility="collapsed",
    key="menu",
)
username = html.escape(current_user["username"])
email = html.escape(current_user["email"])
initials = "".join(part[0] for part in current_user["username"].split()[:2]).upper()
st.sidebar.markdown(
    f"""
    <div class="tm-profile">
        <div class="tm-avatar">{html.escape(initials or "U")}</div>
        <div>
            <div class="tm-profile-name">{username}</div>
            <div class="tm-profile-email">{email}</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
if st.sidebar.button("Cerrar sesión", use_container_width=True):
    st.session_state.pop("user_id", None)
    st.session_state.pop("username", None)
    st.session_state.pop("remember_me", None)
    st.session_state.pop("show_add_transaction", None)
    st.session_state.auth_mode = "login"
    st.rerun()

if menu == "Resumen":
    month_options = [desplazar_mes(date.today(), offset) for offset in range(-11, 1)]
    header_left, header_right = st.columns([2.2, 1], vertical_alignment="bottom")
    with header_left:
        st.markdown('<div class="tm-page-kicker">Hola, ' + username + '</div>', unsafe_allow_html=True)
        st.title("Tu resumen")
    with header_right:
        mes_inicio = st.selectbox(
            "Mes",
            month_options,
            index=len(month_options) - 1,
            format_func=lambda mes: f"{MESES[mes.month - 1]} {mes.year}",
            key="dashboard_month",
        )

    mes_siguiente = desplazar_mes(mes_inicio, 1)
    mes_anterior = desplazar_mes(mes_inicio, -1)
    seis_meses_inicio = desplazar_mes(mes_inicio, -5)
    movimientos_tendencia = db.listar_transacciones(
        usuario_id, seis_meses_inicio, mes_siguiente - timedelta(days=1)
    )
    movimientos_mes = [
        movimiento for movimiento in movimientos_tendencia
        if mes_inicio.isoformat() <= str(movimiento["fecha"]) < mes_siguiente.isoformat()
    ]
    gastos_mes = [
        movimiento for movimiento in movimientos_mes if movimiento["tipo"] == "Gasto"
    ]
    ingresos_mes = [
        movimiento for movimiento in movimientos_mes if movimiento["tipo"] == "Ingreso"
    ]
    total_gastado = sum(float(movimiento["monto"]) for movimiento in gastos_mes)
    total_ingresos = sum(float(movimiento["monto"]) for movimiento in ingresos_mes)
    balance_neto = total_ingresos - total_gastado
    gastos_mes_anterior = db.listar_transacciones(
        usuario_id, mes_anterior, mes_inicio - timedelta(days=1), tipo="Gasto"
    )
    total_mes_anterior = sum(float(movimiento["monto"]) for movimiento in gastos_mes_anterior)

    if total_mes_anterior:
        variacion = (total_gastado - total_mes_anterior) / total_mes_anterior * 100
        nombre_mes_anterior = MESES[mes_anterior.month - 1].lower()
        if variacion > 0:
            comparacion = (
                f"Gastaste {abs(variacion):.0f}% más que en {nombre_mes_anterior}: "
                f"{formato_moneda(total_gastado)} frente a {formato_moneda(total_mes_anterior)}."
            )
        elif variacion < 0:
            comparacion = (
                f"Gastaste {abs(variacion):.0f}% menos que en {nombre_mes_anterior}: "
                f"{formato_moneda(total_gastado)} frente a {formato_moneda(total_mes_anterior)}."
            )
        else:
            comparacion = (
                f"Gastaste lo mismo que en {nombre_mes_anterior}: "
                f"{formato_moneda(total_gastado)}."
            )
    elif total_gastado:
        comparacion = (
            f"Registraste {formato_moneda(total_gastado)} en gastos este mes; "
            f"no hubo gastos en {MESES[mes_anterior.month - 1].lower()} para comparar."
        )
    else:
        comparacion = (
            f"No registraste gastos este mes ni en "
            f"{MESES[mes_anterior.month - 1].lower()}."
        )
    st.markdown(
        f"""
        <div class="tm-hero-card">
            <div class="tm-hero-label">Balance neto · {MESES[mes_inicio.month - 1]} {mes_inicio.year}</div>
            <div class="tm-hero-value">{formato_moneda(balance_neto)}</div>
            <div class="tm-hero-breakdown">
                <div class="tm-hero-breakdown-item">
                    <span class="tm-hero-breakdown-label">Ingresos</span>
                    <span class="tm-hero-breakdown-value">{formato_moneda(total_ingresos)}</span>
                </div>
                <div class="tm-hero-breakdown-item">
                    <span class="tm-hero-breakdown-label">Gastos</span>
                    <span class="tm-hero-breakdown-value">{formato_moneda(total_gastado)}</span>
                </div>
            </div>
            <div class="tm-hero-comparison">{html.escape(comparacion)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander(
        "＋  Registrar un movimiento",
        expanded=st.session_state.get("show_add_transaction", False),
    ):
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
                    st.session_state["show_add_transaction"] = False
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))

    st.subheader("Ingresos y gastos")
    with st.container(border=True):
        st.caption("Comparación de ingresos y gastos de los últimos 6 meses.")
        puntos_tendencia = []
        for mes in (desplazar_mes(mes_inicio, offset) for offset in range(-5, 1)):
            movimientos_periodo = [
                movimiento for movimiento in movimientos_tendencia
                if mes.isoformat() <= str(movimiento["fecha"]) < desplazar_mes(mes, 1).isoformat()
            ]
            ingresos_periodo = sum(
                float(movimiento["monto"])
                for movimiento in movimientos_periodo if movimiento["tipo"] == "Ingreso"
            )
            gastos_periodo = sum(
                float(movimiento["monto"])
                for movimiento in movimientos_periodo if movimiento["tipo"] == "Gasto"
            )
            puntos_tendencia.append(
                (f"{MESES_CORTOS[mes.month - 1]}", ingresos_periodo, gastos_periodo)
            )
        tendencia = pd.DataFrame(
            puntos_tendencia, columns=["Mes", "Ingresos", "Gastos"]
        ).set_index("Mes")
        if any(ingresos or gastos for _, ingresos, gastos in puntos_tendencia):
            st.line_chart(tendencia)
        else:
            st.info("Aún no hay movimientos para mostrar. Registra un ingreso o un gasto.")
            if st.button("Registrar primer movimiento", key="empty_trend_add"):
                solicitar_nuevo_movimiento()
                st.rerun()

    category_totals = {}
    for movement in gastos_mes:
        category_totals[movement["categoria"]] = (
            category_totals.get(movement["categoria"], 0) + float(movement["monto"])
        )
    category_rows = [
        {"categoria": categoria, "total": total}
        for categoria, total in sorted(category_totals.items(), key=lambda item: item[1], reverse=True)
    ]
    recent = sorted(
        movimientos_mes,
        key=lambda movimiento: (str(movimiento["fecha"]), movimiento["id"]),
        reverse=True,
    )[:5]
    breakdown_column, recent_column = st.columns([1, 1], gap="large")
    with breakdown_column:
        st.subheader("Desglose")
        with st.container(border=True):
            if category_rows:
                st.vega_lite_chart(pd.DataFrame(category_rows), {
                    "mark": {"type": "arc", "innerRadius": 58},
                    "encoding": {
                        "theta": {"field": "total", "type": "quantitative"},
                        "color": {"field": "categoria", "type": "nominal"},
                        "tooltip": [
                            {"field": "categoria", "type": "nominal"},
                            {"field": "total", "type": "quantitative", "format": "$,.2f"},
                        ],
                    },
                    "view": {"stroke": None},
                }, width="stretch")
            else:
                st.info(
                    "Aún no hay gastos este mes. Registra un gasto para ver el desglose por categoría."
                )
                if st.button("Registrar gasto", key="empty_breakdown_add"):
                    solicitar_nuevo_movimiento()
                    st.rerun()
    with recent_column:
        recent_header, view_all = st.columns([1, 1], vertical_alignment="center")
        recent_header.subheader("Recientes")
        if view_all.button("Ver todos →", key="dashboard_all_expenses"):
            st.session_state["menu"] = "Movimientos"
            st.rerun()
        with st.container(border=True):
            if recent:
                for transaction in recent:
                    mostrar_movimiento(transaction, usuario_id)
            else:
                st.info(
                    "Aún no hay movimientos este mes. Registra un ingreso o un gasto para empezar."
                )
                if st.button("Registrar primer movimiento", key="empty_recent_add"):
                    solicitar_nuevo_movimiento()
                    st.rerun()

elif menu == "Movimientos":
    st.markdown('<div class="tm-page-kicker">Historial de actividad</div>', unsafe_allow_html=True)
    st.title("Movimientos")
    with st.container(key="movement_filters"):
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
        st.info(
            "No hay movimientos que coincidan. Prueba otra categoría o amplía el rango de fechas."
        )

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
    st.title("Categorías y cuenta")
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
        