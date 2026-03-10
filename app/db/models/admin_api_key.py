from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.db.models.base import Base
from app.utils.timezone_utils import now_bogota


class AdminApiKey(Base):
    __tablename__ = "admin_api_keys"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now_bogota)
    last_used = Column(DateTime, nullable=True)
