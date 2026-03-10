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
qr_karaoke_backend/
├── main.py                    # Punto de entrada FastAPI + lifespan
├── models.py                  # Modelos SQLAlchemy
├── schemas.py                 # Schemas Pydantic
├── crud.py                    # Operaciones de base de datos
├── database.py                # Configuración SQLAlchemy
├── auth.py                    # Autenticación (API keys admin)
├── security.py                # JWT y seguridad
├── config.py                  # Variables de configuración
│
├── # Routers (módulos de endpoints)
├── admin.py                   # Endpoints de administración
├── admin_extra_router.py      # Endpoints extra de admin
├── admin_settings_router.py   # Configuración del sistema
├── mesas.py                   # Endpoints de mesas
├── canciones.py               # Endpoints de canciones/cola
├── consumos.py                # Endpoints de consumos
├── usuarios.py                # Endpoints de usuarios
├── youtube.py                 # Integración YouTube API
├── productos.py               # Endpoints de productos
│
├── # Servicios
├── websocket_manager.py       # Gestión WebSockets
├── queue_manager.py           # Gestor de cola
├── broadcast.py               # Broadcast a clientes
├── thumbnails.py              # Miniaturas de YouTube
├── timezone_utils.py          # Utilidades de timezone (Bogotá)
├── random_scorer.py           # Puntuación de canciones (IA simulada)
├── settings_storage.py        # Almacenamiento de configuración
├── cache_manager.py           # Gestor de caché
├── song_credits_background.py # Créditos de canciones en background
├── reports_pdf.py             # Generación de reportes PDF
│
├── alembic/                   # Migraciones de base de datos
├── static/                    # Frontend (HTML, CSS, JS)
├── scripts/                   # Scripts de utilidad (no son parte del servidor)
│   ├── crear_mesas.py         # Script inicial de creación de mesas
│   ├── create_db.py           # Script de inicialización de DB
│   ├── generate_qr_admin.py   # Generador QR para admin
│   ├── generate_qr_mesas.py   # Generador QR para mesas
│   └── cleanup_db.py          # Limpieza de datos de prueba
│
├── requirements.txt           # Dependencias de producción
├── runtime.txt                # Versión de Python para Render
└── .env.example               # Variables de entorno requeridas
```

## 🚀 Despliegue en Render.com

### Variables de entorno requeridas
Copiar `.env.example` y configurar:
```env
DATABASE_URL=postgresql://...
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
| POST | `/mesas/qr/{qr_code}/usuarios` | Registro de usuario en mesa |
| POST | `/canciones/` | Agregar canción a la cola |
| GET | `/canciones/cola` | Estado actual de la cola |

## 🗃️ Base de datos

El sistema usa **SQLAlchemy** con soporte para SQLite (desarrollo) y PostgreSQL (producción en Render).

Las migraciones están gestionadas con **Alembic** en la carpeta `alembic/`.

## 🎯 Algoritmo de Cola Justa

Las canciones se ordenan usando un sistema Round Robin por mesa:
- **ORO** (consumo > $150.000): 3 canciones por turno
- **PLATA** (consumo > $50.000): 2 canciones por turno
- **BRONCE** (consumo ≤ $50.000): 1 canción por turno
