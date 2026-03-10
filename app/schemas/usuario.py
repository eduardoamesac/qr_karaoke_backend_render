"""Schemas for Users (Usuarios)."""

from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class UsuarioBase(BaseModel):
    nick: str
    model_config = ConfigDict(from_attributes=True)


class UsuarioCreate(UsuarioBase):
    pass


class Usuario(UsuarioBase):
    id: int
    puntos: int
    nivel: str
    is_silenced: bool = False
    song_credits: int = 1
    canciones: List['Cancion'] = []
    model_config = ConfigDict(from_attributes=True)


class UsuarioConectado(BaseModel):
    id: int
    nick: str
    puntos: int
    nivel: str
    song_credits: int = 1
    is_active: bool
    last_active: datetime
    model_config = ConfigDict(from_attributes=True)


class MesaInfo(BaseModel):
    id: int
    nombre: str
    model_config = ConfigDict(from_attributes=True)


class UsuarioPublico(UsuarioBase):
    id: int
    puntos: int
    nivel: str
    song_credits: int = 1
    mesa: Optional[MesaInfo] = None
    is_silenced: bool = False
    model_config = ConfigDict(from_attributes=True)


class UsuarioPerfil(Usuario):
    total_consumido: Decimal = Decimal("0.0")
    rank: Optional[int] = None
    mesa: Optional[MesaInfo] = None
    is_silenced: bool = False
    model_config = ConfigDict(from_attributes=True)


class UsuarioNickUpdate(BaseModel):
    nick: str


class UsuarioMoverMesa(BaseModel):
    nuevo_qr_code: str


class UsuarioPuntosUpdate(BaseModel):
    puntos: int


class ReporteGastoUsuarioPorCategoria(BaseModel):
    nick: str
    total_gastado: Decimal


class ReporteUsuarioRechazado(BaseModel):
    nick: str
    canciones_rechazadas: int


class ConsumoHistorial(BaseModel):
    id: int
    cantidad: int
    valor_total: Decimal
    created_at: datetime
    producto: 'ProductoBase'
    usuario: UsuarioBase
    model_config = ConfigDict(from_attributes=True)


class HistorialUsuario(BaseModel):
    canciones: List['Cancion'] = []
    consumos: List[ConsumoHistorial] = []


class BannedNickView(BaseModel):
    nick: str
    banned_at: datetime
    model_config = ConfigDict(from_attributes=True)


class NickUnban(BaseModel):
    nick: str


# Deferred imports
from app.schemas.cancion import Cancion  # noqa: E402
from app.schemas.producto import ProductoBase  # noqa: E402

Usuario.model_rebuild()
HistorialUsuario.model_rebuild()
ConsumoHistorial.model_rebuild()
