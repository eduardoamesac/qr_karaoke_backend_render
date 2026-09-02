"""CRUD operations for Songs (in JSON cache)."""

import datetime
import time
import logging
from sqlalchemy.orm import Session

from app.schemas import CancionCreate
from app.utils.cache_manager import cache_manager as cache

logger = logging.getLogger(__name__)


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


def get_canciones_pendientes(db: Session):
    """Obtiene todas las canciones pendientes de aprobación."""
    all_songs = cache.get_all_songs()
    return [s for s in all_songs if s.get("estado") == "pendiente"]


def get_cola_lazy(db: Session):
    """Obtiene la cola de canciones pendiente_lazy (CACHE) ordenada."""
    all_songs = cache.get_all_songs()
    lazy = [s for s in all_songs if s.get("estado") == "pendiente_lazy"]
    
    def get_sort_key(s):
        try:
            val = s.get('orden_manual')
            return int(val) if val is not None else 999999
        except (ValueError, TypeError):
            return 999999

    lazy.sort(key=lambda s: (get_sort_key(s), str(s.get("created_at", ""))))
    return lazy


def get_available_song_credits(db: Session, usuario_id: int) -> int:
    """Obtiene los créditos disponibles de canciones para un usuario."""
    from app.db.crud.crud_usuarios import get_usuario_by_id
    usuario = get_usuario_by_id(db, usuario_id)
    if not usuario:
        return 0
    return usuario.song_credits if usuario.song_credits is not None else 0


def get_user_credits_detail(db: Session, usuario_id: int):
    """Obtiene los detalles de créditos del usuario."""
    from app.db.crud.crud_usuarios import get_usuario_by_id
    usuario = get_usuario_by_id(db, usuario_id)
    if not usuario:
        return {"creditos": 0, "proxima_renovacion": None}
    return {
        "creditos": usuario.song_credits if usuario.song_credits is not None else 0,
        "proxima_renovacion": usuario.credits_added_at
    }


def check_if_song_in_user_list(db: Session, usuario_id: int, youtube_id: str) -> bool:
    """Verifica si una canción ya está en la cola para el usuario o su mesa."""
    from app.db.crud.crud_usuarios import get_usuario_by_id
    usuario = get_usuario_by_id(db, usuario_id)
    if not usuario:
        return False

    mesa_id = getattr(usuario, "mesa_id", None)
    usuario_ids_mesa = {usuario_id}

    if mesa_id:
        try:
            usuarios_mesa = cache.get_usuarios_by_mesa_from_cache(mesa_id)
            if usuarios_mesa:
                for u in usuarios_mesa:
                    uid = u.get("id")
                    if uid:
                        usuario_ids_mesa.add(int(uid))
        except Exception:
            pass

    all_songs = cache.get_all_songs()
    for song in all_songs:
        # Solo considerar como duplicado si está en la cola activa (reproduciendo, aprobado, pendiente)
        if song.get("estado") in ["pendiente", "pendiente_lazy", "aprobado", "reproduciendo"]:
            if song.get("youtube_id") == youtube_id:
                if song.get("usuario_id") in usuario_ids_mesa:
                    return True
    return False


