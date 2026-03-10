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
    1. Verificar créditos que han llegado a 0
    2. Marcar como expirados los que no tienen valor
    """
    while True:
        try:
            # Obtener todos los créditos del cache
            # Los créditos se almacenan en el cache por usuario
            # Ahora solo hacemos logging - el sistema de créditos es manejado por cache_manager
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
