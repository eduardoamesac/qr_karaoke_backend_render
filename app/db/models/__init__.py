"""
app/db/models — SQLAlchemy models.

Re-exports Base and all domain models so that existing code using
`from app.db.models import Base, Usuario, ...` continues to work.
"""

from app.db.models.base import Base
from app.db.models.usuario import Usuario
from app.db.models.producto import Producto
from app.db.models.pago import Pago, AdminApiKey

__all__ = [
    "Base",
    "Usuario",
    "Producto",
    "Pago",
    "AdminApiKey",
]
