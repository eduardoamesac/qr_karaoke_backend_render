from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from app.db.models.base import Base
from app.utils.timezone_utils import now_bogota


class Compra(Base):
    __tablename__ = "compras"

    id = Column(Integer, primary_key=True, index=True)
    local_id = Column(Integer, ForeignKey("locales.id", ondelete="CASCADE"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id", ondelete="CASCADE"), nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio_compra = Column(Numeric(10, 2), nullable=False)
    total_costo = Column(Numeric(10, 2), nullable=False)
    fecha = Column(DateTime, default=now_bogota)
    proveedor = Column(String(200), nullable=True)

    producto = relationship("Producto")
