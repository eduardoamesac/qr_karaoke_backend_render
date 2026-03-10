"""
Módulo CRUD para Canciones y Cola de Karaoke.
Gestiona la cola de reproducción (CACHE JSON) con lógica Round-Robin y cola Lazy.
"""

from sqlalchemy.orm import Session
import logging
from fastapi import HTTPException
import datetime
from collections import Counter

import models
import schemas
from cache_manager import cache_manager as cache
from queue_manager import queue_manager


# ================================================================================
# FUNCIONES BASE DE CANCIONES (En CACHE JSON)
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


def update_cancion_estado(db: Session, cancion_id: int, nuevo_estado: str):
    """Actualiza el estado de una canción en cache."""
    all_songs = cache.get_all_songs()
    for song in all_songs:
        if song.get("id") == cancion_id:
            song["estado"] = nuevo_estado
            cache.update_song(cancion_id, {"estado": nuevo_estado})
            return song
    return None


def get_canciones_pendientes(db: Session):
    """Obtiene todas las canciones pendientes de aprobación."""
    all_songs = cache.get_all_songs()
    return [s for s in all_songs if s.get("estado") == "pendiente"]


# ================================================================================
# CRÉDITOS DE CANCIONES
# ================================================================================

def get_available_song_credits(db: Session, usuario_id: int) -> int:
    """Obtiene los créditos disponibles de canciones para un usuario."""
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario:
        return 0
    return usuario.song_credits or 1


def get_user_credits_detail(db: Session, usuario_id: int):
    """Obtiene los detalles de créditos del usuario."""
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario:
        return {"creditos": 0, "proxima_renovacion": None}
    return {
        "creditos": usuario.song_credits or 1,
        "proxima_renovacion": usuario.credits_added_at
    }


def consume_song_credit(db: Session, usuario_id: int, cancion_id: int) -> bool:
    """Consume un crédito de canción del usuario."""
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario or (usuario.song_credits or 0) <= 0:
        return False
    usuario.song_credits = (usuario.song_credits or 1) - 1
    db.commit()
    return True


# ================================================================================
# COLA DE REPRODUCCIÓN
# ================================================================================

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
    return None


def check_and_approve_next_lazy_song(db: Session):
    """Aprueba automáticamente la siguiente canción lazy si aplica."""
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

        canciones_reproduciendo = cache.get_songs_by_estado('reproduciendo') or []
        cancion_actual = canciones_reproduciendo[0] if canciones_reproduciendo else None

        if cancion_actual:
            logger.info(
                f"🏁 Finalizando canción actual: {cancion_actual.get('titulo')} "
                f"(ID: {cancion_actual.get('id')})"
            )
            cache.update_song(cancion_actual['id'], {
                'estado': 'cantada',
                'finished_at': now_bogota().isoformat()
            })
        else:
            logger.info("ℹ️ No hay canción reproduciéndose actualmente.")

        siguiente = queue_manager.pop_next_song(db)

        queue_manager.refresh_all(db)

        try:
            await websocket_manager.manager.broadcast_queue_update()
        except Exception:
            logger.exception('❌ Error broadcasting queue_update after advancing cola')

        if siguiente:
            siguiente = enriquecer_cancion(db, siguiente)
            logger.info(
                f"🎵 Iniciando siguiente canción: {siguiente.get('titulo')} "
                f"(ID: {siguiente.get('id')})"
            )
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
        tb = traceback.format_exc()
        logger = logging.getLogger(__name__)
        logger.error('❌ avanzar_cola_automaticamente failed: %s\n%s', str(e), tb)
        raise HTTPException(status_code=500, detail=f"Error advancing queue: {str(e)}")


# ================================================================================
# COLA LAZY
# ================================================================================

def get_cola_lazy(db: Session):
    """Obtiene la cola de canciones pendiente_lazy (CACHE)."""
    all_songs = cache.get_all_songs()
    lazy = [s for s in all_songs if s.get("estado") == "pendiente_lazy"]
    lazy.sort(key=lambda s: (s.get("orden_manual", 999999) or 999999, s.get("created_at", "")))
    return lazy


def aprobar_siguiente_cancion_lazy(db: Session):
    """Aprueba la siguiente canción en la cola lazy (pendiente_lazy -> aprobado)."""
    all_songs = cache.get_all_songs()
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


def get_cola_completa_con_lazy(db: Session):
    """Obtiene la cola completa con todas las canciones agrupadas por estado."""
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

    upcoming.sort(key=lambda s: (s.get("orden_manual", 999999) or 999999, s.get("created_at", "")))
    lazy_queue.sort(key=lambda s: (s.get("orden_manual", 999999) or 999999, s.get("created_at", "")))
    pending.sort(key=lambda s: s.get("created_at", ""))

    return {
        "now_playing": now_playing,
        "upcoming": upcoming,
        "lazy_queue": lazy_queue,
        "pending": pending
    }


def move_lazy_song_up(db: Session, cancion_id: int, usuario_id: int):
    """Mueve una canción lazy hacia arriba, verificando pertenencia."""
    from queue_synchronizer import QueueSynchronizer

    cancion = cache.get_song_by_id(cancion_id)
    if not cancion or cancion.get("usuario_id") != usuario_id:
        return None

    result = QueueSynchronizer.reorder_lazy_queue_safely(
        db, cancion_id, "up", audit_user=f"user_{usuario_id}"
    )

    if result["success"]:
        updated_song = cache.get_song_by_id(cancion_id)
        return enriquecer_cancion(db, updated_song)
    return None


