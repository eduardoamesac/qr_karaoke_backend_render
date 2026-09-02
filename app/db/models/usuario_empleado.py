from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.models.base import Base
from app.utils.timezone_utils import now_bogota

class UsuarioEmpleadoLocal(Base):
    __tablename__ = "usuarios_empleado_locales"

    id = Column(Integer, primary_key=True, index=True)
    local_id = Column(Integer, ForeignKey("locales.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    nombre = Column(String(200), nullable=False)
    rol = Column(String(50), nullable=False)  # 'dj', 'mesero', 'cajero', 'admin'
    modulos_permitidos = Column(Text, nullable=True)  # JSON array string ej: '["dashboard","accounts","inventory"]'
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now_bogota)

    # Relación con Local
    local = relationship("Local", back_populates="empleados")
