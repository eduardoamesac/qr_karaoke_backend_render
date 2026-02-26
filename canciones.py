import os
import datetime
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from typing import List

import crud, schemas, models, config
from database import SessionLocal
import websocket_manager
from security import api_key_auth
from cache_manager import cache_manager
from queue_manager import queue_manager

router = APIRouter()

# Dependencia para obtener la sesión de la base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- ENDPOINT: Avanzar la cola manualmente ---
@router.post(
    "/siguiente",
    response_model=schemas.PlayNextResponse,
    responses={204: {"description": "No hay más canciones en la cola."}},
    summary="Avanzar la cola y obtener la siguiente canción para reproducir"
)
async def avanzar_cola(db: Session = Depends(get_db)):
    """
    Avanza la cola a la siguiente canción.
    """
    nueva_cancion = await crud.avanzar_cola_automaticamente(db)

    if not nueva_cancion:
        return Response(status_code=204)

    youtube_url = f"https://www.youtube.com/embed/{nueva_cancion['youtube_id']}?autoplay=1&fs=1"

    return schemas.PlayNextResponse(
        play_url=youtube_url,
        cancion=nueva_cancion
    )

# --- ENDPOINT: Añadir canción ---
@router.post(
    "/{usuario_id}",
    response_model=schemas.Cancion,
    summary="Añadir una canción a la lista de un usuario"
)
async def anadir_cancion(
    usuario_id: int,
    cancion: schemas.CancionCreate,
    db: Session = Depends(get_db)
):
    """
    Añade una nueva canción a la lista personal de un usuario, si hay créditos disponibles.
    """
    db_usuario = crud.get_usuario_by_id(db, usuario_id=usuario_id)
    if not db_usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    if db_usuario.is_silenced:
        raise HTTPException(status_code=403, detail="No tienes permiso para añadir más canciones.")

    # Cargar configuraciones de la cola lazy
    from settings_storage import load_settings
    settings = load_settings()
    allow_unrestricted = settings.get("lazy_queue_allow_unrestricted", False)
    max_concurrent_songs = settings.get("lazy_queue_max_concurrent_songs", 10)

    # Validar límite de canciones concurrentes
    canciones_usuario = [c for c in cache_manager.get_songs_by_user(usuario_id) 
                         if c.get("estado") in ["pendiente", "pendiente_lazy", "aprobado"]]
    if len(canciones_usuario) >= max_concurrent_songs:
        raise HTTPException(
            status_code=403,
            detail=f"Has alcanzado el límite máximo de {max_concurrent_songs} canciones en espera."
        )

    # Validar créditos (sólo si no está en modo sin restricciones)
    if not allow_unrestricted:
        available_credits = crud.get_available_song_credits(db, usuario_id)
        if available_credits <= 0:
            credits_detail = crud.get_user_credits_detail(db, usuario_id)
            raise HTTPException(
                status_code=402,
                detail=f"No tienes créditos disponibles para agregar canciones. Debes hacer un pedido para restablecer tus derechos. Minutos hasta alcanzar 0: {credits_detail.get('minutes_to_zero', 0):.1f}"
            )


    hora_cierre_str = config.settings.KARAOKE_CIERRE
    try:
        h, m = map(int, hora_cierre_str.split(':'))
        from timezone_utils import now_bogota
        ahora = now_bogota()
        hora_cierre = ahora.replace(hour=h, minute=m, second=0, microsecond=0)
        if hora_cierre < ahora:
            hora_cierre += datetime.timedelta(days=1)
    except (ValueError, TypeError):
        raise HTTPException(status_code=500, detail="Formato de hora de cierre inválido.")

    if ahora >= hora_cierre:
        raise HTTPException(status_code=400, detail="Ya no se aceptan más canciones por hoy.")

    tiempo_restante_segundos = (hora_cierre - ahora).total_seconds()
    duracion_cola_actual = crud.get_duracion_total_cola_aprobada(db)
    duracion_total_proyectada = duracion_cola_actual + (cancion.duracion_seconds or 0)

    if duracion_total_proyectada > tiempo_restante_segundos:
        raise HTTPException(
            status_code=400,
            detail="No hay tiempo suficiente para añadir esta canción antes del cierre."
        )

    cancion_existente = crud.check_if_song_in_user_list(db, usuario_id=usuario_id, youtube_id=cancion.youtube_id)
    if cancion_existente:
        raise HTTPException(
            status_code=409,
            detail=f"Esta canción ya está en la cola de tu mesa. '{cancion.titulo}' fue agregada por otro usuario de tu mesa."
        )

    db_cancion = crud.create_cancion_para_usuario(db=db, cancion=cancion, usuario_id=usuario_id)
    
    cancion_dict = jsonable_encoder(db_cancion)
    cache_manager.add_song_to_cache(usuario_id, cancion_dict)
    
    if not crud.consume_song_credit(db, usuario_id, db_cancion['id']):
        cache_manager.delete_song_from_cache(db_cancion['id'], usuario_id=usuario_id)
        raise HTTPException(status_code=402, detail="Error al consumir crédito. Intenta nuevamente.")
    
    cancion_final = crud.update_cancion_estado(db, cancion_id=db_cancion['id'], nuevo_estado="pendiente_lazy")
    
    canciones_activas = (cache_manager.get_songs_by_estado("reproduciendo") or []) + (cache_manager.get_songs_by_estado("aprobado") or [])
    hay_cancion_activa = len(canciones_activas) > 0
    
    if not hay_cancion_activa:
        cancion_final = crud.update_cancion_estado(db, cancion_id=db_cancion['id'], nuevo_estado="aprobado")
        await crud.start_next_song_if_autoplay_and_idle(db)
    
    queue_manager.refresh_queue(db)
    await websocket_manager.manager.broadcast_queue_update()

    return cancion_final

