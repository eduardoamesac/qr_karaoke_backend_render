"""
Compatibility shim — re-exports from app.db.database.
Use `from app.db.database import ...` for new code.
"""

from app.db.database import (  # noqa: F401
    engine,
    SessionLocal,
    get_db,
    Base,
    SQLALCHEMY_DATABASE_URL,
    ENVIRONMENT,
    get_pool_status,
)

__all__ = [
    "engine",
    "SessionLocal",
    "get_db",
    "Base",
    "SQLALCHEMY_DATABASE_URL",
    "ENVIRONMENT",
    "get_pool_status",
]
