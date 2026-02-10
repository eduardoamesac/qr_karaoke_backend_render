import logging
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from collections import deque
import models
import schemas
from database import SessionLocal

logger = logging.getLogger(__name__)

class QueueManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(QueueManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._queue: List[models.Cancion] = []
        self._current_song: Optional[models.Cancion] = None
        self._initialized = True
        logger.info("iniciando QueueManager singleton")

    def get_queue(self, db: Session) -> List[models.Cancion]:
        """
        Devuelve la cola actual. Si está vacía, intenta refrescarla desde la DB.
        Nota: Esto devuelve la lista en memoria, pero RE-ADJUNTA los objetos a la sesión actual
        para evitar DetachedInstanceError.
        """
        # Si la cola está vacía, forzamos un refresh por si acaso el servidor se reinició
        if not self._queue:
            self.refresh_queue(db)
            
        if not self._queue:
            return []

        # Re-attach objects to the current session
        # Strategy: Fetch by IDs to ensure freshness and attachment
        ids = [s.id for s in self._queue]
        
        # Fetch objects preserving order is tricky in SQL, so we fetch all and map
        # Optimization: Use joinedload if needed, but for now standard lazy load is safer than detached
        current_objects = db.query(models.Cancion).filter(models.Cancion.id.in_(ids)).all()
        object_map = {obj.id: obj for obj in current_objects}
        
        # Reconstruct list in original order
        attached_queue = []
        dirty = False
        for song_id in ids:
            if song_id in object_map:
                attached_queue.append(object_map[song_id])
            else:
                # Song was deleted from DB but is in cache?
                dirty = True
        
        if dirty:
            # If we found discrepancies, maybe we should refresh?
            # For now, let's just return what we found to avoid recursion or blocking
            pass
            
        return attached_queue

    def refresh_queue(self, db: Session) -> List[models.Cancion]:
        """
        Recalcula la cola completa basada en la lógica de 'Cola Justa' y actualiza el estado en memoria.
        """
        logger.info("Refrescando cola de canciones en QueueManager...")
        
        # 1. Obtener todas las canciones aprobadas
        # Ordenamos por ID ascendente para respetar el orden de llegada "natural" dentro de cada mesa
        todas_canciones = (
            db.query(models.Cancion)
            .join(models.Usuario, models.Cancion.usuario_id == models.Usuario.id)
            .filter(models.Cancion.estado == "aprobado")
            .order_by(
                case((models.Cancion.orden_manual.is_(None), 1), else_=0),
                models.Cancion.orden_manual.asc(),
                models.Cancion.id.asc()
            )
            .all()
        )

        # 2. Separar canciones con orden manual (Prioridad Absoluta)
        cola_manual = []
        cola_pool = []
        
        for cancion in todas_canciones:
            if cancion.orden_manual is not None:
                cola_manual.append(cancion)
            else:
                cola_pool.append(cancion)
                
        # Si solo hay canciones manuales, esa es nuestra cola
        if not cola_pool:
            self._queue = cola_manual
            return self.get_queue(db) # Return attached via get_queue logic

        # 3. Agrupar canciones por Mesa
        match_mesa_canciones = {} # {mesa_id: deque([canciones])}
        mesa_arrival_time = {} # {mesa_id: primer_id_cancion} para ordenar turnos
        
        mesas_involucradas_ids = set()

        for cancion in cola_pool:
            mesa_id = cancion.usuario.mesa_id
            if not mesa_id:
                # Si no tiene mesa (ej. DJ), ID 0
                mesa_id = 0
                
            if mesa_id not in match_mesa_canciones:
                match_mesa_canciones[mesa_id] = deque()
                mesa_arrival_time[mesa_id] = cancion.id # El ID más bajo es el primero que llegó
                mesas_involucradas_ids.add(mesa_id)
                
            match_mesa_canciones[mesa_id].append(cancion)

        # 4. Calcular Categoría (Tier) de cada Mesa y sus Cuotas
        UMBRAL_ORO = 150000
        UMBRAL_PLATA = 50000
        
        mesa_quotas = {} # {mesa_id: int}
        
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
                
                # DJ / Sin Mesa (ID 0) recibe trato Preferencial (Oro)
                if mid == 0: 
                    quota = 3 
                elif total >= UMBRAL_ORO:
                    quota = 3
                elif total >= UMBRAL_PLATA:
                    quota = 2
                else:
                    quota = 1
                    
                mesa_quotas[mid] = quota

        # 5. Construir la Cola Round-Robin
        cola_fair = []
        
        # Ordenamos las mesas por orden de llegada (quién puso canción primero)
        orden_turnos_mesas = sorted(mesas_involucradas_ids, key=lambda mid: mesa_arrival_time[mid])
        
        # Bucle Round Robin
        while match_mesa_canciones:
            # Iterar sobre una copia de la lista de mesas para mantener el orden de turnos
            # Si una mesa se queda sin canciones, la sacamos del diccionario match_mesa_canciones
            
            for mesa_id in orden_turnos_mesas:
                if mesa_id not in match_mesa_canciones:
                    continue
                    
                quota = mesa_quotas.get(mesa_id, 1)
                canciones_mesa = match_mesa_canciones[mesa_id]
                
                # Tomar hasta 'quota' canciones de esta mesa
                tomadas = 0
                while tomadas < quota and canciones_mesa:
                    cola_fair.append(canciones_mesa.popleft())
                    tomadas += 1
                
                # Si se acabaron las canciones de esta mesa, borrarla del diccionario
                if not canciones_mesa:
                    del match_mesa_canciones[mesa_id]

        # Combinar: Manual (prioridad) + Fair
        self._queue = cola_manual + cola_fair
        
        logger.info(f"Cola refrescada. Total: {len(self._queue)} canciones.")
        
        # Instead of returning self._queue (detached), use get_queue to return attached
        return self.get_queue(db)

    def get_next_song(self, db: Session) -> Optional[models.Cancion]:
        """Retorna la siguiente canción sin sacarla de la cola."""
        if not self._queue:
            self.refresh_queue(db)
        
        if self._queue:
            first_id = self._queue[0].id
            return db.query(models.Cancion).filter(models.Cancion.id == first_id).first()
        return None

    def pop_next_song(self, db: Session) -> Optional[models.Cancion]:
        """
        Saca la siguiente canción de la cola y actualiza el estado en DB y memoria.
        """
        # Asegurarnos de tener la cola actualizada
        if not self._queue:
            self.refresh_queue(db)
            
        if not self._queue:
            return None
            
        next_song_detached = self._queue.pop(0) # Sacar de la memoria
        
        # Si tenía orden manual, limpiarlo al reproducir
        # Need to fetch attached object to modify it
        next_song = db.query(models.Cancion).filter(models.Cancion.id == next_song_detached.id).first()
        if next_song:
            if next_song.orden_manual is not None:
                next_song.orden_manual = None
                db.commit()
                db.refresh(next_song)
            return next_song
            
        return None

# Instancia global
queue_manager = QueueManager()