@router.get("/{usuario_id}/lista", response_model=List[schemas.Cancion], summary="Ver la lista de canciones de un usuario")
def ver_lista_de_canciones(usuario_id: int, db: Session = Depends(get_db)):
    """
    Obtiene la lista de canciones del usuario desde el cache sincronizado.
    """
    return queue_manager.get_user_songs(db, usuario_id)

@router.get("/pendientes", response_model=List[schemas.CancionAdminView], summary="Ver todas las canciones pendientes")
def ver_canciones_pendientes(db: Session = Depends(get_db), api_key: str = Depends(api_key_auth)):
    return crud.get_canciones_pendientes(db=db)

@router.post("/{cancion_id}/aprobar", response_model=schemas.Cancion, summary="Aprobar una canción")
async def aprobar_cancion(cancion_id: int, db: Session = Depends(get_db), api_key: str = Depends(api_key_auth)):
    db_cancion = crud.update_cancion_estado(db, cancion_id=cancion_id, nuevo_estado="aprobado")
    if not db_cancion:
        raise HTTPException(status_code=404, detail="Canción no encontrada")
    await crud.start_next_song_if_autoplay_and_idle(db)
    queue_manager.refresh_queue(db)
    await websocket_manager.manager.broadcast_queue_update()
    return db_cancion

@router.post("/{cancion_id}/rechazar", response_model=schemas.Cancion, summary="Rechazar una canción")
async def rechazar_cancion(cancion_id: int, db: Session = Depends(get_db), api_key: str = Depends(api_key_auth)):
    db_cancion = cache_manager.get_song_by_id(cancion_id)
    
    if not db_cancion:
        raise HTTPException(status_code=404, detail="Canción no encontrada")
    
    # Validar que la canción no esté ya reproduciéndose o cantada
    if db_cancion.get('estado') in ['reproduciendo', 'cantada']:
        raise HTTPException(status_code=403, detail="No se puede eliminar: la canción ya está en reproducción o fue cantada")
    
    # Solo se pueden rechazar canciones en estado 'pendiente', 'pendiente_lazy' o 'aprobado' (si no está sonando)
    if db_cancion.get('estado') not in ['pendiente', 'pendiente_lazy', 'aprobado']:
        raise HTTPException(status_code=403, detail="Solo se pueden eliminar canciones pendientes, en cola lazy o aprobadas")
    
    db_cancion = crud.update_cancion_estado(db, cancion_id=cancion_id, nuevo_estado="rechazada")
    
    # NUEVO: Refrescar la cola ANTES de chequear la siguiente lazy para que el cache esté al día
    queue_manager.refresh_queue(db)
    crud.check_and_approve_next_lazy_song(db)
    
    await websocket_manager.manager.broadcast_queue_update()
    return db_cancion