def create_cancion_para_usuario(db: Session, cancion: CancionCreate, usuario_id: int, local_id: int = None):
    """Crea una canción en cache para un usuario y le asocia el local_id correspondiente."""
    from app.utils.timezone_utils import now_bogota
    from app.db.crud.crud_usuarios import get_usuario_by_id

    if local_id is None:
        try:
            usuario = get_usuario_by_id(db, usuario_id)
            if usuario and getattr(usuario, "mesa_id", None):
                mesa = cache.get_mesa_by_id(usuario.mesa_id)
                if mesa and mesa.get("local_id"):
                    local_id = mesa.get("local_id")
        except Exception:
            pass

    song_id = int(time.time() * 1000) + usuario_id

    song_data = {
        "id": song_id,
        "youtube_id": cancion.youtube_id,
        "titulo": cancion.titulo,
        "duracion_seconds": cancion.duracion_seconds,
        "usuario_id": usuario_id,
        "local_id": local_id,
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
    """Consume un crédito de canción del usuario (actualiza en CACHE)."""
    from app.db.crud.crud_usuarios import get_usuario_by_id
    usuario = get_usuario_by_id(db, usuario_id)
    if not usuario or (usuario.song_credits or 0) <= 0:
        return False

    new_credits = max(0, (usuario.song_credits or 0) - 1)
    new_puntos = max(0, (usuario.puntos or 0) - 1)
    cache.update_usuario_en_cache(usuario_id, {"song_credits": new_credits, "puntos": new_puntos})
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


def get_duracion_total_cola_aprobada(db: Session, local_id: int = None) -> int:
    """Obtiene la duración total de la cola de canciones aprobadas para un local_id."""
    all_songs = cache.get_all_songs(local_id=local_id)
    total = 0
    for song in all_songs:
        if song.get("estado") == "aprobado":
            total += int(song.get("duracion_seconds", 0))
    return total


def check_and_approve_next_lazy_song(db: Session):
    """Aprueba automáticamente la siguiente canción lazy si aplica (stub)."""
    pass


def aprobar_siguiente_cancion_lazy(db: Session, local_id: int = None):
    """Aprueba la siguiente canción en la cola lazy (pendiente_lazy -> aprobado) para un local."""
    all_songs = cache.get_all_songs(local_id=local_id)
    lazy_songs = [s for s in all_songs if s.get("estado") == "pendiente_lazy"]
    if not lazy_songs:
        return None

    siguiente = lazy_songs[0]
    siguiente_id = siguiente.get("id")
    if not siguiente_id:
        return None

    update_data = {
        "estado": "aprobado",
        "approved_at": datetime.datetime.now().isoformat()
    }

    cache.update_song(siguiente_id, update_data)
    siguiente.update(update_data)
    return siguiente


def move_lazy_song_up(db: Session, cancion_id: int, usuario_id: int):
    """Mueve una canción lazy hacia arriba, verificando pertenencia."""
    cancion = cache.get_song_by_id(cancion_id)
    if not cancion or cancion.get("usuario_id") != usuario_id:
        return None

    try:
        from queue_synchronizer import QueueSynchronizer
        result = QueueSynchronizer.reorder_lazy_queue_safely(
            db, cancion_id, "up", audit_user=f"user_{usuario_id}"
        )
        if result["success"]:
            updated_song = cache.get_song_by_id(cancion_id)
            return enriquecer_cancion(db, updated_song)
    except ImportError:
        pass
    return None


def move_lazy_song_down(db: Session, cancion_id: int, usuario_id: int):
    """Mueve una canción lazy hacia abajo, verificando pertenencia."""
    cancion = cache.get_song_by_id(cancion_id)
    if not cancion or cancion.get("usuario_id") != usuario_id:
        return None

    try:
        from queue_synchronizer import QueueSynchronizer
        result = QueueSynchronizer.reorder_lazy_queue_safely(
            db, cancion_id, "down", audit_user=f"user_{usuario_id}"
        )
        if result["success"]:
            updated_song = cache.get_song_by_id(cancion_id)
            return enriquecer_cancion(db, updated_song)
    except ImportError:
        pass
    return None


def enriquecer_cancion(db: Session, song: dict):
    """
    Enriquece una canción del cache con info del usuario desde BD.
    """
    from app.db.crud.crud_usuarios import get_usuario_by_id
    from app.utils.timezone_utils import now_bogota
    
    # --- Asegurar campos obligatorios para el schema schemas.Cancion ---
    cancion_enriquecida = {
        "id": int(song.get("id") or 0),
        "titulo": song.get("titulo") or "Título desconocido",
        "youtube_id": song.get("youtube_id") or "",
        "duracion_seconds": int(song.get("duracion_seconds") or 0),
        "estado": song.get("estado", "pendiente"),
        "created_at": song.get("created_at") or now_bogota().isoformat(),
        "started_at": song.get("started_at") if song.get("started_at") else None,
        "finished_at": song.get("finished_at") if song.get("finished_at") else None,
        "puntuacion_ia": song.get("puntuacion_ia"),
        "is_karaoke": bool(song.get("is_karaoke", True)),
        "orden_manual": song.get("orden_manual"),
        "local_id": song.get("local_id")
    }

    usuario_id = song.get("usuario_id")
    usuario = None
    if usuario_id:
        try:
            usuario = get_usuario_by_id(db, usuario_id)
        except Exception:
            usuario = None
            
    if usuario:
        mesa_info = None
        if getattr(usuario, "mesa_id", None):
            try:
                from app.db.crud.crud_mesas import get_mesa_by_id
                mesa_obj = get_mesa_by_id(db, usuario.mesa_id)
                if mesa_obj:
                    mesa_info = {
                        "id": int(mesa_obj.get("id") or usuario.mesa_id),
                        "nombre": str(mesa_obj.get("nombre") or f"Mesa {usuario.mesa_id}")
                    }
            except Exception:
                pass

        cancion_enriquecida["usuario"] = {
            "id": usuario.id,
            "nick": usuario.nick,
            "puntos": usuario.puntos,
            "nivel": usuario.nivel,
            "song_credits": usuario.song_credits or 1,
            "is_silenced": usuario.is_silenced,
            "mesa": mesa_info
        }
    else:
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


def get_cola_completa(db: Session, local_id: int = None):
    """Obtiene la cola básica (now_playing y upcoming) para un local."""
    all_songs = cache.get_all_songs(local_id=local_id)

    now_playing = None
    upcoming = []

    for song in all_songs:
        try:
            if not song or not isinstance(song, dict): continue
            estado = song.get("estado")
            song_enriched = enriquecer_cancion(db, song)

            if estado == "reproduciendo":
                now_playing = song_enriched
            elif estado == "aprobado":
                upcoming.append(song_enriched)
        except Exception:
            continue

    return {
        "now_playing": now_playing,
        "upcoming": upcoming[:1]
    }


def get_cola_completa_con_lazy(db: Session, local_id: int = None):
    """Obtiene la cola completa con todas las canciones agrupadas por estado para un local."""
    all_songs = cache.get_all_songs(local_id=local_id)

    now_playing = None
    upcoming = []
    lazy_queue = []
    pending = []

    for song in all_songs:
        try:
            if not song or not isinstance(song, dict): continue
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
        except Exception:
            continue

    # --- Ordenamiento robusto para la respuesta de la cola ---
    def get_sort_key(s):
        try:
            val = s.get("orden_manual")
            order = int(val) if val is not None else 999999
        except (ValueError, TypeError):
            order = 999999
        return (order, str(s.get("created_at", "")))

    upcoming.sort(key=get_sort_key)
    lazy_queue.sort(key=get_sort_key)
    pending.sort(key=lambda s: str(s.get("created_at", "")))

    return {
        "now_playing": now_playing,
        "upcoming": upcoming,
        "lazy_queue": lazy_queue,
        "pending": pending
    }


async def avanzar_cola_automaticamente(db: Session, local_id: int = None):
    """Avanza la cola automáticamente (siguiente canción) para un local específico."""
    import traceback
    from fastapi import HTTPException
    from app.services.queue_manager import queue_manager

    try:
        from app.utils.timezone_utils import now_bogota
        from app.services import websocket_manager

        canciones_reproduciendo = cache.get_songs_by_estado('reproduciendo', local_id=local_id) or []
        cancion_actual = canciones_reproduciendo[0] if canciones_reproduciendo else None

        if cancion_actual:
            logger.info(f"🏁 Finalizando canción actual ({cancion_actual.get('titulo')}) para local {local_id}")
            cache.update_song(cancion_actual['id'], {
                'estado': 'cantada',
                'finished_at': now_bogota().isoformat()
            })

        siguiente = queue_manager.pop_next_song(db, local_id=local_id)
        queue_manager.refresh_all(db)

        # --- Broadcast con el estado real del CACHE JSON para este local ---
        try:
            new_queue_state = get_cola_completa_con_lazy(db, local_id=local_id)
            await websocket_manager.manager.broadcast_queue_update(new_queue_state, local_id=local_id)
        except Exception:
            logger.exception('❌ Error broadcasting queue_update after advancing cola')

        if siguiente:
            siguiente = enriquecer_cancion(db, siguiente)
            logger.info(f"🎵 Iniciando siguiente canción: {siguiente.get('titulo')} (local {local_id})")
            try:
                await websocket_manager.manager.broadcast_play_song(
                    youtube_id=siguiente.get('youtube_id'),
                    duration_seconds=int(siguiente.get('duracion_seconds', 0) or 0),
                    local_id=local_id
                )
            except Exception:
                logger.exception('❌ Error broadcasting play_song after advancing cola')
        else:
            logger.info(f"📭 No hay más canciones en cola para local {local_id}.")

        return siguiente
    except Exception as e:
        tb = traceback.format_exc()
        logger.error('❌ avanzar_cola_automaticamente failed: %s\n%s', str(e), tb)
        raise HTTPException(status_code=500, detail=f"Error advancing queue: {str(e)}")
