"""
CRUD simplificado - Solo maneja modelos en BD: Usuario, Producto, Pago, AdminApiKey
Las tablas eliminadas (Mesa, Cancion, Consumo, BannedNick, AdminLog) se manejan en CACHE JSON
"""

from sqlalchemy.orm import Session
import logging
from fastapi import HTTPException
from sqlalchemy import func
import secrets
from typing import List, Optional, Dict, Any
import datetime
from collections import Counter
import models, schemas
from decimal import Decimal
from cache_manager import cache_manager as cache
from queue_manager import queue_manager

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

def create_usuario_en_mesa(db: Session, usuario: schemas.UsuarioCreate, mesa_id: int):
    """Crea un nuevo usuario y lo asocia a una mesa."""
    db_usuario = models.Usuario(nick=usuario.nick, mesa_id=mesa_id)
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

def get_o_crear_usuario_admin_para_mesa(db: Session, mesa_id: int):
    """Obtiene o crea un usuario admin/DJ para una mesa específica."""
    nick = f"MESA_{mesa_id}_ADMIN"
    user = get_usuario_by_nick(db, nick)
    if not user:
        user = models.Usuario(nick=nick, mesa_id=mesa_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

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

def get_productos(db: Session, skip: int = 0, limit: int = 100):
    """Compatibilidad: obtiene productos con paginación (sin filtrar por "is_active").
    Se mantiene como alias a la implementación previa que usaban otras partes del código.
    """
    return db.query(models.Producto).offset(skip).limit(limit).all()

def create_producto(db: Session, producto: schemas.ProductoCreate):
    """Crea un nuevo producto."""
    db_producto = models.Producto(**producto.dict())
    db.add(db_producto)
    db.commit()
    db.refresh(db_producto)
    return db_producto

def update_producto(db: Session, producto_id: int, producto_update: schemas.ProductoCreate):
    """Actualiza un producto."""
    db_producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if not db_producto:
        return None
    
    producto_data = producto_update.dict(exclude_unset=True)
    for key, value in producto_data.items():
        if hasattr(db_producto, key) and value is not None:
            setattr(db_producto, key, value)
    
    db.commit()
    db.refresh(db_producto)
    return db_producto

def delete_producto(db: Session, producto_id: int):
    """Elimina un producto de la base de datos por su ID."""
    db_producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if not db_producto:
        return None, "Producto no encontrado."

    # Verificar si el producto tiene consumos asociados en el CACHE
    consumos_globales = cache.get_all_consumos()
    tiene_consumos = any(c.get("producto_id") == producto_id for c in consumos_globales)

    if tiene_consumos:
        # Si tiene consumos, solo lo desactivamos para no romper el historial
        db_producto.is_active = False
        db.commit()
        db.refresh(db_producto)
        return db_producto, "El producto tiene consumos asociados y ha sido desactivado."
    else:
        # Si no hay consumos, se puede borrar de forma segura.
        db.delete(db_producto)
        db.commit()
        return None, "Producto eliminado permanentemente."

def update_producto_valor(db: Session, producto_id: int, nuevo_valor: Decimal):
    """Actualiza el precio de un producto."""
    db_producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if db_producto:
        db_producto.valor = nuevo_valor
        db.commit()
        db.refresh(db_producto)
    return db_producto

def update_producto_active_status(db: Session, producto_id: int, is_active: bool):
    """Actualiza el estado de activación de un producto."""
    db_producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if db_producto:
        db_producto.is_active = is_active
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

def delete_mesa(db: Session, mesa_id: int):
    """Elimina una mesa (CACHE)."""
    return cache.delete_mesa_from_cache(mesa_id)

# ================================================================================
# FUNCIONES PARA CANCIONES (En CACHE JSON)
# ================================================================================

def get_canciones_por_usuario(db: Session, usuario_id: int):
    """Busca todas las canciones de un usuario (desde CACHE)."""
    return cache.get_songs_by_user(usuario_id)

def get_cancion_by_id(db: Session, cancion_id: int):
    """Obtiene una canción por ID (CACHE)."""
    return cache.get_song_by_id(cancion_id)

def get_cancion_reproduciendo(db: Session):
    """Obtiene la canción que se está reproduciendo (CACHE)."""
    result = cache.get_songs_by_estado("reproduciendo")
    return result[0] if result else None

def get_all_canciones(db: Session):
    """Obtiene todas las canciones (CACHE)."""
    return cache.get_all_songs()

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

def create_consumo_para_usuario(db: Session, consumo: schemas.ConsumoCreate, usuario_id: int):
    """
    Crea un nuevo consumo. CAMBIO: El consumo se asigna a la MESA, no al usuario individual.
    """
    usuario = get_usuario_by_id(db, usuario_id)
    if not usuario:
        return None, "Usuario no encontrado."
    
    if not usuario.mesa_id:
        return None, "El usuario no está asociado a ninguna mesa."

    db_producto = get_producto_by_id(db, consumo.producto_id)
    if not db_producto:
        return None, "Producto no encontrado."

    if db_producto.stock < consumo.cantidad:
        return None, f"Stock insuficiente. Disponible: {db_producto.stock}"

    # Calcular valor total
    valor_total = float(db_producto.valor * consumo.cantidad)

    consumo_obj = {
        "cantidad": consumo.cantidad,
        "valor_total": valor_total,
        "mesa_id": usuario.mesa_id,
        "usuario_id": usuario_id,
        "producto_id": consumo.producto_id,
        "created_at": datetime.datetime.now().isoformat(),
        # Default initialization for missing fields
        "is_dispatched": False,
        "is_cancelled": False 
    }
    
    consumo_id = cache.create_consumo_in_cache(consumo_obj)
    consumo_obj["id"] = consumo_id

    # Otorgar créditos por el consumo según la configuración de Cola Lazy
    from settings_storage import load_settings
    settings = load_settings()
    credit_multiplier = settings.get("lazy_queue_credit_multiplier", 1.0)
    
    creditos_ganados = int(valor_total * credit_multiplier)
    if creditos_ganados > 0:
        usuario.song_credits = (usuario.song_credits or 0) + creditos_ganados
        db.add(usuario)
    
    # Descontar stock
    db_producto.stock -= consumo.cantidad
    db.add(db_producto)
    
    db.commit()
    db.refresh(usuario)
    
    # Enriquecer objeto para retorno (compatibilidad con modelos)
    # En este sistema simplificado, devolvemos un objeto que parezca un modelo
    from types import SimpleNamespace
    db_consumo = SimpleNamespace(**consumo_obj)
    db_consumo.usuario = usuario
    db_consumo.producto = db_producto
    db_consumo.valor_total = Decimal(str(valor_total))
    db_consumo.created_at = datetime.datetime.fromisoformat(consumo_obj["created_at"])
    
    return db_consumo, None

def create_pedido_from_carrito(db: Session, carrito: schemas.CarritoCreate, usuario_id: int):
    """Crea múltiples consumos desde un carrito."""
    usuario = get_usuario_by_id(db, usuario_id)
    if not usuario or not usuario.mesa_id:
        return None, "Usuario o mesa no encontrados."

    consumos_creados = []
    for item in carrito.items:
        consumo_data = schemas.ConsumoCreate(producto_id=item.producto_id, cantidad=item.cantidad)
        db_consumo, error = create_consumo_para_usuario(db, consumo_data, usuario_id)
        if error:
            return None, error
        consumos_creados.append(db_consumo)
    
    return consumos_creados, None

def get_table_payment_status(db: Session, mesa_id: int) -> Optional[dict]:
    """Obtiene el estado de cuenta detallado de una mesa (desde CACHE)."""
    mesa = get_mesa_by_id(db, mesa_id)
    if not mesa:
        return None

    # Consumos desde cache
    consumos_raw = cache.get_consumos_by_mesa(mesa_id)
    total_consumido = sum(Decimal(str(c.get("valor_total", 0))) for c in consumos_raw)

    # Pagos desde BD
    total_pagado = db.query(func.sum(models.Pago.monto)).filter(models.Pago.mesa_id == mesa_id).scalar() or Decimal('0.00')

    saldo_pendiente = total_consumido - total_pagado

    consumos_items = []
    for c in consumos_raw:
        producto = get_producto_by_id(db, c.get("producto_id"))
        consumos_items.append({
            "producto_nombre": producto.nombre if producto else "Producto Eliminado",
            "cantidad": c.get("cantidad"),
            "valor_total": Decimal(str(c.get("valor_total"))),
            "created_at": datetime.datetime.fromisoformat(c.get("created_at"))
        })

    pagos_detalle = db.query(models.Pago).filter(models.Pago.mesa_id == mesa_id).order_by(models.Pago.created_at.asc()).all()

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
        # Filtrar mesas inactivas
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

def delete_admin_api_key(db: Session, key_id: int):
    db_key = db.query(models.AdminApiKey).filter(
        models.AdminApiKey.id == key_id
    ).first()

    if not db_key:
        return None

    db.delete(db_key)
    db.commit()

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
    """Obtiene los consumos más recientes desde el cache e hidrata con nombres de BD."""
    consumos = cache.get_all_consumos()
    if not consumos:
        return []
    # Filtrar los que ya fueron despachados
    consumos_pendientes = [c for c in consumos if not c.get("is_dispatched", False)]
    
    # Ordenar por created_at descendente y limitar
    sorted_consumos = sorted(
        consumos_pendientes, 
        key=lambda x: x.get("created_at", ""), 
        reverse=True
    )
    recent = sorted_consumos[:limit]
    
    if not recent:
        return []
        
    # Enriquecer datos con DB
    import models
    user_ids = {c.get("usuario_id") for c in recent if c.get("usuario_id")}
    prod_ids = {c.get("producto_id") for c in recent if c.get("producto_id")}
    
    usuarios = db.query(models.Usuario).filter(models.Usuario.id.in_(user_ids)).all() if user_ids else []
    productos = db.query(models.Producto).filter(models.Producto.id.in_(prod_ids)).all() if prod_ids else []
    
    user_map = {u.id: u.nick for u in usuarios}
    prod_map = {p.id: p.nombre for p in productos}
    mesa_map = {m.get("id"): m.get("nombre") for m in cache.get_all_mesas()}
    
    enriched = []
    for c in recent:
        c_copy = dict(c)
        c_copy["usuario_nick"] = user_map.get(c.get("usuario_id"), "Desconocido")
        c_copy["producto_nombre"] = prod_map.get(c.get("producto_id"), "Desconocido")
        if c.get("mesa_id"):
            c_copy["mesa_nombre"] = mesa_map.get(c.get("mesa_id"))
        enriched.append(c_copy)
        
    return enriched

def delete_consumo(db: Session, consumo_id: int):
    """
    Elimina un consumo del caché, restaura el stock del producto y recalcula créditos.
    """
    consumo = cache.get_consumo_by_id(consumo_id)
    if not consumo:
        return False
        
    # Restaurar stock del producto
    db_producto = get_producto_by_id(db, consumo["producto_id"])
    if db_producto:
        db_producto.stock += consumo["cantidad"]
        db.add(db_producto)
    
    # Restar créditos al usuario
    usuario = get_usuario_by_id(db, consumo["usuario_id"])
    if usuario:
        from settings_storage import load_settings
        settings = load_settings()
        credit_multiplier = settings.get("lazy_queue_credit_multiplier", 1.0)
        creditos_a_restar = int(consumo["valor_total"] * credit_multiplier)
        if creditos_a_restar > 0:
            usuario.song_credits = max(0, (usuario.song_credits or 0) - creditos_a_restar)
            db.add(usuario)
            
    db.commit()
    
    # Eliminar del cache
    return cache.delete_consumo_from_cache(consumo_id)

def update_consumo_cantidad(db: Session, consumo_id: int, delta: int):
    """
    Incrementa o decrementa la cantidad de un consumo.
    Actualiza stock y créditos del usuario.
    """
    consumo = cache.get_consumo_by_id(consumo_id)
    if not consumo:
        return None, "Consumo no encontrado"

    nueva_cantidad = consumo["cantidad"] + delta
    if nueva_cantidad < 1:
        return None, "La cantidad mínima es 1. Para eliminar use el botón cancelar."

    db_producto = get_producto_by_id(db, consumo["producto_id"])
    if not db_producto:
        return None, "Producto no encontrado"

    # Validar stock si se incrementa
    if delta > 0 and db_producto.stock < delta:
        return None, f"Stock insuficiente. Disponible: {db_producto.stock}"

    # Ajustar stock
    db_producto.stock -= delta
    db.add(db_producto)

    # Calcular diferencia de valor para créditos
    valor_unitario = float(db_producto.valor)
    valor_delta = valor_unitario * delta
    nuevo_valor_total = float(consumo["valor_total"]) + valor_delta

    # Actualizar créditos al usuario
    usuario = get_usuario_by_id(db, consumo["usuario_id"])
    if usuario:
        from settings_storage import load_settings
        settings = load_settings()
        credit_multiplier = settings.get("lazy_queue_credit_multiplier", 1.0)
        creditos_delta = int(valor_delta * credit_multiplier)
        if creditos_delta != 0:
            usuario.song_credits = max(0, (usuario.song_credits or 0) + creditos_delta)
            db.add(usuario)

    db.commit()

    # Actualizar cache
    updates = {
        "cantidad": nueva_cantidad,
        "valor_total": nuevo_valor_total
    }
    cache.update_consumo_in_cache(consumo_id, updates)
    
    # Retornar objeto actualizado (enriquecido)
    consumo.update(updates)
    return consumo, None

def get_resumen_noche(db: Session):
    """Obtiene un resumen de la noche desde datos en cache y BD."""
    consumos = cache.get_all_consumos()
    pagos = db.query(models.Pago).all()
    # Solo contar como activos a los usuarios conectados (is_active es True) y que estén en alguna mesa.
    usuarios_activos_db = db.query(models.Usuario).filter(
        models.Usuario.is_active == True,
        models.Usuario.mesa_id.isnot(None)
    ).all()
    
    total_consumido = sum(float(c.get("valor_total", 0)) for c in consumos)
    total_pagado = sum(float(p.monto) for p in pagos)
    saldo = total_consumido - total_pagado
    
    return {
        "total_consumido": float(total_consumido),
        "total_pagado": float(total_pagado),
        "saldo": float(saldo),
        "num_consumos": len(consumos),
        "num_pagos": len(pagos),
        "num_usuarios": len(usuarios_activos_db),
        "num_canciones": len(cache.get_all_songs()),
        "mesas_activas": len(cache.get_all_mesas()),
        "ingresos_totales": float(total_consumido),
        "canciones_cantadas": len(cache.get_all_songs()),
        "usuarios_activos": len(usuarios_activos_db)
    }

def reset_database_for_new_night(db: Session):
    """
    Reinicia el sistema para una nueva noche.
    1. Limpia todo el caché JSON (canciones, consumos, balances).
    2. Resetea créditos y puntos de usuarios en la DB.
    3. Desconecta a todos los usuarios de sus mesas.
    """
    # 1. Limpiar Caché
    cache.clear_all()
    
    # 2. Resetear Usuarios en DB
    db.query(models.Usuario).update({
        "song_credits": 0,
        "puntos": 0,
        "nivel": "bronce",
        "mesa_id": None,
        "is_active": False
    })
    
    db.commit()
    return True

def get_ganancias_totales(db: Session):
    """Obtiene las ganancias reales (valor total de ventas - costo de productos vendidos)."""
    consumos = cache.get_all_consumos()
    productos = db.query(models.Producto).all()
    
    costo_map = {p.id: float(p.costo or 0) for p in productos}
    
    ganancia_real = 0.0
    for c in consumos:
        prod_id = c.get("producto_id")
        cantidad = int(c.get("cantidad", 1))
        venta_total = float(c.get("valor_total", 0))
        
        costo_unitario = costo_map.get(prod_id, 0.0)
        costo_total = costo_unitario * cantidad
        
        ganancia_real += (venta_total - costo_total)
        
    return ganancia_real

def limpiar_datos_prueba(db: Session):
    """Limpia todos los datos (solo para desarrollo/pruebas)."""
    # Limpiar BD
    db.query(models.Pago).delete()
    db.query(models.Usuario).delete()
    db.query(models.Producto).delete()
    db.commit()
    
    # Limpiar CACHE
    cache.clear_all()

def get_cola_completa_con_lazy(db: Session):
    """Obtiene la cola completa con todas las canciones agrupadas por estado.
    
    Retorna:
    {
        "now_playing": cancion_actual_dict o None,
        "upcoming": [lista de canciones aprobadas],
        "lazy_queue": [lista de canciones pendiente_lazy],
        "pending": [lista de canciones pendientes]
    }
    """
    all_songs = cache.get_all_songs()
    
    now_playing = None
    upcoming = []
    lazy_queue = []
    pending = []
    
    for song in all_songs:
        estado = song.get("estado", "pendiente")
        cancion_enriquecida = enriquecer_cancion(db, song)
        
        if estado == "reproduciendo":
            now_playing = cancion_enriquecida
        elif estado == "aprobado":
            upcoming.append(cancion_enriquecida)
        elif estado == "pendiente_lazy":
            lazy_queue.append(cancion_enriquecida)
        elif estado == "pendiente":
            pending.append(cancion_enriquecida)
    
    # Sort lists to ensure UI consistency
    # Usamos una tupla para evitar errores de tipo (TypeError) al mezclar int y str
    upcoming.sort(key=lambda s: (s.get("orden_manual", 999999) or 999999, s.get("created_at", "")))
    lazy_queue.sort(key=lambda s: (s.get("orden_manual", 999999) or 999999, s.get("created_at", "")))
    pending.sort(key=lambda s: s.get("created_at", ""))

    return {
        "now_playing": now_playing,
        "upcoming": upcoming,
        "lazy_queue": lazy_queue,
        "pending": pending
    }

def get_cola_lazy(db: Session):
    """Obtiene solo la cola lazy (pendiente_lazy) ordenada."""
    all_songs = cache.get_all_songs()
    lazy_songs = [s for s in all_songs if s.get("estado") == "pendiente_lazy"]
    # Ordenar por orden_manual (de reordenamiento) o created_at
    lazy_songs.sort(key=lambda s: (s.get("orden_manual", 0) or 0, s.get("created_at", "")))
    return lazy_songs

def aprobar_siguiente_cancion_lazy(db: Session):
    """Aprueba la siguiente canción en la cola lazy (pendiente_lazy -> aprobado)."""
    all_songs = cache.get_all_songs()
    # Filtrar y asegurar que tenemos una lista válida
    lazy_songs = [s for s in all_songs if s.get("estado") == "pendiente_lazy"]
    if not lazy_songs:
        return None
    
    # Tomar la primera canción lazy
    siguiente = lazy_songs[0]
    siguiente_id = siguiente.get("id")
    
    if not siguiente_id:
        return None
        
    update_data = {
        "estado": "aprobado",
        "approved_at": datetime.datetime.now().isoformat()
    }
    
    cache.update_song(siguiente_id, update_data)
    
    # Retornar el objeto actualizado
    siguiente.update(update_data)
    return siguiente

# ================================================================================
# FUNCIONES PARA CANCIONES (En CACHE)
# ================================================================================

def get_available_song_credits(db: Session, usuario_id: int) -> int:
    """Obtiene los créditos disponibles de canciones para un usuario."""
    usuario = get_usuario_by_id(db, usuario_id)
    if not usuario:
        return 0
    return usuario.song_credits or 1

def get_user_credits_detail(db: Session, usuario_id: int):
    """Obtiene los detalles de créditos del usuario."""
    usuario = get_usuario_by_id(db, usuario_id)
    if not usuario:
        return {"creditos": 0, "proxima_renovacion": None}
    return {
        "creditos": usuario.song_credits or 1,
        "proxima_renovacion": usuario.credits_added_at
    }

def check_if_song_in_user_list(db: Session, usuario_id: int, youtube_id: str) -> bool:
    """Verifica si una canción ya fue añadida por este usuario."""
    all_songs = cache.get_all_songs()
    for song in all_songs:
        if song.get("youtube_id") == youtube_id and song.get("usuario_id") == usuario_id:
            return True
    return False

def create_cancion_para_usuario(db: Session, cancion: schemas.CancionCreate, usuario_id: int):
    """Crea una canción en cache para un usuario."""
    from timezone_utils import now_bogota
    
    # Crear ID único para la canción combinando timestamp y usuario_id
    import time
    song_id = int(time.time() * 1000) + usuario_id
    
    song_data = {
        "id": song_id,
        "youtube_id": cancion.youtube_id,
        "titulo": cancion.titulo,
        "duracion_seconds": cancion.duracion_seconds,
        "usuario_id": usuario_id,
        "estado": "pendiente",
        "created_at": now_bogota().isoformat(),
        "approved_at": None,
        "rejected_at": None,
        "started_at": None,
        "finished_at": None
    }
    
    cache.add_song(song_data)
    return song_data

def consume_song_credit(db: Session, usuario_id: int, cancion_id: int) -> bool:
    """Consume un crédito de canción del usuario."""
    usuario = get_usuario_by_id(db, usuario_id)
    if not usuario or (usuario.song_credits or 0) <= 0:
        return False
    
    # Decrementar crédito
    usuario.song_credits = (usuario.song_credits or 1) - 1
    db.commit()
    return True

def update_cancion_estado(db: Session, cancion_id: int, nuevo_estado: str):
    """Actualiza el estado de una canción en cache."""
    all_songs = cache.get_all_songs()
    for song in all_songs:
        if song.get("id") == cancion_id:
            song["estado"] = nuevo_estado
            cache.update_song(cancion_id, {"estado": nuevo_estado})
            return song
    return None

def get_duracion_total_cola_aprobada(db: Session) -> int:
    """Obtiene la duración total de la cola de canciones aprobadas."""
    all_songs = cache.get_all_songs()
    total = 0
    for song in all_songs:
        if song.get("estado") == "aprobado":
            total += int(song.get("duracion_seconds", 0))
    return total

async def start_next_song_if_autoplay_and_idle(db: Session):
    """Inicia la siguiente canción si autoplay está activo e idle."""
    # Este es un stub simplificado - la lógica real está en queue_manager
    return None

def check_and_approve_next_lazy_song(db: Session):
    """Aprueba automáticamente la siguiente canción lazy si aplica."""
    # Este es un stub simplificado - la lógica real está en queue_manager
    pass

async def avanzar_cola_automaticamente(db: Session):
    """Avanza la cola automáticamente (siguiente canción).

    - Marca la canción actual como 'cantada' si existe
    - Pop la siguiente aprobada y la marca como 'reproduciendo'
    - Refresca la cola y emite los broadcasts necesarios
    Retorna la canción que pasa a reproducirse o None si no hay siguiente.
    """
    import traceback
    logger = logging.getLogger(__name__)
    try:
        from timezone_utils import now_bogota
        import websocket_manager

        # 1) Marcar la canción actual como 'cantada' si existe
        canciones_reproduciendo = cache.get_songs_by_estado('reproduciendo') or []
        cancion_actual = canciones_reproduciendo[0] if canciones_reproduciendo else None
        
        if cancion_actual:
            logger.info(f"🏁 Finalizando canción actual: {cancion_actual.get('titulo')} (ID: {cancion_actual.get('id')})")
            cache.update_song(cancion_actual['id'], {
                'estado': 'cantada',
                'finished_at': now_bogota().isoformat()
            })
        else:
            logger.info("ℹ️ No hay canción reproduciéndose actualmente.")

        # 2) Pop / iniciar la siguiente canción aprobada (esta función ahora promueve desde lazy si es necesario)
        siguiente = queue_manager.pop_next_song(db)

        # 3) Refrescar estado global y notificar via websocket
        # Forzamos un refresco total antes de notificar
        queue_manager.refresh_all(db)
        
        try:
            # Notificar actualización de cola a todos (Admin y Usuarios)
            await websocket_manager.manager.broadcast_queue_update()
        except Exception:
            logger.exception('❌ Error broadcasting queue_update after advancing cola')

        # 4) Si hay siguiente, emitir orden de reproducción al player
        if siguiente:
            # Enriquecer la canción con datos del usuario antes de retornar
            # Esto es vital para que el schema PlayNextResponse/CancionAdminView no falle
            siguiente = enriquecer_cancion(db, siguiente)
            
            logger.info(f"🎵 Iniciando siguiente canción: {siguiente.get('titulo')} (ID: {siguiente.get('id')})")
            try:
                await websocket_manager.manager.broadcast_play_song(
                    youtube_id=siguiente.get('youtube_id'),
                    duration_seconds=int(siguiente.get('duracion_seconds', 0) or 0)
                )
            except Exception:
                logger.exception('❌ Error broadcasting play_song after advancing cola')
        else:
            logger.info("📭 No hay más canciones en cola.")

        return siguiente
    except Exception as e:
        # Log completo con traceback y levantar HTTPException para que FastAPI retorne JSON
        tb = traceback.format_exc()
        logger.error('❌ avanzar_cola_automaticamente failed: %s\n%s', str(e), tb)
        raise HTTPException(status_code=500, detail=f"Error advancing queue: {str(e)}")

def get_canciones_pendientes(db: Session):
    """Obtiene todas las canciones pendientes de aprobación."""
    all_songs = cache.get_all_songs()
    return [s for s in all_songs if s.get("estado") == "pendiente"]

def get_cola_lazy(db: Session):
    """Obtiene la cola de canciones pendiente_lazy (CACHE)."""
    all_songs = cache.get_all_songs()
    lazy = [s for s in all_songs if s.get("estado") == "pendiente_lazy"]
    # Ordenar por orden_manual y luego por fecha
    lazy.sort(key=lambda s: (s.get("orden_manual", 999999) or 999999, s.get("created_at", "")))
    return lazy

def move_lazy_song_up(db: Session, cancion_id: int, usuario_id: int):
    """Mueve una canción lazy hacia arriba, verificando pertenencia."""
    from queue_synchronizer import QueueSynchronizer
    
    # Verificar pertenencia antes de operar
    cancion = cache.get_song_by_id(cancion_id)
    if not cancion or cancion.get("usuario_id") != usuario_id:
        return None
    
    result = QueueSynchronizer.reorder_lazy_queue_safely(
        db, cancion_id, "up", audit_user=f"user_{usuario_id}"
    )
    
    if result["success"]:
        # Devolver el objeto canción actualizado o enriquecido
        updated_song = cache.get_song_by_id(cancion_id)
        return enriquecer_cancion(db, updated_song)
    return None

def move_lazy_song_down(db: Session, cancion_id: int, usuario_id: int):
    """Mueve una canción lazy hacia abajo, verificando pertenencia."""
    from queue_synchronizer import QueueSynchronizer
    
    # Verificar pertenencia antes de operar
    cancion = cache.get_song_by_id(cancion_id)
    if not cancion or cancion.get("usuario_id") != usuario_id:
        return None
    
    result = QueueSynchronizer.reorder_lazy_queue_safely(
        db, cancion_id, "down", audit_user=f"user_{usuario_id}"
    )
    
    if result["success"]:
        updated_song = cache.get_song_by_id(cancion_id)
        return enriquecer_cancion(db, updated_song)
    return None

def enriquecer_cancion(db: Session, song: dict):
    """Enriquece una canción del cache con info del usuario desde BD.
    
    Siempre incluye el campo 'usuario' en la copia retornada para
    satisfacer el schema CancionAdminView (campo requerido por Pydantic).
    Si no se puede obtener el usuario, usa un dict de fallback.
    """
    cancion_enriquecida = dict(song)
    usuario_id = song.get("usuario_id")
    
    usuario = get_usuario_by_id(db, usuario_id) if usuario_id else None
    
    if usuario:
        cancion_enriquecida["usuario"] = {
            "id": usuario.id,
            "nick": usuario.nick,
            "puntos": usuario.puntos,
            "nivel": usuario.nivel,
            "song_credits": usuario.song_credits or 1,
            "is_silenced": usuario.is_silenced,
            "mesa": None
        }
    else:
        # Fallback para canciones de usuarios eliminados o sin usuario_id
        cancion_enriquecida["usuario"] = {
            "id": usuario_id or 0,
            "nick": "DJ" if not usuario_id else f"Usuario #{usuario_id}",
            "puntos": 0,
            "nivel": "bronce",
            "song_credits": 0,
            "is_silenced": False,
            "mesa": None
        }
    
    return cancion_enriquecida

def get_cola_completa(db: Session):
    """Obtiene la cola básica (now_playing y upcoming)."""
    all_songs = cache.get_all_songs()
    
    now_playing = None
    upcoming = []
    
    for song in all_songs:
        estado = song.get("estado")
        song_enriched = enriquecer_cancion(db, song)
        
        if estado == "reproduciendo":
            now_playing = song_enriched
        elif estado == "aprobado":
            upcoming.append(song_enriched)
            
    return {
        "now_playing": now_playing,
        "upcoming": upcoming[:1]
    }
# ================================================================================
    # REPORTES Y ESTADÍSTICAS (Usando Cache y BD)
    # ================================================================================

def get_canciones_mas_cantadas(db: Session, limit: int = 10):
    """Reporte de canciones más cantadas."""
    all_songs = cache.get_all_songs()
    cantadas = [s for s in all_songs if s.get("estado") == "cantada"]
    
    counts = Counter((s.get("titulo"), s.get("youtube_id")) for s in cantadas)
    items = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    
    return [(titulo, y_id, count) for (titulo, y_id), count in items]

def get_productos_mas_consumidos(db: Session, limit: int = 10):
    """Reporte de productos más consumidos."""
    consumos = cache.get_all_consumos()
    product_counts = Counter()
    for c in consumos:
        product_counts[c.get("producto_id")] += c.get("cantidad", 0)
    
    # Obtener nombres de productos de la BD
    product_ids = [p_id for p_id, _ in product_counts.most_common(limit)]
    productos = db.query(models.Producto).filter(models.Producto.id.in_(product_ids)).all()
    prod_map = {p.id: p.nombre for p in productos}
    
    return [
        (prod_map.get(p_id, f"Producto #{p_id}"), count) 
        for p_id, count in product_counts.most_common(limit)
    ]

def get_usuarios_sin_consumo(db: Session):
    """Usuarios que no han realizado consumos."""
    consumos = cache.get_all_consumos()
    usuarios_con_consumo = {c.get("usuario_id") for c in consumos}
    return db.query(models.Usuario).filter(~models.Usuario.id.in_(usuarios_con_consumo)).all()

def get_canciones_cantadas_por_usuario(db: Session):
    """Reporte de canciones cantadas por cada usuario."""
    all_songs = cache.get_all_songs()
    cantadas = [s for s in all_songs if s.get("estado") == "cantada"]
    
    user_counts = Counter(s.get("usuario_id") for s in cantadas)
    
    # Enriquecer con nicks de la BD
    user_ids = list(user_counts.keys())
    usuarios = db.query(models.Usuario).filter(models.Usuario.id.in_(user_ids)).all()
    user_map = {u.id: u.nick for u in usuarios}
    
    results = [
        (user_map.get(u_id, f"Usuario #{u_id}"), count) 
        for u_id, count in user_counts.items()
    ]
    return sorted(results, key=lambda x: x[1], reverse=True)

def get_ingresos_promedio_por_usuario(db: Session):
    """Ingresos promedio por cada usuario que ha consumido."""
    consumos = cache.get_all_consumos()
    if not consumos:
        return 0
    
    total_ingresos = sum(float(c.get("valor_total", 0)) for c in consumos)
    num_usuarios = len({c.get("usuario_id") for c in consumos})
    
    return total_ingresos / num_usuarios if num_usuarios > 0 else 0

def get_usuarios_una_cancion(db: Session):
    """Usuarios que han cantado exactamente una canción."""
    all_songs = cache.get_all_songs()
    cantadas = [s for s in all_songs if s.get("estado") == "cantada"]
    user_counts = Counter(s.get("usuario_id") for s in cantadas)
    
    one_hit_ids = [u_id for u_id, count in user_counts.items() if count == 1]
    return db.query(models.Usuario).filter(models.Usuario.id.in_(one_hit_ids)).all()

def get_mesas_vacias(db: Session):
    """Mesas sin usuarios conectados."""
    mesas = cache.get_all_mesas()
    # Los usuarios están en BD
    usuarios = db.query(models.Usuario).all()
    mesas_con_usuarios = {u.mesa_id for u in usuarios if u.mesa_id}
    return [m for m in mesas if m.get("id") not in mesas_con_usuarios]

def get_ingresos_promedio_por_usuario_por_mesa(db: Session):
    """Reporte de ingresos promedio por usuario en cada mesa."""
    mesas = cache.get_all_mesas()
    consumos = cache.get_all_consumos()
    
    mesa_income = Counter()
    mesa_users = {m.get("id"): set() for m in mesas}
    
    # Mapear usuario -> mesa desde la BD
    usuarios = db.query(models.Usuario).all()
    user_to_mesa = {u.id: u.mesa_id for u in usuarios if u.mesa_id}
    
    for c in consumos:
        u_id = c.get("usuario_id")
        m_id = user_to_mesa.get(u_id)
        if m_id:
            mesa_income[m_id] += float(c.get("valor_total", 0))
            mesa_users[m_id].add(u_id)
    
    report = []
    for m in mesas:
        m_id = m.get("id")
        m_name = m.get("nombre", f"Mesa {m_id}")
        # Contamos usuarios que están físicamente en esa mesa según la BD
        num_users = len([u for u in usuarios if u.mesa_id == m_id])
        total = mesa_income[m_id]
        promedio = total / num_users if num_users > 0 else 0
        report.append((m_name, promedio))
    
    return sorted(report, key=lambda x: x[1], reverse=True)

def get_tiempo_promedio_espera(db: Session):
    """Tiempo promedio de espera (created_at hasta finished_at)."""
    all_songs = cache.get_all_songs()
    cantadas = [s for s in all_songs if s.get("estado") == "cantada" and s.get("finished_at") and s.get("created_at")]
    
    if not cantadas:
        return 0
    
    total_seconds = 0
    for s in cantadas:
        try:
            start = datetime.datetime.fromisoformat(s.get("created_at"))
            end = datetime.datetime.fromisoformat(s.get("finished_at"))
            total_seconds += (end - start).total_seconds()
        except:
            continue
            
    return total_seconds / len(cantadas)

def get_actividad_por_hora(db: Session):
    """Reporte de canciones cantadas por hora."""
    all_songs = cache.get_all_songs()
    cantadas = [s for s in all_songs if s.get("estado") == "cantada" and s.get("started_at")]
    
    hora_counts = Counter()
    for s in cantadas:
        try:
            dt = datetime.datetime.fromisoformat(s.get("started_at"))
            hora_counts[dt.hour] += 1
        except:
            continue
            
    return sorted(hora_counts.items(), key=lambda x: x[1], reverse=True)

def get_canciones_cantadas_por_mesa(db: Session):
    """Cantidad de canciones cantadas por mesa."""
    all_songs = cache.get_all_songs()
    cantadas = [s for s in all_songs if s.get("estado") == "cantada"]
    
    # Mapear usuario -> mesa desde la BD
    usuarios = db.query(models.Usuario).all()
    user_to_mesa = {u.id: u.mesa_id for u in usuarios if u.mesa_id}
    
    mesa_counts = Counter()
    
    for s in cantadas:
        m_id = user_to_mesa.get(s.get("usuario_id"))
        if m_id:
            mesa_counts[m_id] += 1
            
    # Nombres de mesas del cache
    mesas = {m.get("id"): m.get("nombre") for m in cache.get_all_mesas()}
    
    results = [
        (mesas.get(m_id, f"Mesa #{m_id}"), count) 
        for m_id, count in mesa_counts.items()
    ]
    return sorted(results, key=lambda x: x[1], reverse=True)

def get_canciones_mas_rechazadas(db: Session, limit: int = 10):
    """Reporte de canciones más rechazadas."""
    all_songs = cache.get_all_songs()
    rechazadas = [s for s in all_songs if s.get("estado") == "rechazada"]
    
    counts = Counter((s.get("titulo"), s.get("youtube_id")) for s in rechazadas)
    items = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    
    return [(titulo, y_id, count) for (titulo, y_id), count in items]

def get_usuarios_mas_rechazados(db: Session, limit: int = 10):
    """Usuarios con más canciones rechazadas."""
    all_songs = cache.get_all_songs()
    rechazadas = [s for s in all_songs if s.get("estado") == "rechazada"]
    
    user_counts = Counter(s.get("usuario_id") for s in rechazadas)
    user_ids = [u_id for u_id, _ in user_counts.most_common(limit)]
    
    usuarios = db.query(models.Usuario).filter(models.Usuario.id.in_(user_ids)).all()
    user_map = {u.id: u.nick for u in usuarios}
    
    return [
        (user_map.get(u_id, f"Usuario #{u_id}"), count) 
        for u_id, count in user_counts.most_common(limit)
    ]

def get_ingresos_por_categoria(db: Session):
    """Ingresos por categoría de producto."""
    consumos = cache.get_all_consumos()
    if not consumos:
        return []
    
    # Necesitamos categorías de los productos en BD
    product_ids = {c.get("producto_id") for c in consumos}
    productos = db.query(models.Producto).filter(models.Producto.id.in_(product_ids)).all()
    prod_cat_map = {p.id: p.categoria for p in productos}
    
    cat_income = Counter()
    for c in consumos:
        cat = prod_cat_map.get(c.get("producto_id"), "Sin Categoría")
        cat_income[cat] += float(c.get("valor_total", 0))
        
    return sorted(cat_income.items(), key=lambda x: x[1], reverse=True)


# ========================================================================
# REPORT FUNCTIONS PREVIOUSLY DELETED DURING CACHE MIGRATION
# RESTORED TO FIX ADMIN DASHBOARD /REPORTS
# ========================================================================

def get_total_ingresos(db: Session):
    consumos = cache.get_all_consumos()
    return sum(float(c.get("valor_total", 0)) for c in consumos)

def get_ingresos_por_mesa(db: Session):
    consumos = cache.get_all_consumos()
    mesas_list = cache.get_all_mesas()
    mesas = {m["id"]: m.get("nombre", f"Mesa {m.get('id')}") for m in mesas_list}
    ingresos = {}
    for c in consumos:
        mesa_id = c.get("mesa_id")
        if not mesa_id: continue
        val = float(c.get("valor_total", 0))
        ingresos[mesa_id] = ingresos.get(mesa_id, 0) + val
    result = []
    for mid, total in ingresos.items():
        if mid in mesas:
            result.append((mesas[mid], total))
    result.sort(key=lambda x: x[1], reverse=True)
    return result

def get_productos_menos_consumidos(db: Session, limit: int = 5):
    consumos = cache.get_all_consumos()
    productos = db.query(models.Producto).all()
    cantidades = {p.id: 0 for p in productos}
    for c in consumos:
        pid = c.get("producto_id")
        if pid in cantidades:
            cantidades[pid] += c.get("cantidad", 1)
    
    prod_map = {p.id: p.nombre for p in productos}
    result = [(prod_map[pid], cant) for pid, cant in cantidades.items()]
    result.sort(key=lambda x: x[1])
    return result[:limit]

def get_top_consumers_one_song(db: Session, limit: int = 10):
    canciones = cache.get_all_songs()
    consumos = cache.get_all_consumos()
    usuarios = db.query(models.Usuario).all()
    user_map = {u.id: u.nick for u in usuarios}
    
    canciones_por_user = {}
    for c in canciones:
        uid = c.get("usuario_id")
        if uid: canciones_por_user[uid] = canciones_por_user.get(uid, 0) + 1
        
    users_one_song = {uid for uid, count in canciones_por_user.items() if count == 1}
    
    gastos = {}
    for c in consumos:
        uid = c.get("usuario_id")
        if uid in users_one_song:
            gastos[uid] = gastos.get(uid, 0) + float(c.get("valor_total", 0))
            
    result = [(user_map.get(uid, f"User {uid}"), total) for uid, total in gastos.items()]
    result.sort(key=lambda x: x[1], reverse=True)
    return result[:limit]

def get_categorias_mas_consumidas_por_mesa(db: Session, mesa_id: int, limit: int = 5):
    consumos = [c for c in cache.get_all_consumos() if c.get("mesa_id") == mesa_id]
    productos = db.query(models.Producto).all()
    prod_cat_map = {p.id: p.categoria for p in productos}
    
    cat_counts = {}
    for c in consumos:
        pid = c.get("producto_id")
        cat = prod_cat_map.get(pid, "Desconocida")
        cat_counts[cat] = cat_counts.get(cat, 0) + c.get("cantidad", 1)
        
    result = list(cat_counts.items())
    result.sort(key=lambda x: x[1], reverse=True)
    return result[:limit]

def get_canciones_mas_pedidas_por_mesa(db: Session, mesa_id: int, limit: int = 5):
    usuarios_mesa = [u.id for u in db.query(models.Usuario).filter(models.Usuario.mesa_id == mesa_id).all()]
    canciones = [c for c in cache.get_all_songs() if c.get("usuario_id") in usuarios_mesa]
    
    counts = {}
    for c in canciones:
        key = (c.get("titulo", "Desconocido"), c.get("youtube_id", ""))
        counts[key] = counts.get(key, 0) + 1
        
    result = [(titulo, yid, count) for (titulo, yid), count in counts.items()]
    result.sort(key=lambda x: x[2], reverse=True)
    return result[:limit]

def get_productos_mas_consumidos_por_mesa(db: Session, mesa_id: int, limit: int = 5):
    consumos = [c for c in cache.get_all_consumos() if c.get("mesa_id") == mesa_id]
    productos = db.query(models.Producto).all()
    prod_map = {p.id: p.nombre for p in productos}
    
    counts = {}
    for c in consumos:
        pid = c.get("producto_id")
        counts[pid] = counts.get(pid, 0) + c.get("cantidad", 1)
        
    result = [(prod_map.get(pid, "Desconocido"), count) for pid, count in counts.items()]
    result.sort(key=lambda x: x[1], reverse=True)
    return result[:limit]

def get_productos_no_consumidos(db: Session):
    consumos = cache.get_all_consumos()
    productos = db.query(models.Producto).all()
    
    consumidos_ids = {c.get("producto_id") for c in consumos}
    no_consumidos = [p for p in productos if p.id not in consumidos_ids]
    return no_consumidos

def get_usuarios_inactivos_consumo(db: Session, horas: int = 2):
    consumos = cache.get_all_consumos()
    usuarios = db.query(models.Usuario).all()
    
    last_consumo = {}
    from datetime import datetime, timedelta
    
    for c in consumos:
        uid = c.get("usuario_id")
        created = c.get("created_at")
        if uid and created:
            try:
                # Reemplazamos la Z que isoformat de Typescript o cache podría emitir
                created = created.replace("Z", "+00:00")
                dt = datetime.fromisoformat(created)
                if uid not in last_consumo or dt > last_consumo[uid]:
                    last_consumo[uid] = dt
            except ValueError:
                pass
                
    from security import now_bogota
    now = now_bogota()
    
    for uid in last_consumo:
        if last_consumo[uid].tzinfo is None:
            last_consumo[uid] = last_consumo[uid].replace(tzinfo=now.tzinfo)
            
    inactivos = []
    for u in usuarios:
        if u.id not in last_consumo:
            inactivos.append(u)
        else:
            diff = now - last_consumo[u.id]
            if diff > timedelta(hours=horas):
                inactivos.append(u)
                
    return inactivos

def get_usuarios_consumen_pero_no_cantan(db: Session, umbral_consumo: float = 100.0):
    canciones = cache.get_all_songs()
    consumos = cache.get_all_consumos()
    usuarios = db.query(models.Usuario).all()
    
    cantores = {c.get("usuario_id") for c in canciones if c.get("usuario_id")}
    
    gastos = {}
    for c in consumos:
        uid = c.get("usuario_id")
        if uid: 
            gastos[uid] = gastos.get(uid, 0) + float(c.get("valor_total", 0))
            
    result = []
    for u in usuarios:
        if u.id not in cantores and gastos.get(u.id, 0) > umbral_consumo:
            result.append(u)
            
    return result
