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
7. Despliega y prueba la URL pública.

La configuración por defecto usa SQLite. En planes gratuitos con almacenamiento efímero, los datos locales pueden perderse al reiniciar o desplegar; para producción conviene conectar PostgreSQL y definir `DATABASE_URL`.

## Pruebas

```powershell
python -m pytest -q
```
