"""
Servicio de background para decrementar créditos de canciones (usando CACHE JSON).
Los créditos decaen 100 puntos cada minuto hasta llegar a 0.
"""

import asyncio
from app.timezone_utils import now_bogota
from app.utils.cache_manager import cache_manager
import logging

logger = logging.getLogger(__name__)

async def credits_decay_worker():
    """
    Tarea de background que se ejecuta cada minuto para:
    1. Decrementar créditos y puntos de los usuarios según la tasa de decaimiento (decay_rate).
    2. Actualizar el caché de cada usuario.
    3. Notificar vía WebSocket a los clientes para refrescar su perfil.
    """
    from app.services.settings_storage import load_settings
    from app.services.websocket_manager import manager as websocket_manager
    
    while True:
        try:
            settings = load_settings()
            decay_rate = settings.get("lazy_queue_decay_rate", 100)
            
            # Solo decaer si la tasa de decaimiento es mayor que 0
            if decay_rate > 0:
                usuarios = cache_manager.get_all_usuarios_from_cache()
                any_updated = False
                
                for u in usuarios:
                    # Aplicar únicamente a usuarios regulares de mesas (con mesa definida)
                    # y omitir usuarios administrativos o staff si aplica
                    if u.get("id") and u.get("mesa_id"):
                        old_credits = u.get("song_credits", 0)
                        old_puntos = u.get("puntos", 0)
                        
                        new_credits = max(0, old_credits - decay_rate)
                        new_puntos = max(0, old_puntos - decay_rate)
                        
                        if new_credits != old_credits or new_puntos != old_puntos:
                            cache_manager.update_usuario_en_cache(u["id"], {
                                "song_credits": new_credits,
                                "puntos": new_puntos
                            })
                            any_updated = True
                
                # Si algún usuario se actualizó, notificar a los clientes conectados para que refresquen
                if any_updated:
                    await websocket_manager.broadcast_points_decay()
            
            logger.debug(f"Credits decay worker executed at {now_bogota()}")
            
        except Exception as e:
            logger.error(f"Error in credits_decay_worker: {e}", exc_info=True)
        
        # Esperar 60 segundos antes de la próxima ejecución
        await asyncio.sleep(60)

def start_credits_background_task():
    """
    Inicia la tarea de background para decrementar créditos.
    Debe ser llamado en el startup de la aplicación.
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    task = loop.create_task(credits_decay_worker())
    logger.info("Credits background task started")
    return task
