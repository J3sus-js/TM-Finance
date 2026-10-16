# TM Finance

## Ejecutar

Instala las dependencias y arranca la aplicación web:

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

La aplicación web guarda los datos en SQLite (`control_gastos.db`). Para usar otra
ruta, define `TM_FINANCE_DB_PATH` antes de iniciar Streamlit.

## Cuentas y datos

Cada cuenta tiene movimientos y presupuestos separados. Las contraseñas se
almacenan con PBKDF2-HMAC-SHA256, nunca en texto plano. Al crear la primera cuenta,
los gastos y presupuestos de la base heredada se copian a esa cuenta; las cuentas
posteriores empiezan con sus propios datos.

La casilla **Recordarme** conserva la preferencia durante la sesión activa de
Streamlit. Para recuperar una contraseña por correo, configura estos valores como
variables de entorno o como secretos de Streamlit (`.streamlit/secrets.toml` en
local; **Settings > Secrets** en Streamlit Community Cloud):

```toml
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "tu-cuenta@gmail.com"
SMTP_PASSWORD = "tu-contraseña-de-aplicación-de-Google"
SMTP_FROM = "tu-cuenta@gmail.com"
APP_BASE_URL = "https://tmfinance.streamlit.app/"
```

En Google, usa una contraseña de aplicación (requiere activar la verificación en
dos pasos); no uses la contraseña normal de la cuenta. Sustituye `tu-cuenta` por
la dirección Gmail real. `SMTP_FROM` puede omitirse si `SMTP_USER` sirve como
remitente. No subas credenciales reales ni el archivo local de secretos al
repositorio.

La utilidad `control_de_gastos.py` es un programa de consola heredado y no usa el
login de la aplicación web. No la expongas como servicio público.