"""
Database Configuration — Connection pool optimized for development and production.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import os
from dotenv import load_dotenv

# Re-export Base so callers can do: from app.db.database import Base
from app.db.models.base import Base  # noqa: F401

load_dotenv()

# ============================================================
# ENVIRONMENT CONFIGURATION
# ============================================================

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "mi_base_datos")

# ============================================================
# POOL CONFIGURATION
# ============================================================

if ENVIRONMENT == "production":
    POOL_SIZE = int(os.getenv("POOL_SIZE", "15"))
    MAX_OVERFLOW = int(os.getenv("MAX_OVERFLOW", "30"))
    POOL_RECYCLE = 3600
    POOL_PRE_PING = True
else:
    POOL_SIZE = int(os.getenv("POOL_SIZE", "5"))
    MAX_OVERFLOW = int(os.getenv("MAX_OVERFLOW", "10"))
    POOL_RECYCLE = 3600
    POOL_PRE_PING = True

# ============================================================
# CONNECTION URL & ENGINE
# ============================================================

# Allow DATABASE_URL override (used by Alembic on Render and by the test suite).
# When set to a sqlite:// URL the engine is configured for SQLite instead of MySQL.
DATABASE_URL_OVERRIDE = os.getenv("DATABASE_URL")

if DATABASE_URL_OVERRIDE:
    SQLALCHEMY_DATABASE_URL = DATABASE_URL_OVERRIDE
    if DATABASE_URL_OVERRIDE.startswith("sqlite"):
        from sqlalchemy.pool import StaticPool
        engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )
    else:
        # Generic URL override (e.g. postgres or mysql with full URL)
        engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=False)
else:
    SQLALCHEMY_DATABASE_URL = (
        f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        poolclass=QueuePool,
        pool_size=POOL_SIZE,
        max_overflow=MAX_OVERFLOW,
        pool_recycle=POOL_RECYCLE,
        pool_pre_ping=POOL_PRE_PING,
        echo=False,
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
    expire_on_commit=False
)

# ============================================================
# FASTAPI DEPENDENCY
# ============================================================


def get_db():
    """FastAPI dependency that provides a database session."""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()


# ============================================================
# UTILITIES
# ============================================================

def get_pool_status():
    """Returns current connection pool status."""
    pool = engine.pool
    return {
        "pool_size": pool.size(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "total_connections": pool.size() + pool.overflow()
    }
