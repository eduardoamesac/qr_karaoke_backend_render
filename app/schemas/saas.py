from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

class LocalBase(BaseModel):
    nombre: str
    slug: str
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    hora_cierre: Optional[str] = "03:00"
    logo_url: Optional[str] = None

class LocalCreate(LocalBase):
    pass

class LocalUpdate(BaseModel):
    nombre: Optional[str] = None
    slug: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    hora_cierre: Optional[str] = None
    logo_url: Optional[str] = None
    is_active: Optional[bool] = None

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
    modulos_permitidos: Optional[List[str]] = None  # ['dashboard', 'queue', 'inventory', 'accounts', 'reports', 'settings', 'tables']

class UsuarioEmpleadoLocalCreate(UsuarioEmpleadoLocalBase):
    password: str

class UsuarioEmpleadoLocalUpdate(BaseModel):
    nombre: Optional[str] = None
    rol: Optional[str] = None
    local_id: Optional[int] = None
    modulos_permitidos: Optional[List[str]] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

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
    local_ids: Optional[List[int]] = None
    modulos_permitidos: Optional[List[str]] = None

class TrasladoInventarioCreate(BaseModel):
    local_origen_id: int
    local_destino_id: int
    producto_id: int
    cantidad: int
    notas: Optional[str] = None

class TrasladoInventarioOut(BaseModel):
    id: int
    local_origen_id: int
    local_destino_id: int
    producto_origen_id: Optional[int] = None
    producto_nombre: str
    cantidad: int
    costo_unitario: Optional[float] = 0
    usuario_id: Optional[int] = None
    usuario_nombre: Optional[str] = None
    notas: Optional[str] = None
    fecha: datetime
    local_origen_nombre: Optional[str] = None
    local_destino_nombre: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

