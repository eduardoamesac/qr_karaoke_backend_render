import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, case
import models
import schemas
from database import SessionLocal
from timezone_utils import now_bogota
import json
from fastapi.encoders import jsonable_encoder

logger = logging.getLogger(__name__)

class QueueManager:
    """
    Singleton que gestiona el estado global de todas las colas de canciones.
    Actúa como una base de datos en memoria sincronizada con la DB real.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(QueueManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        # Almacenamos los objetos detached
        self._now_playing: Optional[models.Cancion] = None
        self._approved_queue: List[models.Cancion] = []
        self._lazy_queue: List[models.Cancion] = []
        self._pending_queue: List[models.Cancion] = []
        
        # Cache de canciones por usuario (para "Mis canciones")
        self._user_songs: Dict[int, List[models.Cancion]] = {}
        
        self._initialized = True
        logger.info("QueueManager Unified Cache (Full) inicializado.")

    def _reattach(self, db: Session, song: Optional[models.Cancion]) -> Optional[models.Cancion]:
        if not song: return None
        return db.merge(song, load=False)

    def refresh_all(self, db: Session):
        """Sincroniza todas las estructuras desde la base de datos."""
        # 1. Now Playing
        self._now_playing = db.query(models.Cancion)\
            .options(joinedload(models.Cancion.usuario).joinedload(models.Usuario.mesa))\
            .filter(models.Cancion.estado == "reproduciendo")\
            .first()
        if self._now_playing: db.expunge(self._now_playing)

        # 2. Approved Queue
        from crud import get_cola_priorizada
        self._approved_queue = get_cola_priorizada(db)
        for s in self._approved_queue: db.expunge(s)

        # 3. Lazy Queue
        from crud import get_cola_lazy
        self._lazy_queue = get_cola_lazy(db)
        for s in self._lazy_queue: db.expunge(s)

        # 4. Pending Queue
        from crud import get_canciones_pendientes_por_aprobar
        self._pending_queue = get_canciones_pendientes_por_aprobar(db)
        for s in self._pending_queue: db.expunge(s)

        # Reset user songs cache (se recargará bajo demanda)
        self._user_songs = {}
        
        logger.info("Cache unificado refrescado exitosamente.")

    def get_full_state(self, db: Session) -> Dict[str, Any]:
        """Estado para el Dashboard de Admin."""
        # Siempre refrescamos para asegurar que el admin vea la realidad
        self.refresh_all(db)
        return {
            "now_playing": self._reattach(db, self._now_playing),
            "upcoming": [self._reattach(db, s) for s in self._approved_queue[:1]],
            "lazy_queue": [self._reattach(db, s) for s in self._lazy_queue],
            "pending": [self._reattach(db, s) for s in self._pending_queue]
        }

    def get_user_songs(self, db: Session, usuario_id: int) -> List[models.Cancion]:
        """Estado para 'Mis canciones' del usuario."""
        # Si no está en cache, cargar de DB
        if usuario_id not in self._user_songs:
            from crud import get_canciones_por_usuario
            songs = get_canciones_por_usuario(db, usuario_id)
            for s in songs: db.expunge(s)
            self._user_songs[usuario_id] = songs
            
        return [self._reattach(db, s) for s in self._user_songs[usuario_id]]

    def pop_next_song(self, db: Session) -> Optional[models.Cancion]:
        """
        Transición de estado: Siguiente en Approved -> Reproduciendo.
        Marca la anterior como 'cantada'.
        """
        # Asegurar que tenemos la cola fresca
        self.refresh_all(db)
        
        if not self._approved_queue:
            return None
            
        next_song_detached = self._approved_queue[0]
        next_song = db.query(models.Cancion).filter(models.Cancion.id == next_song_detached.id).first()
        
        if next_song:
            # 1. Finalizar actual
            actual = db.query(models.Cancion).filter(models.Cancion.estado == "reproduciendo").first()
            if actual:
                actual.estado = "cantada"
                actual.finished_at = now_bogota()
            
            # 2. Iniciar nueva
            next_song.estado = "reproduciendo"
            next_song.started_at = now_bogota()
            next_song.orden_manual = None
            
            db.commit()
            db.refresh(next_song)
            
            # 3. Invalidar caches
            self.refresh_all(db)
            return next_song
            
        return None

    def invalidate_user_cache(self, usuario_id: Optional[int] = None):
        """Limpia el cache de usuarios. Si no se pasa id, limpia todos."""
        if usuario_id:
            if usuario_id in self._user_songs:
                del self._user_songs[usuario_id]
        else:
            self._user_songs = {}

# Instancia global
queue_manager = QueueManager()
