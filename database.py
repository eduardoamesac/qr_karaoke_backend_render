"""
🔧 Database Configuration - Versión PROFESIONAL con Connection Pool
====================================================================
Configuración automática según ambiente (desarrollo/producción)
Pool se adapta automáticamente al desplegar en VPS
"""

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# ============================================================
# LECTURA DE CONFIGURACIÓN
# ============================================================

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "mi_base_datos")

# ============================================================
# CONFIGURACIÓN DEL POOL (Se adapta automáticamente)
# ============================================================

if ENVIRONMENT == "production":
    # 📊 VPS Production - Valores profesionales
    POOL_SIZE = int(os.getenv("POOL_SIZE", "15"))  # 15 conexiones por defecto
    MAX_OVERFLOW = int(os.getenv("MAX_OVERFLOW", "30"))  # 30 conexiones extra
    POOL_RECYCLE = 3600  # Reciclar conexiones cada 1 hora
    POOL_PRE_PING = True  # Verificar antes de usar
else:
    # 💻 Development - Valores conservadores
    POOL_SIZE = int(os.getenv("POOL_SIZE", "5"))
    MAX_OVERFLOW = int(os.getenv("MAX_OVERFLOW", "10"))
    POOL_RECYCLE = 3600
    POOL_PRE_PING = True

# ============================================================
# URL DE CONEXIÓN
# ============================================================

SQLALCHEMY_DATABASE_URL = (
    f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ============================================================
# CREAR ENGINE CON POOL OPTIMIZADO
# ============================================================

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=QueuePool,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_recycle=POOL_RECYCLE,
    pool_pre_ping=POOL_PRE_PING,
    echo=False,  # Cambiar a True para ver SQL ejecutado
    connect_args={
        "use_unicode": True,
        "charset": "utf8mb4",
        "collation": "utf8mb4_unicode_ci",
    }
)

# ============================================================
# SESSION FACTORY
# ============================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Mejor performance
)

# ============================================================
# BASE PARA MODELS
# ============================================================

Base = declarative_base()

# ============================================================
# DEPENDENCY INJECTION PARA FASTAPI (Uso recomendado)
# ============================================================

def get_db():
    """
    Dependency de FastAPI para obtener sesión de BD
    
    USO EN ENDPOINTS:
    
    from fastapi import Depends
    from sqlalchemy.orm import Session
    from database import get_db
    
    @app.get("/usuarios")
    def listar_usuarios(db: Session = Depends(get_db)):
        return db.query(Usuario).all()
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        print(f"❌ Database error: {e}")
        raise
    finally:
        db.close()

# ============================================================
# UTILIDADES
# ============================================================

def test_connection():
    """Verifica que la conexión a BD funciona"""
    try:
        session = SessionLocal()
        session.execute("SELECT 1")
        session.close()
        print("✅ Database connection OK")
        return True
    except Exception as e:
        print(f"❌ Database connection FAILED: {e}")
        return False

def get_pool_status():
    """Obtiene estado actual del connection pool"""
    pool = engine.pool
    return {
        "pool_size": pool.size(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "total_connections": pool.size() + pool.overflow()
    }

# ============================================================
# DEBUG INFO
# ============================================================

if ENVIRONMENT == "development":
    print(f"""
    ℹ️  Database Configuration (Development):
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Host:        {DB_HOST}
    Database:    {DB_NAME}
    Pool Size:   {POOL_SIZE}
    Max Overflow: {MAX_OVERFLOW}
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """)