"""
app/db/models — SQLAlchemy models.

Re-exports Base and all domain models so that existing code using
`from app.db.models import Base, Usuario, ...` continues to work.
"""

from app.db.models.base import Base
from app.db.models.usuario import Usuario
from app.db.models.producto import Producto
from app.db.models.pago import Pago
from app.db.models.admin_api_key import AdminApiKey
from app.db.models.local import Local
from app.db.models.usuario_local import UsuarioLocal
from app.db.models.usuario_empleado import UsuarioEmpleadoLocal
from app.db.models.compra import Compra

__all__ = [
    "Base",
    "Usuario",
    "Producto",
    "Pago",
    "AdminApiKey",
    "Local",
    "UsuarioLocal",
    "UsuarioEmpleadoLocal",
    "Compra",
]
