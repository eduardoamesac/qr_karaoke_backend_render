from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Numeric, Boolean
from sqlalchemy.orm import relationship
import datetime

from database import Base
from timezone_utils import now_bogota

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nick = Column(String(100), index=True)
    puntos = Column(Integer, default=0)
    nivel = Column(String(50), default="bronce")  # bronce, plata, oro
    last_active = Column(DateTime, default=now_bogota)
    is_silenced = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_banned = Column(Boolean, default=False)
    song_credits = Column(Integer, default=1)
    credits_added_at = Column(DateTime, default=now_bogota)
    last_song_added_at = Column(DateTime, nullable=True)

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

class AdminApiKey(Base):
    __tablename__ = "admin_api_keys"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now_bogota)
    last_used = Column(DateTime, nullable=True)

class Pago(Base):
    __tablename__ = "pagos"

    id = Column(Integer, primary_key=True, index=True)
    monto = Column(Numeric(10, 2), nullable=False)
    metodo_pago = Column(String(50), default="Efectivo")
    created_at = Column(DateTime, default=now_bogota)
    mesa_id = Column(Integer)  # ID de mesa en cache JSON (no BD)