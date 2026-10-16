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
Streamlit. Para recuperar una contraseña por correo, configura estas variables de
entorno en el servidor, sin guardarlas en el repositorio:

- `SMTP_HOST`, `SMTP_PORT` (587 para STARTTLS o 465 para SSL)
- `SMTP_USER` y `SMTP_PASSWORD` si el servidor requiere autenticación
- `SMTP_FROM` y `APP_BASE_URL`

La utilidad `control_de_gastos.py` es un programa de consola heredado y no usa el
login de la aplicación web. No la expongas como servicio público.