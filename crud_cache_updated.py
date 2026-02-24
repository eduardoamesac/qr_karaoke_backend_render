"""
CRUD functions updated to use cache for mesas, cuentas, consumos, song_credits
These functions should replace the corresponding functions in crud.py
"""

from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import models, schemas
from cache_manager import cache_manager
from timezone_utils import now_bogota
from decimal import Decimal

# ========================================================================
# FUNCIONES DE MESAS (AHORA EN CACHE)
# ========================================================================

def get_mesa_by_qr(db: Session, qr_code: str):
    """Busca una mesa por su código QR desde CACHE."""
    return cache_manager.get_mesa_by_qr(qr_code)

def get_mesas(db: Session):
    """Devuelve todas las mesas desde CACHE."""
    return cache_manager.get_all_mesas()

def create_mesa(db: Session, mesa: schemas.MesaCreate):
    """Crea una nueva mesa en CACHE."""
    mesa_id = cache_manager.create_mesa_in_cache(mesa.nombre, mesa.qr_code)
    return cache_manager.get_mesa_by_id(mesa_id)

def get_mesa_by_id(db: Session, mesa_id: int):
    """Busca una mesa por su ID desde CACHE."""
    return cache_manager.get_mesa_by_id(mesa_id)

def delete_mesa(db: Session, mesa_id: int):
    """Elimina una mesa del CACHE."""
    return cache_manager.delete_mesa_from_cache(mesa_id)

def get_mesas_vacias(db: Session):
    """Obtiene todas las mesas sin consumos."""
    all_mesas = cache_manager.get_all_mesas()
    vacias = []
    for mesa in all_mesas:
        mesa_id = mesa.get("id")
        consumos = cache_manager.get_consumos_by_mesa(mesa_id)
        if not consumos:
            vacias.append(mesa)
    return vacias

def set_mesa_active_status(db: Session, mesa_id: int, is_active: bool):
    """Activa/desactiva una mesa."""
    cache_manager.update_mesa_in_cache(mesa_id, {"is_active": is_active})
    return cache_manager.get_mesa_by_id(mesa_id)

# ========================================================================
# FUNCIONES DE CONSUMOS (AHORA EN CACHE)
# ========================================================================

def create_consumo_para_usuario(db: Session, consumo: schemas.ConsumoCreate, usuario_id: int):
    """Crea un consumo en CACHE (JSON)."""
    consumo_dict = {
        "cantidad": consumo.cantidad,
        "valor_total": float(consumo.valor_total),
        "producto_id": consumo.producto_id,
        "mesa_id": consumo.mesa_id,
        "usuario_id": usuario_id,
        "is_dispatched": False
    }
    
    consumo_id = cache_manager.create_consumo_in_cache(consumo_dict)
    return cache_manager.get_consumo_by_id(consumo_id)

def get_consumos_por_usuario(db: Session, usuario_id: int):
    """Obtiene todos los consumos de un usuario desde CACHE."""
    return cache_manager.get_consumos_by_usuario(usuario_id)

def get_consumos_por_mesa(db: Session, mesa_id: int):
    """Obtiene todos los consumos de una mesa desde CACHE."""
    return cache_manager.get_consumos_by_mesa(mesa_id)

def get_consumo_por_mesa(db: Session, mesa_id: int):
    """Obtiene el total consumido por una mesa."""
    consumos = cache_manager.get_consumos_by_mesa(mesa_id)
    total = sum(float(c.get("valor_total", 0)) for c in consumos)
    return {
        "mesa_id": mesa_id,
        "total_consumido": total,
        "cantidad_items": len(consumos),
        "consumos": consumos
    }

def get_recent_consumos(db: Session, limit: int = 10):
    """Obtiene los últimos consumos desde CACHE."""
    all_consumos = cache_manager.get_all_consumos()
    # Ordenar por created_at descendente
    sorted_consumos = sorted(all_consumos, key=lambda x: x.get("created_at", ""), reverse=True)
    return sorted_consumos[:limit]

# ========================================================================
# FUNCIONES DE SONG CREDITS (AHORA EN CACHE)
# ========================================================================

