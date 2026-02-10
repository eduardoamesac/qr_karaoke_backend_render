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

    def refresh_queue(self, db: Session):
        """
        Alias de refresh_all para compatibilidad con código existente.
        Sincroniza todas las estructuras desde la base de datos.
        """
        self.refresh_all(db)
        return self._approved_queue

    def refresh_all(self, db: Session):
        """Sincroniza todas las estructuras desde la base de datos."""
        # 1. Now Playing
        self._now_playing = db.query(models.Cancion)\
            .options(joinedload(models.Cancion.usuario).joinedload(models.Usuario.mesa))\
            .filter(models.Cancion.estado == "reproduciendo")\
            .first()
        if self._now_playing: db.expunge(self._now_playing)

        # 2. Approved Queue (Fair Queue Logic)
        self._approved_queue = self._get_cola_justa_db(db, "aprobado")
        for s in self._approved_queue: db.expunge(s)

        # 3. Lazy Queue
        self._lazy_queue = self._get_cola_justa_db(db, "pendiente_lazy")
        for s in self._lazy_queue: db.expunge(s)

        # 4. Pending Queue
        self._pending_queue = db.query(models.Cancion)\
            .options(joinedload(models.Cancion.usuario).joinedload(models.Usuario.mesa))\
            .filter(models.Cancion.estado == 'pendiente')\
            .order_by(models.Cancion.created_at.asc())\
            .all()
        for s in self._pending_queue: db.expunge(s)

        # Reset user songs cache (se recargará bajo demanda)
        self._user_songs = {}
        
        logger.info("Cache unificado refrescado exitosamente.")

    def _get_cola_justa_db(self, db: Session, estado: str) -> List[models.Cancion]:
        """
        Calcula la cola justa directamente desde la DB.
        Cargamos con joinedload para evitar DetachedInstanceError.
        """
        from collections import deque
        
        # Obtener todas las canciones en el estado solicitado
        todas_canciones = (
            db.query(models.Cancion)
            .options(joinedload(models.Cancion.usuario).joinedload(models.Usuario.mesa))
            .filter(models.Cancion.estado == estado)
            .order_by(
                case((models.Cancion.orden_manual.is_(None), 1), else_=0),
                models.Cancion.orden_manual.asc(),
                models.Cancion.id.asc()
            )
            .all()
        )
        
        if not todas_canciones:
            return []
            
        cola_manual = []
        cola_pool = []
        
        for cancion in todas_canciones:
            if cancion.orden_manual is not None:
                cola_manual.append(cancion)
            else:
                cola_pool.append(cancion)
        
        if not cola_pool:
            return cola_manual
            
        # Agrupar por mesa
        match_mesa_canciones = {}
        mesa_arrival_time = {}
        mesas_involucradas_ids = set()
        
        for cancion in cola_pool:
            mesa_id = cancion.usuario.mesa_id or 0
            if mesa_id not in match_mesa_canciones:
                match_mesa_canciones[mesa_id] = deque()
                mesa_arrival_time[mesa_id] = cancion.id
                mesas_involucradas_ids.add(mesa_id)
            match_mesa_canciones[mesa_id].append(cancion)
            
        # Calcular quotas
        UMBRAL_ORO = 150000
        UMBRAL_PLATA = 50000
        mesa_quotas = {}
        
        if mesas_involucradas_ids:
            ids_reales = [mid for mid in mesas_involucradas_ids if mid != 0]
            consumos_mesas = {}
            
            if ids_reales:
                rows = (
                    db.query(
                        models.Usuario.mesa_id,
                        func.sum(models.Consumo.valor_total)
                    )
                    .join(models.Consumo, models.Usuario.id == models.Consumo.usuario_id)
                    .filter(models.Usuario.mesa_id.in_(ids_reales))
                    .group_by(models.Usuario.mesa_id)
                    .all()
                )
                for mid, total in rows:
                    consumos_mesas[mid] = total or 0
            
            for mid in mesas_involucradas_ids:
                total = consumos_mesas.get(mid, 0)
                if mid == 0: quota = 3
                elif total >= UMBRAL_ORO: quota = 3
                elif total >= UMBRAL_PLATA: quota = 2
                else: quota = 1
                mesa_quotas[mid] = quota
                
        cola_justa = []
        orden_turnos_mesas = sorted(mesas_involucradas_ids, key=lambda mid: mesa_arrival_time[mid])
        
        while match_mesa_canciones:
            for mesa_id in orden_turnos_mesas:
                if mesa_id not in match_mesa_canciones:
                    continue
                queue_de_mesa = match_mesa_canciones[mesa_id]
                cupo = mesa_quotas.get(mesa_id, 1)
                tomadas = 0
                while tomadas < cupo and queue_de_mesa:
                    cancion = queue_de_mesa.popleft()
                    cola_justa.append(cancion)
                    tomadas += 1
                if not queue_de_mesa:
                    del match_mesa_canciones[mesa_id]
                    
        return cola_manual + cola_justa

    def get_queue(self, db: Session) -> List[models.Cancion]:
        """Retorna la cola de aprobadas (para crud.get_cola_priorizada)."""
        # Si la cola está vacía, refrescar. 
        # En producción podrías cachear por N segundos, pero aquí priorizamos precisión.
        if not self._approved_queue:
            self.refresh_queue(db)
        return [self._reattach(db, s) for s in self._approved_queue]

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
