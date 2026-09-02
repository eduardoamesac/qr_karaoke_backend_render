from sqlalchemy import Column, Integer, String, DateTime, Boolean, Table, ForeignKey
from sqlalchemy.orm import relationship
from app.db.models.base import Base
from app.utils.timezone_utils import now_bogota

usuarios_locales_rel = Table(
    "usuarios_locales_rel",
    Base.metadata,
    Column("usuario_local_id", Integer, ForeignKey("usuarios_locales.id", ondelete="CASCADE"), primary_key=True),
    Column("local_id", Integer, ForeignKey("locales.id", ondelete="CASCADE"), primary_key=True),
)

class Local(Base):
    __tablename__ = "locales"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    nombre = Column(String(200), index=True, nullable=False)
    direccion = Column(String(200), nullable=True)
    telefono = Column(String(50), nullable=True)
    hora_cierre = Column(String(10), default="03:00", nullable=True)
    logo_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now_bogota)

    # Relación con administradores (dueños)
    administradores = relationship(
        "UsuarioLocal",
        secondary=usuarios_locales_rel,
        back_populates="locales"
    )

    # Relación con empleados
    empleados = relationship("UsuarioEmpleadoLocal", back_populates="local", cascade="all, delete-orphan")
