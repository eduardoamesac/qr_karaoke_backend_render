"""
Compatibility shim — re-exports from app.db.models.
Use `from app.db.models import ...` for new code.
"""

from app.db.models import (  # noqa: F401
    Base,
    Usuario,
    Producto,
    Pago,
    AdminApiKey,
)

__all__ = [
    "Base",
    "Usuario",
    "Producto",
    "Pago",
    "AdminApiKey",
]
