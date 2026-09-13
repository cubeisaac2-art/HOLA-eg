# HOLA GUINEA

Progressive Web App Flask para descubrir Guinea Ecuatorial: guía local, recomendaciones comunitarias, noticias, historia, deporte, diccionario, mapa, reseñas y acceso a información de visado.

## Ejecutar en local

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m flask --app "app:create_app()" run --debug
```

Abre `http://127.0.0.1:5000`.

## Administrador

1. Entra en `/login`.
2. En desarrollo, usa `admin@holaguinea.com` y `admin123`.
3. Abre `/admin` y entra en **Contenido**.
4. Desde allí puedes crear comidas, restaurantes, hoteles y noticias.
5. Las recomendaciones enviadas por usuarios aparecen como `pending`; pulsa **Aprobar** para publicarlas en `/places`.

## Cuentas de negocio y suscripciones

Los restaurantes y hoteles pueden registrarse como cuenta de **Negocio** desde `/register`. Después de elegir un plan, el administrador confirma el pago desde `/admin/users`:

- **250 FCFA/mes:** hasta 3 publicaciones entre restaurantes y hoteles.
- **500 FCFA/mes:** publicaciones ilimitadas.

La activación dura 30 días y el negocio administra únicamente sus propios contenidos desde `/business`. El proyecto deja el estado de la suscripción en `pending` hasta que se confirme el pago; para cobrar automáticamente hay que conectar una pasarela de pagos compatible con Guinea Ecuatorial.

En producción debes cambiar la cuenta inicial, definir `SECRET_KEY` y no reutilizar la contraseña de desarrollo.

## Secciones principales

- `/places`: lugares publicados y formulario autenticado para recomendar sitios.
- `/news`: noticias filtrables por actualidad, historia, deporte y cultura.
- `/visa`: redirección a la web de la embajada configurada en `EMBASSY_VISA_URL`.
- `/map`: mapa de restaurantes y hoteles.

## Despliegue gratuito con Render

1. Sube el proyecto a GitHub.
2. En Render, crea un **Web Service** y conecta el repositorio.
3. Usa runtime `Python`.
4. Build command: `pip install -r requirements.txt`.
5. Start command: `gunicorn "app:create_app()"`.
6. Añade las variables `SECRET_KEY`, `EMBASSY_VISA_URL` y las claves VAPID si usarás notificaciones push.
7. Crea una base PostgreSQL en el proveedor elegido y copia su cadena de conexión en `DATABASE_URL`.
8. Despliega y prueba la URL pública.

La configuración local usa SQLite si no existe `DATABASE_URL`. En producción, define `DATABASE_URL` con la cadena PostgreSQL. Render puede pedirte crear la base de datos por separado según el plan disponible; copia su URL privada en la variable del Web Service. Las tablas se crean automáticamente al iniciar la aplicación.

`DATABASE_URL` es necesaria en Render para conservar noticias, hoteles, usuarios y cambios del administrador. Sin ella, la aplicación usa SQLite dentro del disco efímero del servicio y los cambios pueden desaparecer al reiniciar o desplegar.

Para usar Neon en VS Code, copia `.env.example` como `.env` y pega la cadena de conexión de Neon en `DATABASE_URL`. En Render, añade la misma variable en **Environment > Environment Variables** del Web Service; no la pongas en `render.yaml` ni la subas a GitHub. También se acepta `NEON_DATABASE_URL` para el desarrollo local.

Ejemplo de formato:

```text
DATABASE_URL=postgresql://usuario:contraseña@host:5432/hola_guinea
```

## Pruebas

```powershell
python -m pytest -q
```

## Importar diccionario Fang

El importador acepta la extracción de texto del diccionario Fang-Español, evita duplicados y conserva el origen de cada entrada:

```powershell
python scripts/import_fang_dictionary.py "C:\ruta\diccionario_fang_espanol.txt"
```

Si `DATABASE_URL` está definida, la importación se realiza en PostgreSQL; si no, usa la SQLite local. El archivo fuente no se incluye en el repositorio.
