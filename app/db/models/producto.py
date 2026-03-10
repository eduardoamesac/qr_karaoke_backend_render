from sqlalchemy import Column, Integer, String, Numeric, Boolean
from app.db.models.base import Base


class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), unique=True, index=True)
    categoria = Column(String(100), index=True, default="General")
    valor = Column(Numeric(10, 2))
    costo = Column(Numeric(10, 2), default=0)
    stock = Column(Integer, default=0)
    imagen_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
