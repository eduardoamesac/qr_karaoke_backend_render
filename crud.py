"""
CRUD simplificado - Solo maneja modelos en BD: Usuario, Producto, Pago, AdminApiKey
Las tablas eliminadas (Mesa, Cancion, Consumo, BannedNick, AdminLog) se manejan en CACHE JSON
"""

from sqlalchemy.orm import Session
import logging
from fastapi import HTTPException
from sqlalchemy import func
import secrets
from typing import List, Optional
import datetime
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

    # Calcular valor total
    valor_total = float(db_producto.valor * consumo.cantidad)

    consumo_obj = {
        "cantidad": consumo.cantidad,
        "valor_total": valor_total,
        "mesa_id": usuario.mesa_id,
        "usuario_id": usuario_id,
        "producto_id": consumo.producto_id,
        "created_at": datetime.datetime.now().isoformat()
    }
    
    consumo_id = cache.add_consumo(consumo_obj)
    consumo_obj["id"] = consumo_id
    
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
        "total_consumido": total_consumido,
        "total_pagado": total_pagado,
        "saldo_pendiente": saldo_pendiente,
        "consumos": consumos_items,
        "pagos": pagos_detalle
    }

def get_all_tables_payment_status(db: Session):
    """Devuelve el estado de cuenta para todas las mesas (lista de dicts)."""
    mesas = cache.get_all_mesas() or []
    result = []
    for m in mesas:
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
    upcoming.sort(key=lambda s: s.get("orden_manual", 0) or s.get("created_at", ""))
    lazy_queue.sort(key=lambda s: s.get("orden_manual", 0) or s.get("created_at", ""))
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
            cache.update_song(cancion_actual['id'], {
                'estado': 'cantada',
                'finished_at': now_bogota().isoformat()
            })

        # 2) Pop / iniciar la siguiente canción aprobada
        siguiente = queue_manager.pop_next_song(db)

        # 3) Refrescar y notificar via websocket
        queue_manager.refresh_queue(db)
        try:
            await websocket_manager.manager.broadcast_queue_update()
        except Exception:
            logger.exception('Error broadcasting queue_update after advancing cola')

        # 4) Si hay siguiente, emitir play_song
        if siguiente:
            try:
                await websocket_manager.manager.broadcast_play_song(
                    youtube_id=siguiente.get('youtube_id'),
                    duration_seconds=int(siguiente.get('duracion_seconds', 0) or 0)
                )
            except Exception:
                logger.exception('Error broadcasting play_song after advancing cola')

        return siguiente
    except Exception as e:
        # Log completo con traceback y levantar HTTPException para que FastAPI retorne JSON
        tb = traceback.format_exc()
        logger = logging.getLogger(__name__)
        logger.error('avanzar_cola_automaticamente failed: %s\n%s', str(e), tb)
        raise HTTPException(status_code=500, detail=f"Error advancing queue: {str(e)}")

def get_canciones_pendientes(db: Session):
    """Obtiene todas las canciones pendientes de aprobación."""
    all_songs = cache.get_all_songs()
    return [s for s in all_songs if s.get("estado") == "pendiente"]

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
