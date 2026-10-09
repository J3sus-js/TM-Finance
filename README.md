# TM-Finance

## Instrucciones de Instalación

Instala las dependencias y ejecuta la aplicación localmente:

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## PostgreSQL en Streamlit Community Cloud

La aplicación usa PostgreSQL mediante `st.connection("postgresql", type="sql")`.
En Neon o Supabase crea una base de datos y copia sus datos de conexión: usuario,
contraseña, host y nombre de base de datos. Usa una conexión con SSL habilitado.

En Streamlit Community Cloud abre **Advanced settings > Secrets** y agrega:

```toml
[connections.postgresql]
url = "postgresql+psycopg2://USUARIO:CONTRASEÑA@HOST/BASE_DE_DATOS?sslmode=require"
```

Sustituye los valores por los de tu proveedor. Codifica caracteres especiales de
la contraseña para URL (por ejemplo, `@` como `%40`). No guardes credenciales en
este repositorio ni en `app.py`; configura el secreto directamente en Streamlit
Cloud. Al iniciar, la app crea las tablas `gastos`, `presupuestos` y `categorias`.

Los datos que existían en `control_gastos.db` no se copian automáticamente a
PostgreSQL. Expórtalos antes de retirar el almacenamiento local y cárgalos en la
nueva base si necesitas conservar el historial previo.