"""CRUD operations for Payments and Admin API Keys (in database)."""

import secrets
from sqlalchemy.orm import Session

from app.db.models import Pago, AdminApiKey
from app.schemas import PagoCreate


def create_pago(db: Session, pago: PagoCreate):
    """Crea un nuevo pago."""
    db_pago = Pago(**pago.dict())
    db.add(db_pago)
    db.commit()
    db.refresh(db_pago)
    return db_pago


def get_pagos(db: Session):
    """Obtiene todos los pagos."""
    return db.query(Pago).order_by(Pago.created_at.desc()).all()


def get_pagos_mesa(db: Session, mesa_id: int):
    """Obtiene todos los pagos de una mesa."""
    return db.query(Pago).filter(Pago.mesa_id == mesa_id).order_by(Pago.created_at.desc()).all()


def create_admin_api_key(db: Session, description: str = None):
    """Crea una nueva API Key para admin."""
    key = secrets.token_urlsafe(32)
    db_key = AdminApiKey(key=key, description=description)
    db.add(db_key)
    db.commit()
    db.refresh(db_key)
    return db_key


def get_admin_api_key(db: Session, key: str):
    """Verifica si una API key es válida y activa."""
    return db.query(AdminApiKey).filter(
        AdminApiKey.key == key,
        AdminApiKey.is_active == True
    ).first()


def get_all_admin_api_keys(db: Session):
    """Obtiene todas las API keys."""
    return db.query(AdminApiKey).all()


def deactivate_admin_api_key(db: Session, key_id: int):
    """Desactiva una API key."""
    db_key = db.query(AdminApiKey).filter(AdminApiKey.id == key_id).first()
    if db_key:
        db_key.is_active = False
        db.commit()
        db.refresh(db_key)
    return db_key


def delete_admin_api_key(db: Session, key_id: int):
    """Elimina una API key por su ID."""
    db_key = db.query(AdminApiKey).filter(AdminApiKey.id == key_id).first()
    if not db_key:
        return None
    db.delete(db_key)
    db.commit()
    return db_key