def add_song_credits_to_usuario(db: Session, usuario_id: int, credits_value: int):
    """Agrega créditos de canción a un usuario."""
    cache_manager.add_song_credits(usuario_id, credits_value)
    return cache_manager.get_song_credits(usuario_id)

def get_song_credits(db: Session, usuario_id: int):
    """Obtiene los song_credits de un usuario."""
    return cache_manager.get_song_credits(usuario_id)

def get_active_song_credits(db: Session, usuario_id: int) -> int:
    """Obtiene los créditos activos de un usuario."""
    return cache_manager.get_active_song_credits(usuario_id)

def consume_song_credit(db: Session, usuario_id: int, song_id: int) -> bool:
    """Marca un crédito como consumido."""
    return cache_manager.consume_song_credits(usuario_id, song_id)

# ========================================================================
# FUNCIONES DE REPORTES USANDO CACHE
# ========================================================================

def get_ingresos_por_mesa(db: Session):
    """Calcula ingresos por mesa desde CACHE."""
    mesas = cache_manager.get_all_mesas()
    resultado = []
    
    for mesa in mesas:
        mesa_id = mesa.get("id")
        consumos = cache_manager.get_consumos_by_mesa(mesa_id)
        total = sum(float(c.get("valor_total", 0)) for c in consumos)
        
        resultado.append({
            "mesa_id": mesa_id,
            "nombre_mesa": mesa.get("nombre"),
            "total_consumido": total,
            "cantidad_consumos": len(consumos)
        })
    
    return resultado

def get_estado_mesas(db: Session):
    """Obtiene el estado de todas las mesas."""
    mesas = cache_manager.get_all_mesas()
    resultado = []
    
    for mesa in mesas:
        mesa_id = mesa.get("id")
        cuenta = cache_manager.get_mesa_cuenta_from_cache(mesa_id)
        
        resultado.append({
            "mesa_id": mesa_id,
            "nombre": mesa.get("nombre"),
            "qr_code": mesa.get("qr_code"),
            "is_active": mesa.get("is_active"),
            "total_consumido": cuenta.get("total_consumido", 0),
            "total_pagado": cuenta.get("total_pagado", 0),
            "saldo": cuenta.get("saldo", 0)
        })
    
    return resultado

def get_resumen_mesa(db: Session, mesa_id: int):
    """Obtiene un resumen completo de una mesa."""
    mesa = cache_manager.get_mesa_by_id(mesa_id)
    if not mesa:
        return None
    
    consumos = cache_manager.get_consumos_by_mesa(mesa_id)
    cuenta = cache_manager.get_mesa_cuenta_from_cache(mesa_id)
    
    return {
        "mesa": mesa,
        "cuenta": cuenta,
        "consumos": consumos,
        "total_consumido": cuenta.get("total_consumido", 0),
        "total_pagado": cuenta.get("total_pagado", 0),
        "saldo": cuenta.get("saldo", 0)
    }

def get_productos_mas_consumidos_por_mesa(db: Session, mesa_id: int, limit: int = 5):
    """Obtiene los productos más consumidos en una mesa."""
    consumos = cache_manager.get_consumos_by_mesa(mesa_id)
    
    # Agrupar por producto
    productos_consumo = {}
    for consumo in consumos:
        producto_id = consumo.get("producto_id")
        if producto_id not in productos_consumo:
            productos_consumo[producto_id] = {"cantidad": 0, "total": 0}
        
        productos_consumo[producto_id]["cantidad"] += consumo.get("cantidad", 0)
        productos_consumo[producto_id]["total"] += float(consumo.get("valor_total", 0))
    
    # Ordenar por total descendente
    sorted_productos = sorted(productos_consumo.items(), key=lambda x: x[1]["total"], reverse=True)
    return sorted_productos[:limit]

def get_consumo_total_usuario(db: Session, usuario_id: int):
    """Calcula el total consumido por un usuario."""
    consumos = cache_manager.get_consumos_by_usuario(usuario_id)
    return sum(float(c.get("valor_total", 0)) for c in consumos)
