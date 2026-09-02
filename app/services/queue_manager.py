"""
QueueManager - Gestor de colas usando CACHE JSON
Sincroniza el estado de canciones desde el cache centralizado
"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.timezone_utils import now_bogota
from app.utils.cache_manager import cache_manager as cache

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
        def get_sort_key(s):
            try:
                val = s.get("orden_manual")
                # None o corruptos van al final (999999)
                order = int(val) if val is not None else 999999
            except (ValueError, TypeError):
                order = 999999
            return (order, str(s.get("created_at", "")))

        self._now_playing_list = cache.get_songs_by_estado("reproduciendo")
        self._now_playing = self._now_playing_list[0] if self._now_playing_list else None
        
        self._approved_queue = cache.get_songs_by_estado("aprobado") or []
        self._approved_queue.sort(key=get_sort_key)

        self._lazy_queue = cache.get_songs_by_estado("pendiente_lazy") or []
        self._lazy_queue.sort(key=get_sort_key)

        self._pending_queue = cache.get_songs_by_estado("pendiente") or []
        self._pending_queue.sort(key=lambda s: s.get("created_at", ""))
        
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
            songs = cache.get_songs_by_user(usuario_id) or []
            # Ordenar por orden_manual y luego por fecha de creación
            songs.sort(key=lambda s: (s.get("orden_manual", 0) or 0, s.get("created_at", "")))
            self._user_songs[usuario_id] = songs
        return self._user_songs[usuario_id]

    def pop_next_song(self, db: Session, local_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Transición de estado: Siguiente en Approved -> Reproduciendo para un local_id específico.
        Si no hay aprobadas, intenta promover una de la cola lazy de ese local automáticamente.
        """
        self.refresh_all(db)
        
        approved_for_local = [
            s for s in self._approved_queue 
            if local_id is None or s.get("local_id") == local_id or s.get("local_id") is None
        ]
        lazy_for_local = [
            s for s in self._lazy_queue 
            if local_id is None or s.get("local_id") == local_id or s.get("local_id") is None
        ]

        # 1. Si no hay aprobadas, intentar promover la primera de la cola lazy del local
        if not approved_for_local and lazy_for_local:
            first_lazy = lazy_for_local[0]
            logger.info(f"🚀 No hay canciones aprobadas para local {local_id}. Promoviendo '{first_lazy.get('titulo')}' desde cola lazy.")
            
            # Promover a aprobado
            cache.update_song(first_lazy["id"], {"estado": "aprobado"})
            
            # Refrescar para que aparezca en _approved_queue
            self.refresh_all(db)
            approved_for_local = [
                s for s in self._approved_queue 
                if local_id is None or s.get("local_id") == local_id or s.get("local_id") is None
            ]

        # 2. Proceder con el pop normal si hay algo en la cola aprobada para este local
        if not approved_for_local:
            return None
        
        next_song = approved_for_local[0]
        
        if next_song:
            # Actualizar estado en cache
            next_song["estado"] = "reproduciendo"
            next_song["started_at"] = now_bogota().isoformat()
            cache.update_song(next_song["id"], next_song)
            
            # Refrescar estado global
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
