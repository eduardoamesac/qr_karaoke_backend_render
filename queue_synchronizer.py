"""
Queue Synchronizer: Mecanismo determinístico de sincronización
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Regla de oro:
El frontend NUNCA debe asumir orden.
El backend SIEMPRE envía el estado COMPLETO y ACTUAL.

Cada operación es ATÓMICA:
1. Cambio en DB
2. Validación de integridad
3. Refresh completo del cache
4. Broadcast del estado DEFINITIVO
5. Log de auditoría (qué cambió y por qué)
"""

import logging
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
import models
from timezone_utils import now_bogota
from fastapi.encoders import jsonable_encoder
from cache_manager import cache_manager

logger = logging.getLogger(__name__)


class QueueSynchronizer:
    """
    Gestor centralizado de sincronización de cola.
    Asegura que todos los cambios sean atómicos y auditados.
    """

    @staticmethod
    def get_definitive_state(db: Session) -> Dict[str, Any]:
        """
        Calcula el estado DEFINITIVO de la cola en este MISMO instante.
        
        REGLA: Siempre desde BD, nunca desde cache.
        Válida integridad: now_playing no puede estar en upcoming.
        
        Formato contractual (INMUTABLE):
        {
            "timestamp": ISO8601,
            "revision": int (incrementa con cada cambio),
            "now_playing": {canción} | null,
            "upcoming": [{canción}, ...],  # Solo aprobadas, sin now_playing
            "lazy_queue": [{canción}, ...],# Pendientes_lazy
            "pending": [{canción}, ...],   # Pendientes sin aprobar
            "_integrity": {checks}           # Para auditoría
        }
        """
        from queue_manager import queue_manager

        # PASO 1: Forzar sincronización desde BD
        queue_manager.refresh_all(db)

        # PASO 2: Obtener estado base del cache (ya sincronizado)
        state = queue_manager.get_full_state(db)

        # PASO 3: Validaciones de integridad
        now_playing = state["now_playing"]
        upcoming = state["upcoming"]

        # Verificar que now_playing no esté en upcoming (now_playing es dict)
        if now_playing:
            upcoming_ids = [s.get("id") if isinstance(s, dict) else s.id for s in upcoming]
            now_playing_id = now_playing.get("id") if isinstance(now_playing, dict) else now_playing.id
            if now_playing_id in upcoming_ids:
                logger.error(
                    f"INTEGRITY ERROR: now_playing (ID {now_playing_id}) "
                    f"también está en upcoming. Corrigiendo..."
                )
                upcoming = [s for s in upcoming if (s.get("id") if isinstance(s, dict) else s.id) != now_playing_id]

        # PASO 4: Obtener versión (usa cache JSON en lugar de BD)
        revision = cache_manager.get_queue_revision()

        # PASO 5: Serializar con integridad
        payload = {
            "timestamp": now_bogota().isoformat(),
            "revision": revision,
            "now_playing": jsonable_encoder(now_playing),
            "upcoming": [jsonable_encoder(s) for s in upcoming],
            "lazy_queue": [jsonable_encoder(s) for s in state["lazy_queue"]],
            "pending": [jsonable_encoder(s) for s in state["pending"]],
            "_integrity_checks": {
                "now_playing_not_in_upcoming": (
                    now_playing is None or 
                    (now_playing.get("id") if isinstance(now_playing, dict) else now_playing.id) 
                    not in [s.get("id") if isinstance(s, dict) else s.id for s in upcoming]
                ),
                "all_upcoming_states_approved": all(
                    (s.get("estado") if isinstance(s, dict) else s.estado) == "aprobado" for s in upcoming
                ),
                "all_lazy_states_pending_lazy": all(
                    (s.get("estado") if isinstance(s, dict) else s.estado) == "pendiente_lazy" for s in state["lazy_queue"]
                ),
            }
        }

        return payload

    @staticmethod
    def increment_revision(db: Session) -> int:
        """Incrementa el número de revisión para invalidar cache del frontend."""
        # Usar cache JSON en lugar de BD
        new_revision = cache_manager.increment_queue_revision()
        return new_revision

    @staticmethod
    def validate_song_still_valid(db: Session, cancion_id: int, expected_state: str) -> bool:
        """
        Valida que una canción existe y está en el estado esperado.
        Previene operaciones sobre canciones que cambiaron de estado.
        Ahora usa cache en lugar de BD.
        """
        all_songs = cache_manager.get_all_songs()
        cancion = next((s for s in all_songs if s.get("id") == cancion_id), None)

        if not cancion:
            logger.warning(f"Song ID {cancion_id} no existe en cache")
            return False

        actual_state = cancion.get("estado")
        if actual_state != expected_state:
            logger.warning(
                f"Song ID {cancion_id} estado cambió de {expected_state} a {actual_state}"
            )
            return False

        return True

    @staticmethod
    def reorder_lazy_queue_safely(
        db: Session,
        cancion_id: int,
        direction: str,  # "up" o "down"
        audit_user: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Reordena canción lazy de forma SEGURA.
        Ahora usa cache en lugar de BD.
        
        SEGURIDADES:
        1. Valida que canción esté en estado pendiente_lazy
        2. Valida que no esté reproduciendo
        3. Recalcula TODA la cola para garantizar integridad
        4. Valida que no_playing sigue siendo válido
        5. Incrementa versión
        6. Retorna estado definitivo
        """
        logger.info(
            f"REORDER_LAZY_SAFE: Song {cancion_id} move-{direction} by {audit_user}"
        )

        # PASO 1: Validar que canción existe y está en estado correcto
        all_songs = cache_manager.get_all_songs()
        cancion = next((s for s in all_songs if s.get("id") == cancion_id), None)

        if not cancion:
            return {
                "success": False,
                "error": "Canción no encontrada",
                "cancion_id": cancion_id
            }

        estado = cancion.get("estado")
        if estado == "reproduciendo":
            return {
                "success": False,
                "error": "No se puede reordenar: canción está reproduciendo",
                "cancion_id": cancion_id
            }

        if estado != "pendiente_lazy":
            return {
                "success": False,
                "error": f"Canción no está en lazy (está en {estado})",
                "cancion_id": cancion_id
            }

        # PASO 2: Obtener cola ACTUAL
        from crud import get_cola_lazy
        cola_actual = get_cola_lazy(db)
        # Convertir a dicts si son objetos ORM, extraer IDs
        cola_dicts = [
            s if isinstance(s, dict) else {
                "id": s.id,
                "titulo": getattr(s, "titulo", ""),
                "estado": getattr(s, "estado", "")
            }
            for s in cola_actual
        ]
        cola_ids = [s.get("id") for s in cola_dicts]

        # Encontrar índice
        try:
            current_idx = cola_ids.index(cancion_id)
        except ValueError:
            return {
                "success": False,
                "error": "Canción no está en cola lazy (inconsistencia detectada)",
                "cancion_id": cancion_id
            }

        # PASO 3: Calcular nuevo índice
        new_idx = current_idx
        if direction == "up" and current_idx > 0:
            new_idx = current_idx - 1
        elif direction == "down" and current_idx < len(cola_actual) - 1:
            new_idx = current_idx + 1
        else:
            return {
                "success": False,
                "error": "Canción ya está en el límite",
                "cancion_id": cancion_id
            }

        # PASO 4: Reordenar en cache
        cola_reordenada = cola_dicts.copy()
        cola_reordenada[current_idx], cola_reordenada[new_idx] = (
            cola_reordenada[new_idx],
            cola_reordenada[current_idx]
        )

        # Actualizar orden en cache
        for idx, song_dict in enumerate(cola_reordenada):
            song_id = song_dict.get("id")
            # Actualizar en cache
            cache_manager.update_song(song_id, {"orden_manual": idx + 1000})

        # PASO 5: Incrementar versión
        new_revision = QueueSynchronizer.increment_revision(db)

        # PASO 6: Calcular y retornar estado definitivo
        state = QueueSynchronizer.get_definitive_state(db)
        state["action"] = f"reorder_lazy_{direction}"
        state["audit_user"] = audit_user
        state["new_revision"] = new_revision

        logger.info(
            f"REORDER_LAZY_SUCCESS: Song {cancion_id} moved {direction}. "
            f"Revision: {new_revision}"
        )

        return {
            "success": True,
            "queue_state": state
        }

    @staticmethod
    def validate_and_respond_to_state_request(db: Session) -> Dict[str, Any]:
        """
        Endpoint '/queue/state' - Respuesta DEFINITIVA y confiable.
        
        Frontend debe:
        1. Guardar revision
        2. Guardar timestamp
        3. Si llama de nuevo y revision es igual, puede usar cache LOCAL
        4. Si revision cambió, RENDERIZAR NUEVO
        """
        return QueueSynchronizer.get_definitive_state(db)

    @staticmethod
    def detect_desynchronization(db: Session) -> Dict[str, Any]:
        """
        Detecta y reporta problemas de sincronización.
        Ahora usa cache en lugar de BD.
        Útil para debugging.
        """
        all_songs = cache_manager.get_all_songs()

        now_playing = next((s for s in all_songs if s.get("estado") == "reproduciendo"), None)
        upcoming = [s for s in all_songs if s.get("estado") == "aprobado"]
        lazy = [s for s in all_songs if s.get("estado") == "pendiente_lazy"]
        pending = [s for s in all_songs if s.get("estado") == "pendiente"]

        issues = []

        # Chequeo 1: now_playing no debería estar en upcoming
        if now_playing:
            now_playing_id = now_playing.get("id")
            upcoming_ids = [s.get("id") for s in upcoming]
            if now_playing_id in upcoming_ids:
                issues.append(
                    f"CRITICAL: now_playing (ID {now_playing_id}) "
                    f"también está en upcoming. State corrupted."
                )

        # Chequeo 2: Validar que no haya duplicados
        all_ids = (
            ([now_playing.get("id")] if now_playing else [])
            + [s.get("id") for s in upcoming]
            + [s.get("id") for s in lazy]
            + [s.get("id") for s in pending]
        )
        if len(all_ids) != len(set(all_ids)):
            issues.append("WARNING: Duplicate canciones detected in queue states")

        # Chequeo 3: Validar que canciones reproduciendo tengan timestamps
        if now_playing:
            started_at = now_playing.get("started_at")
            finished_at = now_playing.get("finished_at")
            if not started_at or finished_at is not None:
                issues.append(
                    f"WARNING: now_playing (ID {now_playing.get('id')}) tiene timestamps inválidos"
                )

        return {
            "clean": len(issues) == 0,
            "issues": issues,
            "now_playing_id": now_playing.get("id") if now_playing else None,
            "upcoming_count": len(upcoming),
            "lazy_count": len(lazy),
            "pending_count": len(pending),
        }