@router.post("/admin/add", response_model=schemas.Cancion, summary="[Admin] Añadir una canción como DJ")
async def admin_anadir_cancion(cancion: schemas.CancionCreate, db: Session = Depends(get_db), api_key: str = Depends(api_key_auth)):
    dj_user = crud.get_or_create_dj_user(db)
    db_cancion = crud.create_cancion_para_usuario(db=db, cancion=cancion, usuario_id=dj_user.id)
    
    # db_cancion es un dict (viene del cache JSON)
    cancion_id = db_cancion['id']
    
    # LAZY APPROVAL: Solo aprobar si no hay nada en la cola
    canciones_activas = (cache_manager.get_songs_by_estado("reproduciendo") or []) + (cache_manager.get_songs_by_estado("aprobado") or [])
    hay_cancion_activa = len(canciones_activas) > 0
    
    if hay_cancion_activa:
        cancion_final = crud.update_cancion_estado(db, cancion_id=cancion_id, nuevo_estado="pendiente_lazy")
    else:
        cancion_final = crud.update_cancion_estado(db, cancion_id=cancion_id, nuevo_estado="aprobado")
        await crud.start_next_song_if_autoplay_and_idle(db)
    
    queue_manager.refresh_queue(db)
    await websocket_manager.manager.broadcast_queue_update()
    return cancion_final


@router.get("/cola", response_model=schemas.ColaView, summary="Ver la cola de canciones")
def ver_cola_de_canciones(db: Session = Depends(get_db)):
    cola_data = crud.get_cola_completa(db)
    return schemas.ColaView(now_playing=cola_data["now_playing"], upcoming=cola_data["upcoming"])

@router.get("/cola/extended", response_model=schemas.ColaViewExtended, summary="Ver la cola de canciones con lazy queue")
def ver_cola_extendida(db: Session = Depends(get_db)):
    """
    Retorna la cola completa incluyendo:
    - now_playing: Canción actual
    - upcoming: Siguiente canción aprobada (máximo 1)
    - lazy_queue: Canciones en espera de aprobación lazy
    - pending: Canciones pendientes de aprobación manual
    """
    cola_data = crud.get_cola_completa_con_lazy(db)
    return schemas.ColaViewExtended(
        now_playing=cola_data["now_playing"],
        upcoming=cola_data["upcoming"],
        lazy_queue=cola_data["lazy_queue"],
        pending=cola_data["pending"]
    )


@router.get("/{cancion_id}/tiempo-espera", response_model=dict, summary="Calcular tiempo de espera")
def calcular_tiempo_espera(cancion_id: int, db: Session = Depends(get_db)):
    tiempo_segundos = crud.get_tiempo_espera_para_cancion(db, cancion_id=cancion_id)
    if tiempo_segundos == -1:
        raise HTTPException(status_code=404, detail="La canción no está en la cola.")
    return {"tiempo_espera_segundos": tiempo_segundos}

