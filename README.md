# 🎤 QR Karaoke Backend

Sistema de karaoke con pedidos por código QR por mesa, cola de canciones de YouTube y panel de administración en tiempo real.

## ¿Qué es este proyecto?

**QR Karaoke** es un sistema backend construido con FastAPI que permite a los clientes de un local de karaoke:

- Escanear un **código QR** en su mesa para acceder al sistema
- **Buscar canciones** en YouTube y agregarlas a una cola compartida
- Ver en tiempo real el **estado de la cola** de canciones (WebSockets)
- Hacer **pedidos de consumo** desde la mesa

El panel de **administración** permite:

- Aprobar/rechazar canciones solicitadas
- Controlar la reproducción del player de YouTube
- Gestionar mesas, usuarios y productos
- Ver reportes de ganancias e ingresos

---

## Stack Técnico

| Componente | Tecnología |
|---|---|
| Framework Web | [FastAPI](https://fastapi.tiangolo.com/) |
| ORM | [SQLAlchemy](https://www.sqlalchemy.org/) |
| Migraciones | [Alembic](https://alembic.sqlalchemy.org/) |
| Tiempo real | WebSockets (nativo FastAPI) |
| Autenticación | JWT (python-jose) |
| Base de datos | PostgreSQL (producción) / SQLite (desarrollo) |
| Despliegue | [Render.com](https://render.com) |
| Python | 3.11+ |

---

## Prerrequisitos

- Python 3.11+
- pip
- PostgreSQL (para producción) o SQLite (para desarrollo local)
- Cuenta en [Google Cloud Console](https://console.cloud.google.com/) para obtener una `YOUTUBE_API_KEY`

---

## Instalación Local

### 1. Clonar el repositorio

```bash
git clone https://github.com/marcoantoniomesacaceres-lgtm/qr_karaoke_backend_render.git
cd qr_karaoke_backend_render
```

### 2. Crear y activar entorno virtual

```bash
python -m venv venv
# En Linux/Mac:
source venv/bin/activate
# En Windows:
venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
# Dependencias de producción
pip install -r requirements.txt

# Dependencias de desarrollo (incluye pytest, etc.)
pip install -r requirements-dev.txt
```

### 4. Configurar variables de entorno

Crear un archivo `.env` en la raíz del proyecto con el siguiente contenido:

```env
DATABASE_URL=sqlite:///./karaoke.db
YOUTUBE_API_KEY=tu_clave_de_youtube_aqui
SECRET_KEY=una_clave_secreta_muy_larga_y_aleatoria
```

> **Nota**: Para producción en Render.com, usar `DATABASE_URL` con PostgreSQL.

### 5. Ejecutar migraciones de base de datos

```bash
alembic upgrade head
```

### 6. Iniciar el servidor de desarrollo

```bash
uvicorn main:app --reload
```

La API estará disponible en: `http://localhost:8000`

La documentación interactiva (Swagger UI) en: `http://localhost:8000/docs`

---

## Variables de Entorno

| Variable | Descripción | Requerida |
|---|---|---|
| `DATABASE_URL` | URL de conexión a la base de datos | ✅ Sí |
| `YOUTUBE_API_KEY` | Clave de API de YouTube Data API v3 | ✅ Sí |
| `SECRET_KEY` | Clave secreta para firmar tokens JWT | ✅ Sí |

---

## Correr Tests

```bash
# Correr todos los tests
pytest

# Correr con verbose
pytest -v

# Correr un test específico
pytest tests/test_endpoints.py -v
```

---

## Estructura del Proyecto

```
qr_karaoke_backend_render/
│
├── main.py                    # Entry point de FastAPI
├── requirements.txt           # Dependencias de producción
├── requirements-dev.txt       # Dependencias de desarrollo
├── runtime.txt                # Versión de Python para Render
├── alembic.ini                # Configuración de Alembic
├── pytest.ini                 # Configuración de pytest
│
├── app/                       # Módulo principal de la aplicación
│   ├── api/                   # Routers y endpoints de FastAPI
│   ├── core/                  # Configuración, BD, seguridad
│   ├── models/                # Modelos SQLAlchemy
│   ├── schemas/               # Schemas Pydantic
│   ├── crud/                  # Operaciones CRUD
│   └── services/              # Lógica de negocio y servicios
│
├── migrations/                # Scripts de migración ad-hoc
├── scripts/                   # Scripts de utilidad y mantenimiento
├── tests/                     # Suite de tests
├── docs/                      # Documentación del proyecto
├── alembic/                   # Migraciones Alembic automáticas
└── static/                    # Archivos estáticos (HTML, CSS, JS)
```

> **Nota sobre la estructura**: Los archivos Python principales (`main.py`, `crud.py`, `admin.py`, etc.) se mantienen en la raíz por compatibilidad con el despliegue actual en Render.com. La carpeta `app/` está preparada para una futura refactorización gradual de imports.

---

## Deploy en Render.com

### Configuración del servicio web en Render

1. Conectar el repositorio de GitHub en Render.com
2. Configurar el servicio con:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. Agregar las variables de entorno (`DATABASE_URL`, `YOUTUBE_API_KEY`, `SECRET_KEY`)
4. El archivo `runtime.txt` indica la versión de Python a usar

### Base de datos en Render

1. Crear una base de datos PostgreSQL en Render
2. Copiar la **Internal Database URL** y usarla como `DATABASE_URL`
3. Las migraciones se ejecutan automáticamente al iniciar la aplicación

---

## Documentación Detallada

Ver la carpeta [`docs/`](./docs/README.md) para documentación técnica detallada sobre:

- Cambios y mejoras implementadas
- Correcciones de bugs
- Guías de uso del sistema
- Planes de implementación

---

## Contribuir

1. Crear una rama desde `develop`
2. Hacer los cambios
3. Crear un Pull Request hacia `develop`
4. El PR debe pasar los tests antes de ser mergeado

---

## Licencia

Proyecto privado — © 2024 Marco Antonio Mesa Cáceres
