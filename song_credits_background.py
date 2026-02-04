"""
Servicio de background para decrementar créditos de canciones.
Los créditos decaen 100 puntos cada minuto hasta llegar a 0.
"""

import asyncio
from database import SessionLocal
import models
from timezone_utils import now_bogota
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
            db = SessionLocal()
            try:
                # Obtener todos los créditos que no han sido consumidos
                credits = db.query(models.SongCredits).filter(
                    models.SongCredits.consumed_at.is_(None),
                    models.SongCredits.consumed_by_song_id.is_(None),
                    models.SongCredits.expires_at.is_(None)
                ).all()
                
                current_time = now_bogota()
                
                for credit in credits:
                    # Calcular minutos transcurridos
                    minutes_elapsed = (current_time - credit.created_at).total_seconds() / 60
                    
                    # Calcular valor restante
                    remaining_value = max(0, credit.credits_value - int(minutes_elapsed * 100))
                    
                    # Si el crédito llegó a 0, marcar como expirado
                    if remaining_value == 0:
                        credit.expires_at = current_time
                        logger.info(f"Crédito {credit.id} expirado para usuario {credit.usuario_id}")
                
                db.commit()
                logger.debug(f"Credits decay worker executed at {current_time}")
                
            finally:
                db.close()
        
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
