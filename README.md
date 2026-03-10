# 🎤 QR Karaoke Backend

Backend del sistema de karaoke con control de mesas vía QR, built con **FastAPI** y desplegado en **Render.com**.

## 📋 Descripción

Sistema de gestión de karaoke que permite:
- Registro de usuarios por mesa vía código QR
- Cola de canciones con algoritmo de "Cola Justa" (Round Robin por mesa)
- Gestión de consumos y pagos por mesa
- Panel de administración para el DJ
- Reproducción automática con WebSockets
- Sistema de puntos y niveles para usuarios

## 🏗️ Arquitectura

```
qr_karaoke_backend_render/
├── main.py                        # Punto de entrada FastAPI + lifespan
├── requirements.txt               # Dependencias de producción
├── requirements-dev.txt           # Dependencias de desarrollo
├── runtime.txt                    # Versión de Python para Render
├── alembic.ini                    # Configuración de Alembic
├── .env.example                   # Ejemplo de variables de entorno
│
├── app/                           # Código principal de la aplicación
│   ├── __init__.py
│   ├── database.py                # Configuración SQLAlchemy + pool
│   ├── models.py                  # Modelos SQLAlchemy
│   ├── schemas.py                 # Schemas Pydantic
│   ├── crud.py                    # Operaciones de base de datos
│   ├── auth.py                    # Autenticación JWT
│   ├── security.py                # Seguridad API keys
│   ├── config.py                  # Variables de configuración
│   ├── timezone_utils.py          # Utilidades de timezone (Bogotá)
│   │
│   ├── routers/                   # Routers FastAPI
│   │   ├── __init__.py
│   │   ├── mesas.py               # Endpoints de mesas
│   │   ├── canciones.py           # Endpoints de canciones/cola
│   │   ├── usuarios.py            # Endpoints de usuarios
│   │   ├── consumos.py            # Endpoints de consumos
│   │   ├── productos.py           # Endpoints de productos
│   │   ├── youtube.py             # Integración YouTube API
│   │   ├── admin.py               # Endpoints de administración
│   │   ├── admin_settings.py      # Configuración del sistema
│   │   └── admin_extra.py         # Endpoints extra de admin
│   │
│   ├── services/                  # Lógica de negocio/servicios
│   │   ├── __init__.py
│   │   ├── broadcast.py           # Broadcast a clientes
│   │   ├── websocket_manager.py   # Gestión WebSockets
│   │   ├── queue_manager.py       # Gestor de cola
│   │   ├── thumbnails.py          # Miniaturas de YouTube
│   │   ├── random_scorer.py       # Puntuación de canciones
│   │   ├── reports_pdf.py         # Generación de reportes PDF
│   │   ├── settings_storage.py    # Almacenamiento de configuración
│   │   └── song_credits_background.py  # Créditos en background
│   │
│   └── utils/
│       ├── __init__.py
│       └── cache_manager.py       # Gestor de caché centralizado
│
├── alembic/                       # Migraciones de base de datos
├── static/                        # Frontend (HTML, CSS, JS)
│
└── scripts/                       # Scripts de utilidad
    ├── crear_mesas.py
    ├── create_db.py
    ├── generate_qr_admin.py
    ├── generate_qr_mesas.py
    └── cleanup_db.py
```

## 🚀 Despliegue en Render.com

### Variables de entorno requeridas
Copiar `.env.example` y configurar:
```env
DATABASE_URL=mysql+mysqlconnector://user:password@host:port/dbname
YOUTUBE_API_KEY=...
SECRET_KEY=...
```

### Comando de inicio
```
uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Health Check
```
GET /salud
```

## 💻 Desarrollo local

```bash
# 1. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus valores

# 4. Iniciar servidor
uvicorn main:app --reload
```

## 🔑 Endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/salud` | Health check |
| GET | `/` | Frontend principal (mesa) |
| GET | `/admin` | Panel de administración |
| GET | `/player` | Reproductor de canciones |
| WS | `/ws/cola` | WebSocket cola de canciones |
| POST | `/api/v1/mesas/{qr_code}/usuarios` | Registro de usuario en mesa |
| POST | `/api/v1/canciones/` | Agregar canción a la cola |
| GET | `/api/v1/canciones/cola` | Estado actual de la cola |

## 🗃️ Base de datos

El sistema usa **SQLAlchemy** con **MySQL** (producción en Render/VPS).

Las migraciones están gestionadas con **Alembic** en la carpeta `alembic/`.

## 🎯 Algoritmo de Cola Justa

Las canciones se ordenan usando un sistema Round Robin por mesa:
- **ORO** (consumo > $150.000): 3 canciones por turno
- **PLATA** (consumo > $50.000): 2 canciones por turno
- **BRONCE** (consumo ≤ $50.000): 1 canción por turno
