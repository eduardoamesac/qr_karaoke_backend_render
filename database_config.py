"""
🔧 Database Configuration - Versión PROFESIONAL con Connection Pool
====================================================================
Dos opciones:
1. SQLAlchemy Pool (recomendado - ya lo usas)
2. MySQL Connector Pool (alternativa)
"""

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool, NullPool
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# ============================================================
# OPCIÓN 1: SQLAlchemy Connection Pool (RECOMENDADO)
# ============================================================

class DatabaseConfig:
    """Configuración profesional de base de datos con pool"""
    
    # Detectar si estamos en producción
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    
    # Credenciales
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "mi_base_datos")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    
    # Connection Pool Settings
    # 📊 Ajusta según tu VPS:
    # VPS 4GB RAM → pool_size=10, max_overflow=20
    # VPS 8GB RAM → pool_size=15, max_overflow=30
    # VPS 16GB+ RAM → pool_size=20, max_overflow=40
    
    if ENVIRONMENT == "production":
        POOL_SIZE = int(os.getenv("POOL_SIZE", "15"))
        MAX_OVERFLOW = int(os.getenv("MAX_OVERFLOW", "30"))
        POOL_RECYCLE = 3600  # Reciclar conexiones cada 1 hora
        POOL_PRE_PING = True  # Verificar conexión antes de usar
    else:
        POOL_SIZE = int(os.getenv("POOL_SIZE", "10"))
        MAX_OVERFLOW = int(os.getenv("MAX_OVERFLOW", "20"))
        POOL_RECYCLE = 3600
        POOL_PRE_PING = True
    
    # URL de conexión
    DATABASE_URL = (
        f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    
    # ✅ Engine con pool profesional
    @staticmethod
    def get_engine():
        """Crea engine con pool optimizado"""
        engine = create_engine(
            DatabaseConfig.DATABASE_URL,
            poolclass=QueuePool,
            pool_size=DatabaseConfig.POOL_SIZE,
            max_overflow=DatabaseConfig.MAX_OVERFLOW,
            pool_recycle=DatabaseConfig.POOL_RECYCLE,
            pool_pre_ping=DatabaseConfig.POOL_PRE_PING,
            echo=False,  # Cambia a True para debug
            connect_args={
                "autocommit": False,
                "use_unicode": True,
                "charset": "utf8mb4",
                "collation": "utf8mb4_unicode_ci",
            }
        )
        return engine

# ============================================================
# INICIALIZACIÓN
# ============================================================

# Engine con configuración profesional
engine = DatabaseConfig.get_engine()

# SessionLocal factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Mejor rendimiento
)

# Base para models
Base = declarative_base()

# ============================================================
# DEPENDENCY PARA FASTAPI (Uso Recomendado)
# ============================================================

def get_db_session():
    """
    Dependency para FastAPI - Uso correcto de sesiones
    
    Ejemplo:
        @app.get("/usuarios")
        def get_usuarios(db: Session = Depends(get_db_session)):
            return db.query(Usuario).all()
    """
    session = SessionLocal()
    try:
        yield session
    except Exception as e:
        session.rollback()
        print(f"❌ Database Error: {e}")
        raise
    finally:
        session.close()

# ============================================================
# MONITOREO DE POOL
# ============================================================

def get_pool_status():
    """Obtiene estado actual del connection pool"""
    pool = engine.pool
    return {
        "pool_size": pool.size(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "total": pool.size() + pool.overflow()
    }

def print_pool_status():
    """Imprime estado del pool (para debugging)"""
    status = get_pool_status()
    print(f"""
    📊 Connection Pool Status:
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Pool Size:     {status['pool_size']}
    Checked Out:   {status['checked_out']}
    Overflow:      {status['overflow']}
    Total Used:    {status['total']}
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """)

# ============================================================
# SALUD DE CONEXIÓN
# ============================================================

def test_connection():
    """Verifica que la conexión a BD funciona"""
    session = SessionLocal()
    try:
        session.execute("SELECT 1")
        print("✅ Database connection OK")
        return True
    except Exception as e:
        print(f"❌ Database connection FAILED: {e}")
        return False
    finally:
        session.close()

# ============================================================
# INFORMACIÓN PARA .env
# ============================================================

"""
Agrega esto a tu archivo .env:

# ============ Database ============
ENVIRONMENT=production  # o 'development'
DB_HOST=localhost  # o tu IP de VPS
DB_PORT=3306
DB_USER=root
DB_PASSWORD=tu_password_segura
DB_NAME=mi_base_datos

# ============ Pool Settings ============
# VPS 4GB: POOL_SIZE=10, MAX_OVERFLOW=20
# VPS 8GB: POOL_SIZE=15, MAX_OVERFLOW=30
POOL_SIZE=15
MAX_OVERFLOW=30

# ============ FastAPI ============
DEBUG=False
"""
