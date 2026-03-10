"""Schemas for Authentication and Admin API keys."""

from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class AdminApiKeyCreate(BaseModel):
    description: str


class AdminApiKeyInfo(BaseModel):
    id: int
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    last_used: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AdminApiKeyView(AdminApiKeyInfo):
    key: str


class AdminLoginRequest(BaseModel):
    api_key: str


class AdminLoginResponse(BaseModel):
    success: bool
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None
    description: Optional[str] = None


class ConfiguracionGlobalBase(BaseModel):
    clave: str
    valor: str


class ConfiguracionGlobal(ConfiguracionGlobalBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class ClosingTimeUpdate(BaseModel):
    hora_cierre: str


class Notificacion(BaseModel):
    mensaje: str
