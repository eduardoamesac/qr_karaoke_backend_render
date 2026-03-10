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
├── main.py                        # Punto de entrada — solo configura y monta la app
├── requirements.txt               # Dependencias de producción
├── requirements-dev.txt           # Dependencias de desarrollo
├── runtime.txt                    # Versión de Python para Render
├── alembic.ini                    # Configuración de Alembic
├── .env.example                   # Ejemplo de variables de entorno
│
├── app/
│   ├── __init__.py
│   │
│   ├── core/                      # Configuración central y seguridad
│   │   ├── config.py              # Settings via os.getenv
│   │   ├── security.py            # JWT y tokens
│   │   ├── auth.py                # Dependencias de autenticación FastAPI
│   │   └── logging_config.py      # Configuración del logger
│   │
│   ├── db/                        # Capa de base de datos
│   │   ├── database.py            # Engine, SessionLocal, get_db
│   │   ├── models/                # Modelos SQLAlchemy por dominio
│   │   │   ├── base.py            # declarative_base()
│   │   │   ├── usuario.py         # Modelo Usuario
│   │   │   ├── producto.py        # Modelo Producto
│   │   │   └── pago.py            # Modelos Pago + AdminApiKey
│   │   └── crud/                  # Operaciones CRUD por dominio
│   │       ├── crud_usuarios.py   # CRUD de usuarios
│   │       ├── crud_productos.py  # CRUD de productos
│   │       ├── crud_pagos.py      # CRUD de pagos y API keys
│   │       ├── crud_mesas.py      # CRUD de mesas (CACHE JSON)
│   │       ├── crud_canciones.py  # CRUD de canciones + cola
│   │       ├── crud_consumos.py   # CRUD de consumos/pedidos
│   │       └── crud_admin.py      # Reset noche, rankings, reportes
│   │
│   ├── schemas/                   # Schemas Pydantic por dominio
│   │   ├── cancion.py
│   │   ├── usuario.py
│   │   ├── mesa.py
│   │   ├── consumo.py
│   │   ├── producto.py
│   │   ├── pago.py
│   │   └── token.py               # Auth / Admin API key schemas
│   │
│   ├── routers/                   # Routers FastAPI (APIRouter)
│   │   ├── mesas.py
│   │   ├── canciones.py
│   │   ├── usuarios.py
│   │   ├── consumos.py
│   │   ├── productos.py
│   │   ├── youtube.py
│   │   ├── admin.py
│   │   ├── admin_settings.py
│   │   └── admin_extra.py
│   │
│   ├── services/                  # Lógica de negocio y servicios externos
│   │   ├── broadcast.py           # Broadcast de eventos
│   │   ├── websocket_manager.py   # Manager de conexiones WebSocket
│   │   ├── queue_manager.py       # Gestión de la cola de karaoke
│   │   ├── thumbnails.py          # Servicio de thumbnails YouTube
│   │   ├── random_scorer.py       # Puntuación de canciones
│   │   ├── reports_pdf.py         # Generación de reportes PDF
│   │   ├── settings_storage.py    # Persistencia de settings
│   │   └── song_credits_background.py  # Tarea background de créditos
│   │
│   └── utils/                     # Utilidades generales
│       ├── timezone_utils.py      # now_bogota() y manejo de timezone
│       └── cache_manager.py       # Cache en memoria/JSON
│
├── alembic/                       # Migraciones (NO tocar las versiones)
├── static/                        # Frontend (NO tocar)
├── scripts/                       # Scripts utilitarios ejecutables
└── tests/                         # Suite de tests
    └── conftest.py                # Fixtures compartidos (FastAPI TestClient)
```

## 🚀 Instalación local

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

## ⚙️ Variables de entorno (.env.example)

```env
ENVIRONMENT=development
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=karaoke_db
YOUTUBE_API_KEY=your_youtube_api_key
JWT_SECRET_KEY=super-secret-key-change-this
MASTER_API_KEY=zxc12345
KARAOKE_CIERRE=02:00
```

## 🚀 Deploy en Render.com

### Variables de entorno requeridas
Configurar en el dashboard de Render:
```
DATABASE_URL=mysql+mysqlconnector://user:password@host:port/dbname
YOUTUBE_API_KEY=...
JWT_SECRET_KEY=...
MASTER_API_KEY=...
ENVIRONMENT=production
```

### Comando de inicio
```
uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Health Check
```
GET /salud → {"status": "ok"}
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
| POST | `/api/v1/consumos/` | Crear consumo |
| GET | `/api/v1/admin/resumen` | Resumen de la noche |
| POST | `/api/v1/admin/reset` | Reset para nueva noche |

## 🗃️ Base de datos

El sistema usa **SQLAlchemy** con **MySQL** (producción en Render/VPS).
Las migraciones están gestionadas con **Alembic** en la carpeta `alembic/`.

**Modelos en BD:** `Usuario`, `Producto`, `Pago`, `AdminApiKey`
**En CACHE JSON:** `Mesa`, `Cancion`, `Consumo` (rendimiento optimizado)

## 🎯 Algoritmo de Cola Justa (Round Robin con Tiers)

Las canciones se ordenan usando un sistema Round Robin por mesa:
- **ORO** (consumo > $150.000): 3 canciones por turno
- **PLATA** (consumo > $50.000): 2 canciones por turno
- **BRONCE** (consumo ≤ $50.000): 1 canción por turno

El sistema garantiza que todos los usuarios tengan oportunidad de cantar,
priorizando a quienes más consumen pero sin excluir a nadie.

## 🧪 Tests

```bash
pip install -r requirements-dev.txt
pytest tests/
```

## Comandos útiles

```bash
# Ver rutas disponibles
python scripts/list_routes.py

# Crear mesas
python scripts/crear_mesas.py

# Generar QR de admin
python scripts/generate_qr_admin.py

# Limpiar base de datos (solo dev)
python scripts/cleanup_db.py
```