def move_lazy_song_down(db: Session, cancion_id: int, usuario_id: int):
    """Mueve una canción lazy hacia abajo, verificando pertenencia."""
    from queue_synchronizer import QueueSynchronizer

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


# ================================================================================
# COLA COMPLETA
# ================================================================================

def enriquecer_cancion(db: Session, song: dict):
    """Enriquece una canción del cache con info del usuario desde BD."""
    cancion_enriquecida = dict(song)
    usuario_id = song.get("usuario_id")

    usuario = (
        db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
        if usuario_id else None
    )

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
# ESTADÍSTICAS DE CANCIONES
# ================================================================================

def get_canciones_mas_cantadas(db: Session, limit: int = 10):
    """Reporte de canciones más cantadas."""
    all_songs = cache.get_all_songs()
    cantadas = [s for s in all_songs if s.get("estado") == "cantada"]

    counts = Counter((s.get("titulo"), s.get("youtube_id")) for s in cantadas)
    items = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]

    return [(titulo, y_id, count) for (titulo, y_id), count in items]


def get_canciones_mas_rechazadas(db: Session, limit: int = 10):
    """Reporte de canciones más rechazadas."""
    all_songs = cache.get_all_songs()
    rechazadas = [s for s in all_songs if s.get("estado") == "rechazada"]

    counts = Counter((s.get("titulo"), s.get("youtube_id")) for s in rechazadas)
    items = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]

    return [(titulo, y_id, count) for (titulo, y_id), count in items]


def get_canciones_cantadas_por_usuario(db: Session):
    """Reporte de canciones cantadas por cada usuario."""
    all_songs = cache.get_all_songs()
    cantadas = [s for s in all_songs if s.get("estado") == "cantada"]

    user_counts = Counter(s.get("usuario_id") for s in cantadas)

    user_ids = list(user_counts.keys())
    usuarios = db.query(models.Usuario).filter(models.Usuario.id.in_(user_ids)).all()
    user_map = {u.id: u.nick for u in usuarios}

    results = [
        (user_map.get(u_id, f"Usuario #{u_id}"), count)
        for u_id, count in user_counts.items()
    ]
    return sorted(results, key=lambda x: x[1], reverse=True)


def get_canciones_cantadas_por_mesa(db: Session):
    """Cantidad de canciones cantadas por mesa."""
    all_songs = cache.get_all_songs()
    cantadas = [s for s in all_songs if s.get("estado") == "cantada"]

    usuarios = db.query(models.Usuario).all()
    user_to_mesa = {u.id: u.mesa_id for u in usuarios if u.mesa_id}

    mesa_counts = Counter()
    for s in cantadas:
        m_id = user_to_mesa.get(s.get("usuario_id"))
        if m_id:
            mesa_counts[m_id] += 1

    mesas = {m.get("id"): m.get("nombre") for m in cache.get_all_mesas()}

    results = [
        (mesas.get(m_id, f"Mesa #{m_id}"), count)
        for m_id, count in mesa_counts.items()
    ]
    return sorted(results, key=lambda x: x[1], reverse=True)


def get_actividad_por_hora(db: Session):
    """Reporte de canciones cantadas por hora."""
    all_songs = cache.get_all_songs()
    cantadas = [
        s for s in all_songs
        if s.get("estado") == "cantada" and s.get("started_at")
    ]

    hora_counts = Counter()
    for s in cantadas:
        try:
            dt = datetime.datetime.fromisoformat(s.get("started_at"))
            hora_counts[dt.hour] += 1
        except Exception:
            continue

    return sorted(hora_counts.items(), key=lambda x: x[1], reverse=True)


def get_tiempo_promedio_espera(db: Session):
    """Tiempo promedio de espera (created_at hasta finished_at)."""
    all_songs = cache.get_all_songs()
    cantadas = [
        s for s in all_songs
        if s.get("estado") == "cantada" and s.get("finished_at") and s.get("created_at")
    ]

    if not cantadas:
        return 0

    total_seconds = 0
    for s in cantadas:
        try:
            start = datetime.datetime.fromisoformat(s.get("created_at"))
            end = datetime.datetime.fromisoformat(s.get("finished_at"))
            total_seconds += (end - start).total_seconds()
        except Exception:
            continue

    return total_seconds / len(cantadas)


def get_canciones_mas_pedidas_por_mesa(db: Session, mesa_id: int, limit: int = 5):
    """Reporte de canciones más pedidas en una mesa específica."""
    usuarios_mesa = [
        u.id for u in db.query(models.Usuario).filter(
            models.Usuario.mesa_id == mesa_id
        ).all()
    ]
    canciones = [
        c for c in cache.get_all_songs()
        if c.get("usuario_id") in usuarios_mesa
    ]

    counts = {}
    for c in canciones:
        key = (c.get("titulo", "Desconocido"), c.get("youtube_id", ""))
        counts[key] = counts.get(key, 0) + 1

    result = [(titulo, yid, count) for (titulo, yid), count in counts.items()]
    result.sort(key=lambda x: x[2], reverse=True)
    return result[:limit]