@router.post("/{cancion_id}/play", status_code=200, summary="Reproducir una canción en el player")
async def play_song_now(cancion_id: int, db: Session = Depends(get_db), api_key: str = Depends(api_key_auth)):
    """
    **[Admin]** Envía la orden de reproducir una canción específica en el player.
    """
    db_cancion = cache_manager.get_song_by_id(cancion_id)
    if not db_cancion:
        raise HTTPException(status_code=404, detail="Canción no encontrada.")

    from timezone_utils import now_bogota

    canciones_reproduciendo = cache_manager.get_songs_by_estado('reproduciendo')
    if canciones_reproduciendo:
        current_playing = canciones_reproduciendo[0]
        if current_playing['id'] != cancion_id:
            cache_manager.update_song_in_cache(current_playing['id'], {
                'estado': 'cantada',
                'finished_at': now_bogota().isoformat()
            })

    cache_manager.update_song_in_cache(cancion_id, {
        'estado': 'reproduciendo',
        'started_at': now_bogota().isoformat()
    })
    
    db_cancion = cache_manager.get_song_by_id(cancion_id)
    
    queue_manager.refresh_queue(db)
    await websocket_manager.manager.broadcast_queue_update()
    await websocket_manager.manager.broadcast_play_song(
        youtube_id=db_cancion['youtube_id'],
        duration_seconds=db_cancion.get('duracion_seconds', 0)
    )

    return {"mensaje": f"Reproduciendo: {db_cancion['titulo']}"}

@router.delete("/{cancion_id}", status_code=204, summary="Eliminar una canción de la lista personal")
async def eliminar_cancion(cancion_id: int, usuario_id: int, db: Session = Depends(get_db)):
    """
    [Usuario] Elimina una canción de su propia lista.
    Solo se puede eliminar si la canción pertenece al usuario y está en estado 'pendiente' o 'aprobado'.
    No se puede eliminar si ya está 'reproduciendo' o 'cantada'.
    """
    db_cancion = cache_manager.get_song_by_id(cancion_id)

    if not db_cancion or db_cancion.get('usuario_id') != usuario_id:
        raise HTTPException(status_code=404, detail="Canción no encontrada o no te pertenece.")
    
    if db_cancion.get('estado') not in ['pendiente', 'aprobado', 'pendiente_lazy']:
        raise HTTPException(status_code=400, detail="No se puede eliminar una canción que ya está reproduciendo o ha sido cantada.")

    fue_aprobada = db_cancion.get('estado') == 'aprobado'
    
    cache_manager.delete_song_from_cache(cancion_id, usuario_id=usuario_id)
    
    queue_manager.refresh_queue(db)
    
    if fue_aprobada:
        crud.check_and_approve_next_lazy_song(db)
    
    await websocket_manager.manager.broadcast_queue_update()
    return Response(status_code=204)
@router.post("/{cancion_id}/mover-arriba", response_model=schemas.Cancion, summary="Mover una canciÃ³n pendiente_lazy hacia arriba")
async def mover_cancion_arriba(cancion_id: int, usuario_id: int, db: Session = Depends(get_db)):
    """
    [Usuario] Mueve una canciÃ³n pendiente_lazy hacia arriba en su cola personal.
    Solo funciona para canciones del usuario actual en estado pendiente_lazy.
    """
    db_cancion = crud.move_lazy_song_up(db, cancion_id=cancion_id, usuario_id=usuario_id)
    
    if not db_cancion:
        raise HTTPException(status_code=404, detail="CanciÃ³n no encontrada o no te pertenece.")
    
    await websocket_manager.manager.broadcast_queue_update()
    return db_cancion

@router.post("/{cancion_id}/mover-abajo", response_model=schemas.Cancion, summary="Mover una canciÃ³n pendiente_lazy hacia abajo")
async def mover_cancion_abajo(cancion_id: int, usuario_id: int, db: Session = Depends(get_db)):
    """
    [Usuario] Mueve una canciÃ³n pendiente_lazy hacia abajo en su cola personal.
    Solo funciona para canciones del usuario actual en estado pendiente_lazy.
    """
    db_cancion = crud.move_lazy_song_down(db, cancion_id=cancion_id, usuario_id=usuario_id)
    
    if not db_cancion:
        raise HTTPException(status_code=404, detail="CanciÃ³n no encontrada o no te pertenece.")
    
    await websocket_manager.manager.broadcast_queue_update()
    return db_cancion
