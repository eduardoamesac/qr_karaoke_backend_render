from sqlalchemy import Column, Integer, String, DateTime, Boolean
from app.db.models.base import Base
from app.utils.timezone_utils import now_bogota


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nick = Column(String(100), index=True)
    mesa_id = Column(Integer, nullable=True)
    puntos = Column(Integer, default=0)
    nivel = Column(String(50), default="bronce")
    last_active = Column(DateTime, default=now_bogota)
    is_silenced = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_banned = Column(Boolean, default=False)
    song_credits = Column(Integer, default=1)
    credits_added_at = Column(DateTime, default=now_bogota)
    last_song_added_at = Column(DateTime, nullable=True)
