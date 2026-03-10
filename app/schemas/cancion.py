"""Schemas for Songs (Canciones)."""

from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class CancionBase(BaseModel):
    titulo: str
    youtube_id: str
    puntuacion_ia: Optional[int] = None
    duracion_seconds: Optional[int] = 0
    is_karaoke: Optional[bool] = True


class CancionCreate(CancionBase):
    pass


class Cancion(CancionBase):
    id: int
    estado: str
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    puntuacion_ia: Optional[int] = None
    is_karaoke: Optional[bool] = True
    model_config = ConfigDict(from_attributes=True)


class CancionAdminView(Cancion):
    usuario: 'UsuarioPublico'
    model_config = ConfigDict(from_attributes=True)


class CancionMasCantada(BaseModel):
    titulo: str
    youtube_id: str
    veces_cantada: int


class ReordenarCola(BaseModel):
    canciones_ids: list[int]


class ReporteCancionesPorUsuario(BaseModel):
    nick: str
    canciones_cantadas: int


class ReporteCancionesPorMesa(BaseModel):
    mesa_nombre: str
    canciones_cantadas: int


class ReporteCancionesRechazadas(BaseModel):
    titulo: str
    youtube_id: str
    veces_rechazada: int


class ReporteCancionMasPedida(BaseModel):
    titulo: str
    youtube_id: str
    veces_pedida: int


class ReporteActividadPorHora(BaseModel):
    hora: int
    canciones_cantadas: int


class ReporteTiempoEsperaPromedio(BaseModel):
    tiempo_espera_promedio_segundos: int


class ColaView(BaseModel):
    now_playing: Optional[CancionAdminView] = None
    upcoming: list[CancionAdminView] = []


class ColaViewExtended(BaseModel):
    now_playing: Optional[CancionAdminView] = None
    upcoming: list[CancionAdminView] = []
    lazy_queue: list[CancionAdminView] = []
    pending: list[CancionAdminView] = []


class PlayNextResponse(BaseModel):
    play_url: str
    cancion: CancionAdminView


# Deferred import to avoid circular reference
from app.schemas.usuario import UsuarioPublico  # noqa: E402
CancionAdminView.model_rebuild()
