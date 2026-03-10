"""
Módulo CRUD para Administración.
Gestiona API Keys de administrador y el reset de la base de datos.
"""

from sqlalchemy.orm import Session
import secrets
from typing import List, Optional

import models
from cache_manager import cache_manager as cache


# ================================================================================
# FUNCIONES PARA ADMIN API KEYS (En BD)
# ================================================================================

def create_admin_api_key(db: Session, description: str = None):
    """Crea una nueva API Key para admin usando secrets.token_urlsafe(32)."""
    key = secrets.token_urlsafe(32)
    db_key = models.AdminApiKey(key=key, description=description)
    db.add(db_key)
    db.commit()
    db.refresh(db_key)
    return db_key


def get_admin_api_key(db: Session, key: str) -> Optional[models.AdminApiKey]:
    """Verifica si una API key es válida y está activa."""
    return db.query(models.AdminApiKey).filter(
        models.AdminApiKey.key == key,
        models.AdminApiKey.is_active == True
    ).first()


def get_all_admin_api_keys(db: Session) -> List[models.AdminApiKey]:
    """Obtiene todas las API keys de administrador."""
    return db.query(models.AdminApiKey).all()


def deactivate_admin_api_key(db: Session, key_id: int):
    """Desactiva una API key sin eliminarla."""
    db_key = db.query(models.AdminApiKey).filter(models.AdminApiKey.id == key_id).first()
    if db_key:
        db_key.is_active = False
        db.commit()
        db.refresh(db_key)
    return db_key


def delete_admin_api_key(db: Session, key_id: int):
    """Elimina permanentemente una API key."""
    db_key = db.query(models.AdminApiKey).filter(
        models.AdminApiKey.id == key_id
    ).first()

    if not db_key:
        return None

    db.delete(db_key)
    db.commit()
    return db_key


# ================================================================================
# RESET DE BASE DE DATOS
# ================================================================================

def reset_database_for_new_night(db: Session):
    """
    Reinicia el sistema para una nueva noche.
    1. Limpia todo el caché JSON (canciones, consumos, balances, mesas).
    2. Elimina todos los pagos de la BD.
    3. Resetea créditos y puntos de usuarios en la DB.
    4. Desconecta a todos los usuarios de sus mesas.
    """
    cache.clear_all()

    db.query(models.Pago).delete()

    db.query(models.Usuario).update({
        "song_credits": 0,
        "puntos": 0,
        "nivel": "bronce",
        "mesa_id": None,
        "is_active": False
    })

    db.commit()
    return True


def limpiar_datos_prueba(db: Session):
    """Limpia todos los datos (solo para desarrollo/pruebas)."""
    db.query(models.Pago).delete()
    db.query(models.Usuario).delete()
    db.query(models.Producto).delete()
    db.commit()

    cache.clear_all()
