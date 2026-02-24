"""
CRUD simplificado - Solo maneja modelos en BD: Usuario, Producto, Pago, AdminApiKey
Las tablas eliminadas (Mesa, Cancion, Consumo, BannedNick, AdminLog) se manejan en CACHE JSON
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
import secrets
from typing import List, Optional
import datetime
import models, schemas
from decimal import Decimal
from cache_manager import CacheManager

# Instancia global del cache manager
cache = CacheManager(cache_dir="cache")

# ================================================================================
# FUNCIONES PARA USUARIOS (En BD)
# ================================================================================

def get_usuario_by_id(db: Session, usuario_id: int):
    """Busca un usuario por su ID."""
    return db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()

def get_usuario_by_nick(db: Session, nick: str):
    """Busca un usuario por su nick (case-insensitive)."""
    return db.query(models.Usuario).filter(func.lower(models.Usuario.nick) == func.lower(nick)).first()

def create_usuario(db: Session, usuario: schemas.UsuarioCreate):
    """Crea un nuevo usuario en la BD."""
    db_usuario = models.Usuario(nick=usuario.nick)
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

def get_all_usuarios(db: Session):
    """Obtiene todos los usuarios."""
    return db.query(models.Usuario).all()

def update_usuario(db: Session, usuario_id: int, usuario_data: dict):
    """Actualiza un usuario."""
    db_usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not db_usuario:
        return None
    
    for key, value in usuario_data.items():
        if hasattr(db_usuario, key) and value is not None:
            setattr(db_usuario, key, value)
    
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

def delete_usuario(db: Session, usuario_id: int):
    """Elimina un usuario."""
    db_usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if db_usuario:
        db.delete(db_usuario)
        db.commit()
    return db_usuario

def get_or_create_dj_user(db: Session):
    """Obtiene o crea el usuario DJ para reproducir canciones."""
    dj_user = get_usuario_by_nick(db, "DJ_KARAOKE")
    if not dj_user:
        dj_user = create_usuario(db, schemas.UsuarioCreate(nick="DJ_KARAOKE"))
    return dj_user

# ================================================================================
# FUNCIONES PARA PRODUCTOS (En BD)
# ================================================================================

def get_producto_by_id(db: Session, producto_id: int):
    """Obtiene un producto por ID."""
    return db.query(models.Producto).filter(models.Producto.id == producto_id).first()

def get_producto_by_nombre(db: Session, nombre: str):
    """Obtiene un producto por nombre."""
    return db.query(models.Producto).filter(models.Producto.nombre == nombre).first()

def get_all_productos(db: Session):
    """Obtiene todos los productos."""
    return db.query(models.Producto).filter(models.Producto.is_active == True).all()

def create_producto(db: Session, producto: schemas.ProductoCreate):
    """Crea un nuevo producto."""
    db_producto = models.Producto(**producto.dict())
    db.add(db_producto)
    db.commit()
    db.refresh(db_producto)
    return db_producto

def update_producto(db: Session, producto_id: int, producto_data: dict):
    """Actualiza un producto."""
    db_producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if not db_producto:
        return None
    
    for key, value in producto_data.items():
        if hasattr(db_producto, key) and value is not None:
            setattr(db_producto, key, value)
    
    db.commit()
    db.refresh(db_producto)
    return db_producto

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
    return db.query(models.Pago).filter(models.Pago.mesa_id == mesa_id).order_by(models.Pago.created_at.desc()).all()

# ================================================================================
# FUNCIONES PARA MESAS (En CACHE JSON)
# ================================================================================

def get_mesa_by_qr(db: Session, qr_code: str):
    """Busca una mesa por su código QR (desde CACHE)."""
    return cache.get_mesa_by_qr(qr_code)

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

# ================================================================================
# FUNCIONES PARA CANCIONES (En CACHE JSON)
# ================================================================================

def get_canciones_por_usuario(db: Session, usuario_id: int):
    """Busca todas las canciones de un usuario (desde CACHE)."""
    return cache.get_songs_by_user(usuario_id)

def create_cancion_para_usuario(db: Session, cancion: schemas.CancionCreate, usuario_id: int):
    """Crea una canción para un usuario (CACHE)."""
    cancion_data = {
        "youtube_id": cancion.youtube_id,
        "titulo": cancion.titulo,
        "duracion_seconds": cancion.duracion_seconds,
        "estado": "pendiente",
        "usuario_id": usuario_id,
        "created_at": datetime.datetime.now().isoformat(),
    }
    cancion_id = cache.add_song(cancion_data)
    cancion_data["id"] = cancion_id
    return cancion_data

def get_cancion_by_id(db: Session, cancion_id: int):
    """Obtiene una canción por ID (CACHE)."""
    return cache.get_song_by_id(cancion_id)

def get_canciones_pendientes(db: Session):
    """Obtiene todas las canciones pendientes (CACHE)."""
    return cache.get_songs_by_estado("pendiente")

def get_cancion_reproduciendo(db: Session):
    """Obtiene la canción que se está reproduciendo (CACHE)."""
    return cache.get_songs_by_estado("reproduciendo")[0] if cache.get_songs_by_estado("reproduciendo") else None

def get_all_canciones(db: Session):
    """Obtiene todas las canciones (CACHE)."""
    return cache.get_all_songs()

def update_cancion_estado(db: Session, cancion_id: int, nuevo_estado: str):
    """Actualiza el estado de una canción (CACHE)."""
    cancion = cache.get_song_by_id(cancion_id)
    if cancion:
        cancion["estado"] = nuevo_estado
        cache.update_song(cancion_id, cancion)
    return cancion

# ================================================================================
# FUNCIONES PARA CONSUMOS (En CACHE JSON)
# ================================================================================

def get_total_consumido_por_usuario(db: Session, usuario_id: int):
    """Calcula el total consumido por un usuario (CACHE)."""
    consumos = cache.get_consumos_by_usuario(usuario_id)
    if not consumos:
        return Decimal('0.00')
    return sum(Decimal(str(c.get("valor_total", 0))) for c in consumos)

def get_consumos_mesa(db: Session, mesa_id: int):
    """Obtiene todos los consumos de una mesa (CACHE)."""
    return cache.get_consumos_by_mesa(mesa_id)

def get_all_consumos(db: Session):
    """Obtiene todos los consumos (CACHE)."""
    return cache.get_all_consumos()

def create_consumo(db: Session, consumo_data: dict):
    """Crea un nuevo consumo (CACHE)."""
    consumo_obj = {
        "cantidad": consumo_data.get("cantidad", 1),
        "valor_total": float(consumo_data.get("valor_total", 0)),
        "mesa_id": consumo_data.get("mesa_id"),
        "usuario_id": consumo_data.get("usuario_id"),
        "producto_id": consumo_data.get("producto_id"),
        "created_at": datetime.datetime.now().isoformat()
    }
    consumo_id = cache.add_consumo(consumo_obj)
    consumo_obj["id"] = consumo_id
    return consumo_obj

# ================================================================================
# FUNCIONES PARA ADMIN API KEYS (En BD)
# ================================================================================

def create_admin_api_key(db: Session, description: str = None):
    """Crea una nueva API Key para admin."""
    key = secrets.token_urlsafe(32)
    db_key = models.AdminApiKey(key=key, description=description)
    db.add(db_key)
    db.commit()
    db.refresh(db_key)
    return db_key

def get_admin_api_key(db: Session, key: str):
    """Verifica si una API key es válida."""
    return db.query(models.AdminApiKey).filter(
        models.AdminApiKey.key == key,
        models.AdminApiKey.is_active == True
    ).first()

def get_all_admin_api_keys(db: Session):
    """Obtiene todas las API keys."""
    return db.query(models.AdminApiKey).all()

def deactivate_admin_api_key(db: Session, key_id: int):
    """Desactiva una API key."""
    db_key = db.query(models.AdminApiKey).filter(models.AdminApiKey.id == key_id).first()
    if db_key:
        db_key.is_active = False
        db.commit()
        db.refresh(db_key)
    return db_key

# ================================================================================
# FUNCIONES AUXILIARES
# ================================================================================

def get_ranking_usuarios(db: Session):
    """Obtiene el ranking de usuarios ordenado por puntos."""
    usuarios = db.query(models.Usuario).order_by(models.Usuario.puntos.desc()).all()
    return [
        {
            "usuario_id": u.id,
            "nick": u.nick,
            "puntos": u.puntos,
            "nivel": u.nivel,
            "last_active": u.last_active
        }
        for u in usuarios
    ]

def get_recent_consumos(db: Session, limit: int = 10):
    """Obtiene los consumos más recientes desde el cache."""
    consumos = cache.get_all_consumos()
    if not consumos:
        return []
    # Ordenar por created_at descendente y limitar
    sorted_consumos = sorted(
        consumos, 
        key=lambda x: x.get("created_at", ""), 
        reverse=True
    )
    return sorted_consumos[:limit]

def get_resumen_noche(db: Session):
    """Obtiene un resumen de la noche desde datos en cache y BD."""
    consumos = cache.get_all_consumos()
    pagos = db.query(models.Pago).all()
    usuarios = db.query(models.Usuario).all()
    
    total_consumido = sum(float(c.get("valor_total", 0)) for c in consumos)
    total_pagado = sum(float(p.monto) for p in pagos)
    saldo = total_consumido - total_pagado
    
    return {
        "total_consumido": float(total_consumido),
        "total_pagado": float(total_pagado),
        "saldo": float(saldo),
        "num_consumos": len(consumos),
        "num_pagos": len(pagos),
        "num_usuarios": len(usuarios),
        "num_canciones": len(cache.get_all_songs()),
        "mesas_activas": len(cache.get_all_mesas()),
        "ingresos_totales": float(total_consumido),
        "canciones_cantadas": len(cache.get_all_songs()),
        "usuarios_activos": len(usuarios)
    }

def get_ganancias_totales(db: Session):
    """Obtiene las ganancias totales (saldo = consumido - pagado)."""
    consumos = cache.get_all_consumos()
    pagos = db.query(models.Pago).all()
    
    total_consumido = sum(float(c.get("valor_total", 0)) for c in consumos)
    total_pagado = sum(float(p.monto) for p in pagos)
    
    return float(total_consumido - total_pagado)

def limpiar_datos_prueba(db: Session):
    """Limpia todos los datos (solo para desarrollo/pruebas)."""
    # Limpiar BD
    db.query(models.Pago).delete()
    db.query(models.Usuario).delete()
    db.query(models.Producto).delete()
    db.commit()
    
    # Limpiar CACHE
    cache.clear_all()
