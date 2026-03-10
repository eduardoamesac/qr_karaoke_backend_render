"""
Módulo CRUD para Mesas y Pagos.
Gestiona las mesas del karaoke (almacenadas en CACHE JSON) y los pagos (en BD).
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
import datetime
from decimal import Decimal

import models
import schemas
from cache_manager import cache_manager as cache


# ================================================================================
# FUNCIONES PARA MESAS (En CACHE JSON)
# ================================================================================

def get_mesa_by_qr(db: Session, qr_code: str):
    """Busca una mesa por su código QR (desde CACHE)."""
    return cache.get_mesa_by_qr(qr_code)


def get_mesa_by_id(db: Session, mesa_id: int):
    """Obtiene una mesa por ID (desde CACHE)."""
    return cache.get_mesa_by_id(mesa_id)


def get_mesas(db: Session):
    """Devuelve todas las mesas (desde CACHE)."""
    mesas = cache.get_all_mesas()
    return mesas if mesas else []


def create_mesa(db: Session, mesa: schemas.MesaCreate):
    """Crea una nueva mesa en el CACHE."""
    mesa_data = {
        "nombre": mesa.nombre,
        "qr_code": mesa.qr_code,
        "is_active": True,
        "created_at": datetime.datetime.now().isoformat(),
        "usuarios": []
    }
    mesa_id = cache.create_mesa(mesa_data)
    mesa_data["id"] = mesa_id
    return mesa_data


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


def get_mesas_vacias(db: Session):
    """Mesas sin usuarios conectados."""
    mesas = cache.get_all_mesas()
    usuarios = db.query(models.Usuario).all()
    mesas_con_usuarios = {u.mesa_id for u in usuarios if u.mesa_id}
    return [m for m in mesas if m.get("id") not in mesas_con_usuarios]


def get_table_payment_status(db: Session, mesa_id: int) -> Optional[dict]:
    """Obtiene el estado de cuenta detallado de una mesa (desde CACHE)."""
    mesa = get_mesa_by_id(db, mesa_id)
    if not mesa:
        return None

    # Consumos desde cache
    consumos_raw = cache.get_consumos_by_mesa(mesa_id)
    total_consumido = sum(Decimal(str(c.get("valor_total", 0))) for c in consumos_raw)

    # Pagos desde BD
    total_pagado = db.query(func.sum(models.Pago.monto)).filter(
        models.Pago.mesa_id == mesa_id
    ).scalar() or Decimal('0.00')

    saldo_pendiente = total_consumido - total_pagado

    consumos_items = []
    for c in consumos_raw:
        producto = db.query(models.Producto).filter(
            models.Producto.id == c.get("producto_id")
        ).first()
        consumos_items.append({
            "producto_nombre": producto.nombre if producto else "Producto Eliminado",
            "cantidad": c.get("cantidad"),
            "valor_total": Decimal(str(c.get("valor_total"))),
            "created_at": datetime.datetime.fromisoformat(c.get("created_at"))
        })

    pagos_detalle = db.query(models.Pago).filter(
        models.Pago.mesa_id == mesa_id
    ).order_by(models.Pago.created_at.asc()).all()

    return {
        "mesa_id": mesa_id,
        "mesa_nombre": mesa.get("nombre"),
        "is_active": mesa.get("is_active", True),
        "total_consumido": total_consumido,
        "total_pagado": total_pagado,
        "saldo_pendiente": saldo_pendiente,
        "consumos": consumos_items,
        "pagos": pagos_detalle
    }


def get_all_tables_payment_status(db: Session):
    """Devuelve el estado de cuenta para todas las mesas activas (lista de dicts)."""
    mesas = cache.get_all_mesas() or []
    result = []
    for m in mesas:
        if not m.get("is_active", True):
            continue
        mesa_id = m.get("id")
        if mesa_id is None:
            continue
        status = get_table_payment_status(db, mesa_id)
        if status:
            result.append(status)
    return result


# ================================================================================
# FUNCIONES PARA PAGOS (En BD)
# ================================================================================

def create_pago(db: Session, pago: schemas.PagoCreate):
    """Crea un nuevo pago."""
    db_pago = models.Pago(**pago.dict())
    db.add(db_pago)
    db.commit()
    db.refresh(db_pago)
    return db_pago


def get_pagos(db: Session):
    """Obtiene todos los pagos."""
    return db.query(models.Pago).order_by(models.Pago.created_at.desc()).all()


def get_pagos_mesa(db: Session, mesa_id: int):
    """Obtiene todos los pagos de una mesa."""
    return db.query(models.Pago).filter(
        models.Pago.mesa_id == mesa_id
    ).order_by(models.Pago.created_at.desc()).all()
