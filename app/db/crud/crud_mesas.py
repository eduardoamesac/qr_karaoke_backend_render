"""CRUD operations for Tables (in JSON cache)."""

import datetime
from sqlalchemy.orm import Session

from app.schemas import MesaCreate
from app.utils.cache_manager import cache_manager as cache


def get_mesa_by_qr(db: Session, qr_code: str):
    """Busca una mesa por su código QR (desde CACHE)."""
    return cache.get_mesa_by_qr(qr_code)


def get_mesas(db: Session):
    """Devuelve todas las mesas (desde CACHE)."""
    mesas = cache.get_all_mesas()
    return mesas if mesas else []


def create_mesa(db: Session, mesa: MesaCreate):
    """Crea una nueva mesa en el CACHE."""
    mesa_data = {
        "nombre": mesa.nombre,
        "qr_code": mesa.qr_code,
        "local_id": mesa.local_id,
        "is_active": True,
        "created_at": datetime.datetime.now().isoformat(),
        "usuarios": []
    }
    mesa_id = cache.create_mesa(mesa_data)
    mesa_data["id"] = mesa_id
    return mesa_data


def get_mesa_by_id(db: Session, mesa_id: int):
    """Obtiene una mesa por ID (desde CACHE)."""
    return cache.get_mesa_by_id(mesa_id)


def set_mesa_active_status(db: Session, mesa_id: int, is_active: bool):
    """Actualiza el estado de activación de una mesa (CACHE)."""
    mesa = cache.get_mesa_by_id(mesa_id)
    if mesa:
        mesa["is_active"] = is_active
        cache.update_mesa(mesa_id, mesa)
    return mesa


def delete_mesa(db: Session, mesa_id: int):
    """Elimina una mesa (CACHE)."""
    return cache.delete_mesa_from_cache(mesa_id)
