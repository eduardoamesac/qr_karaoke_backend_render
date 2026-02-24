"""
QueueManager - Gestor de colas usando CACHE JSON
Sincroniza el estado de canciones desde el cache centralizado
"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from timezone_utils import now_bogota
from cache_manager import cache_manager as cache

logger = logging.getLogger(__name__)

class QueueManager:
    """
    Singleton que gestiona el estado global de colas.
    Ahora usa CACHE JSON en lugar de BD para canciones.
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
            
        self._now_playing: Optional[Dict[str, Any]] = None
        self._approved_queue: List[Dict[str, Any]] = []
        self._lazy_queue: List[Dict[str, Any]] = []
        self._pending_queue: List[Dict[str, Any]] = []
        self._user_songs: Dict[int, List[Dict[str, Any]]] = {}
        
        self._initialized = True
        logger.info("QueueManager inicializado usando CACHE JSON")

    def refresh_queue(self, db: Session):
        """Retorna la cola de aprobadas."""
        self.refresh_all(db)
        return self._approved_queue

    def refresh_all(self, db: Session):
        """Sincroniza desde el CACHE JSON."""
        # Obtener canciones por estado del cache
        self._now_playing_list = cache.get_songs_by_estado("reproduciendo")
        self._now_playing = self._now_playing_list[0] if self._now_playing_list else None
        
        self._approved_queue = cache.get_songs_by_estado("aprobado") or []
        self._lazy_queue = cache.get_songs_by_estado("pendiente_lazy") or []
        self._pending_queue = cache.get_songs_by_estado("pendiente") or []
        
        self._user_songs = {}
        logger.info("Cache refrescado desde JSON")

    def _get_cola_justa_db(self, db: Session, estado: str) -> List[Dict[str, Any]]:
        """Obtiene cola justa desde caché."""
        return cache.get_songs_by_estado(estado) or []

    def get_queue(self, db: Session) -> List[Dict[str, Any]]:
        """Retorna la cola de aprobadas."""
        if not self._approved_queue:
            self.refresh_queue(db)
        return self._approved_queue

    def get_full_state(self, db: Session) -> Dict[str, Any]:
        """Estado para Dashboard de Admin."""
        self.refresh_all(db)
        return {
            "now_playing": self._now_playing,
            "upcoming": self._approved_queue[:1] if self._approved_queue else [],
            "lazy_queue": self._lazy_queue,
            "pending": self._pending_queue
        }

    def get_user_songs(self, db: Session, usuario_id: int) -> List[Dict[str, Any]]:
        """Obtiene canciones de un usuario."""
        if usuario_id not in self._user_songs:
            self._user_songs[usuario_id] = cache.get_songs_by_user(usuario_id) or []
        return self._user_songs[usuario_id]

    def pop_next_song(self, db: Session) -> Optional[Dict[str, Any]]:
        """Transición de estado: Siguiente en Approved -> Reproduciendo."""
        self.refresh_all(db)
        
        if not self._approved_queue:
            return None
        
        next_song = self._approved_queue[0]
        
        if next_song:
            # Actualizar estado en cache
            next_song["estado"] = "reproduciendo"
            next_song["started_at"] = now_bogota().isoformat()
            cache.update_song(next_song["id"], next_song)
            
            # Refrescar estado
            self.refresh_all(db)
            return next_song
        
        return None

    def invalidate_user_cache(self, usuario_id: Optional[int] = None):
        """Limpia el cache de usuarios."""
        if usuario_id:
            if usuario_id in self._user_songs:
                del self._user_songs[usuario_id]
        else:
            self._user_songs = {}

# Instancia global
queue_manager = QueueManager()
