from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.models.base import Base
from app.utils.timezone_utils import now_bogota

class TrasladoInventario(Base):
    __tablename__ = "traslados_inventario"

    id = Column(Integer, primary_key=True, index=True)
    local_origen_id = Column(Integer, ForeignKey("locales.id", ondelete="CASCADE"), nullable=False)
    local_destino_id = Column(Integer, ForeignKey("locales.id", ondelete="CASCADE"), nullable=False)
    producto_origen_id = Column(Integer, ForeignKey("productos.id", ondelete="SET NULL"), nullable=True)
    producto_nombre = Column(String(200), nullable=False)
    cantidad = Column(Integer, nullable=False)
    costo_unitario = Column(Numeric(10, 2), default=0)
    usuario_id = Column(Integer, nullable=True)
    usuario_nombre = Column(String(200), nullable=True)
    notas = Column(String(500), nullable=True)
    fecha = Column(DateTime, default=now_bogota)

    # Relaciones
    local_origen = relationship("Local", foreign_keys=[local_origen_id])
    local_destino = relationship("Local", foreign_keys=[local_destino_id])
    producto_origen = relationship("Producto", foreign_keys=[producto_origen_id])
