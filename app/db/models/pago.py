from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime
from app.db.models.base import Base
from app.utils.timezone_utils import now_bogota


class Pago(Base):
    __tablename__ = "pagos"

    id = Column(Integer, primary_key=True, index=True)
    monto = Column(Numeric(10, 2), nullable=False)
    metodo_pago = Column(String(50), default="Efectivo")
    created_at = Column(DateTime, default=now_bogota)
    mesa_id = Column(Integer)


# Re-export for backward compatibility — AdminApiKey lives in admin_api_key.py
from app.db.models.admin_api_key import AdminApiKey  # noqa: F401
