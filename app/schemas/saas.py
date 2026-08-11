from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

class LocalBase(BaseModel):
    nombre: str
    slug: str
    direccion: Optional[str] = None
    logo_url: Optional[str] = None

class LocalCreate(LocalBase):
    pass

class LocalOut(LocalBase):
    id: int
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class UsuarioLocalBase(BaseModel):
    email: str
    nombre: str
    telefono: Optional[str] = None

class UsuarioLocalCreate(UsuarioLocalBase):
    password: str

class UsuarioLocalOut(UsuarioLocalBase):
    id: int
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class UsuarioLocalLogin(BaseModel):
    email: str
    password: str

class UsuarioEmpleadoLocalBase(BaseModel):
    email: str
    nombre: str
    rol: str  # 'dj', 'mesero', 'cajero', 'admin'
    local_id: int

class UsuarioEmpleadoLocalCreate(UsuarioEmpleadoLocalBase):
    password: str

class UsuarioEmpleadoLocalOut(UsuarioEmpleadoLocalBase):
    id: int
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str  # 'owner', 'dj', 'mesero', etc.
    email: str
    name: str
    local_slugs: Optional[List[str]] = None
