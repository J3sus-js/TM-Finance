# TM Finance

Aplicación web para organizar gastos personales, consultar resúmenes mensuales y
planificar presupuestos por categoría.

**Desarrollado por Jesús Monroy** · [Abrir aplicación](https://tmfinance.streamlit.app/)

### Tecnologías

- **Python** — lógica de la aplicación y acceso a datos.
- **Streamlit** — interfaz web interactiva.
- **SQLite 3** — almacenamiento local de cuentas, movimientos y presupuestos.
- **Pandas** — preparación de datos para resúmenes y gráficos.

## Ejecutar

Instala las dependencias y arranca la aplicación web:

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

La aplicación web guarda los datos en SQLite (`control_gastos.db`). Para usar otra
ruta, define `TM_FINANCE_DB_PATH` antes de iniciar Streamlit.

## Interfaz

El panel usa un diseño claro y adaptable a móviles, con navegación lateral,
registro rápido de movimientos y un resumen mensual del balance neto, ingresos y
gastos. Incluye una comparación explícita de los gastos con el mes anterior,
tendencia de seis meses para ingresos y gastos, desglose por categoría y
movimientos recientes. Los filtros del historial se reorganizan en dos columnas
en pantallas pequeñas. El selector del resumen permite consultar cualquiera de
los últimos doce meses.
Cada usuario puede alternar entre los temas **Claro** y **Oscuro** con el botón
flotante de sol/luna; la selección se mantiene durante la sesión de Streamlit.
La interfaz usa una entrada breve en el resumen y microinteracciones discretas
en tarjetas y controles, sin movimiento continuo; respeta la preferencia del
dispositivo para reducir movimiento.

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

## Acceso con Google en Streamlit Cloud

Para habilitar **Continuar con Google** en `https://tmfinance.streamlit.app/`:

1. En Google Cloud Console, selecciona o crea un proyecto y configura la pantalla
   de consentimiento OAuth. Si la app está en modo de prueba, añade como usuario
   de prueba cada cuenta de Google que vaya a iniciar sesión.
2. Crea un ID de cliente OAuth de tipo **Aplicación web**. Añade
   `https://tmfinance.streamlit.app` a **Orígenes autorizados de JavaScript** y
   `https://tmfinance.streamlit.app/` a **URI de redirección autorizados**. La
   URI de redirección debe coincidir exactamente, incluida la barra final.
3. Copia el ID y el secreto del cliente. En Streamlit Community Cloud, abre la
   app, ve a **Settings > Secrets** y guarda:

```toml
GOOGLE_CLIENT_ID = "pega-aqui-el-id-de-cliente"
GOOGLE_CLIENT_SECRET = "pega-aqui-el-secreto-del-cliente"
GOOGLE_REDIRECT_URI = "https://tmfinance.streamlit.app/"
```

4. Guarda los secretos y reinicia o vuelve a desplegar la app. El botón de Google
   se activará al detectar los tres valores.

No publiques el secreto del cliente, no lo agregues al repositorio ni lo pegues
en mensajes. El inicio de sesión usa OAuth con PKCE, valida el estado de la
solicitud contra la sesión que la inició y consume cada transacción una sola vez;
solo crea o vincula cuentas con correo verificado por Google. Para desarrollo
local, registra también `http://localhost:8501/` como URI de retorno autorizada y
configura esa misma dirección en `GOOGLE_REDIRECT_URI`.

La utilidad `control_de_gastos.py` es un programa de consola heredado y no usa el
login de la aplicación web. No la expongas como servicio público.

## Pruebas

Ejecuta las pruebas del acceso a datos con:

```bash
python -m unittest discover -s tests
```

Las pruebas crean una base SQLite temporal y no modifican los datos de la aplicación.