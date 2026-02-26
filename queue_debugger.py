"""
Queue Debugger: Herramienta completa para diagnosticar problemas de sincronización.
Muestra EXACTAMENTE qué va a reproducir vs qué muestra la UI.
"""

import logging
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
import models
from timezone_utils import now_bogota
from fastapi.encoders import jsonable_encoder
import json

logger = logging.getLogger(__name__)


class QueueDebugger:
    """
    Diagnostica problemas de sincronización de cola.
    Compara UI vs realidad del backend.
    """

    @staticmethod
    def _get_enriched_songs(db: Session, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Helper para obtener canciones enriquecidas desde el cache."""
        import crud
        from cache_manager import cache_manager as cache
        
        all_songs = cache.get_all_songs()
        if status:
            filtered = [s for s in all_songs if s.get("estado") == status]
        else:
            filtered = all_songs
            
        return [crud.enriquecer_cancion(db, s) for s in filtered]

    @staticmethod
    def get_full_debug_report(db: Session) -> Dict[str, Any]:
        """
        Retorna un reporte COMPLETO de depuración desde el CACHE.
        """
        now = now_bogota()

        # ========== SECCIÓN 1-4: Obtener canciones desde CACHE ==========
        enriched_songs = QueueDebugger._get_enriched_songs(db)
        
        now_playing = next((s for s in enriched_songs if s.get("estado") == "reproduciendo"), None)
        
        all_approved = [s for s in enriched_songs if s.get("estado") == "aprobado"]
        all_approved.sort(key=lambda s: (s.get("orden_manual", 999999) or 999999, s.get("id", 0)))
        
        all_lazy = [s for s in enriched_songs if s.get("estado") == "pendiente_lazy"]
        all_lazy.sort(key=lambda s: (s.get("orden_manual", 999999) or 999999, s.get("id", 0)))
        
        all_pending = [s for s in enriched_songs if s.get("estado") == "pendiente"]
        all_pending.sort(key=lambda s: s.get("created_at", ""))

        # ========== SECCIÓN 5: Historial reciente ==========
        recent_logs = []

        # ========== SECCIÓN 6: Validaciones ==========
        issues = []

        # Chequeo 1: now_playing NO debería estar en approved
        if now_playing:
            if now_playing.get("id") in [s.get("id") for s in all_approved]:
                issues.append(
                    {
                        "severity": "CRITICAL",
                        "issue": "now_playing está TAMBIÉN en approved queue",
                        "cancion_id": now_playing.get("id"),
                        "titulo": now_playing.get("titulo")
                    }
                )

        # Chequeo 2: Validar orden_manual
        for i, song in enumerate(all_approved):
            if song.get("orden_manual") and song.get("orden_manual") != i + 1:
                issues.append(
                    {
                        "severity": "WARNING",
                        "issue": f"orden_manual inconsistente: {song.get('orden_manual')} pero posición es {i+1}",
                        "cancion_id": song.get("id"),
                        "titulo": song.get("titulo")
                    }
                )

        # Chequeo 3: Verificar que no haya duplicados
        all_ids = (
            ([now_playing.get("id")] if now_playing else [])
            + [s.get("id") for s in all_approved]
            + [s.get("id") for s in all_lazy]
            + [s.get("id") for s in all_pending]
        )
        if len(all_ids) != len(set(all_ids)):
            duplicate_ids = [id for id in set(all_ids) if all_ids.count(id) > 1]
            issues.append(
                {
                    "severity": "CRITICAL",
                    "issue": f"Duplicados detectados en estados",
                    "duplicate_ids": duplicate_ids
                }
            )

        # ========== RETORNAR REPORTE ==========
        return {
            "timestamp": now.isoformat(),
            "report_type": "FULL_QUEUE_DEBUG",

            "what_will_play": {
                "now_playing_id": now_playing.get("id") if now_playing else None,
                "now_playing_title": now_playing.get("titulo") if now_playing else None,
                "now_playing_user": now_playing.get("usuario", {}).get("nick") if now_playing else None,
                "now_playing_duration": now_playing.get("duracion_seconds") if now_playing else None,
                "now_playing_started_at": now_playing.get("started_at") if now_playing else None,
                "next_20_in_queue": [
                    {
                        "position": i + 1,
                        "id": song.get("id"),
                        "titulo": song.get("titulo"),
                        "usuario": song.get("usuario", {}).get("nick"),
                        "duracion": song.get("duracion_seconds"),
                        "orden_manual": song.get("orden_manual"),
                        "estado": song.get("estado"),
                        "created_at": song.get("created_at")
                    }
                    for i, song in enumerate(all_approved[:20])
                ]
            },

            "database_state": {
                "reproduciendo_count": 1 if now_playing else 0,
                "aprobado_count": len(all_approved),
                "aprobado_list": [
                    {
                        "id": s.get("id"),
                        "titulo": s.get("titulo"),
                        "usuario": s.get("usuario", {}).get("nick"),
                        "orden_manual": s.get("orden_manual"),
                        "created_at": s.get("created_at"),
                        "approved_at": s.get("approved_at")
                    }
                    for s in all_approved
                ],
                "pendiente_lazy_count": len(all_lazy),
                "pendiente_lazy_list": [
                    {
                        "id": s.get("id"),
                        "titulo": s.get("titulo"),
                        "usuario": s.get("usuario", {}).get("nick"),
                        "orden_manual": s.get("orden_manual"),
                        "created_at": s.get("created_at")
                    }
                    for s in all_lazy[:20]
                ],
                "pendiente_count": len(all_pending),
                "pendiente_list": [
                    {
                        "id": s.get("id"),
                        "titulo": s.get("titulo"),
                        "usuario": s.get("usuario", {}).get("nick"),
                        "created_at": s.get("created_at")
                    }
                    for s in all_pending[:10]
                ]
            },

            "integrity_checks": {
                "now_playing_not_in_approved": (
                    now_playing.get("id") not in [s.get("id") for s in all_approved]
                    if now_playing else True
                ),
                "no_duplicates": len(all_ids) == len(set(all_ids)),
                "all_approved_have_correct_status": all(
                    s.get("estado") == "aprobado" for s in all_approved
                ),
                "all_lazy_have_correct_status": all(
                    s.get("estado") == "pendiente_lazy" for s in all_lazy
                ),
                "issues_detected": len(issues) > 0
            },

            "issues": issues,

            "recent_queue_operations": []
        }

    @staticmethod
    def get_next_song_to_play(db: Session) -> Dict[str, Any]:
        """
        Retorna LA PRÓXIMA CANCIÓN que va a reproducir el player.
        """
        enriched_songs = QueueDebugger._get_enriched_songs(db)
        
        now_playing = next((s for s in enriched_songs if s.get("estado") == "reproduciendo"), None)
        
        all_approved = [s for s in enriched_songs if s.get("estado") == "aprobado"]
        all_approved.sort(key=lambda s: (s.get("orden_manual", 999999) or 999999, s.get("id", 0)))
        
        all_lazy = [s for s in enriched_songs if s.get("estado") == "pendiente_lazy"]
        all_lazy.sort(key=lambda s: (s.get("orden_manual", 999999) or 999999, s.get("id", 0)))

        if now_playing:
            next_song = all_approved[0] if all_approved else None

            return {
                "status": "something_is_playing",
                "now_playing": {
                    "id": now_playing.get("id"),
                    "titulo": now_playing.get("titulo"),
                    "usuario": now_playing.get("usuario", {}).get("nick"),
                    "started_at": now_playing.get("started_at"),
                    "duracion_seconds": now_playing.get("duracion_seconds"),
                    "progress_percent": QueueDebugger._calculate_progress(now_playing)
                },
                "next_after_current": {
                    "id": next_song.get("id"),
                    "titulo": next_song.get("titulo"),
                    "usuario": next_song.get("usuario", {}).get("nick"),
                    "orden_manual": next_song.get("orden_manual"),
                    "created_at": next_song.get("created_at")
                } if next_song else None
            }
        else:
            next_song = all_approved[0] if all_approved else None

            if next_song:
                return {
                    "status": "ready_to_play",
                    "nothing_playing": True,
                    "next_to_play": {
                        "id": next_song.get("id"),
                        "titulo": next_song.get("titulo"),
                        "usuario": next_song.get("usuario", {}).get("nick"),
                        "duracion_seconds": next_song.get("duracion_seconds"),
                        "urgency": "PLAY NOW"
                    }
                }
            else:
                lazy_song = all_lazy[0] if all_lazy else None

                if lazy_song:
                    return {
                        "status": "waiting_for_approval",
                        "no_approved": True,
                        "first_lazy_waiting": {
                            "id": lazy_song.get("id"),
                            "titulo": lazy_song.get("titulo"),
                            "usuario": lazy_song.get("usuario", {}).get("nick"),
                            "message": "DEBE SER APROBADA PRIMERO"
                        }
                    }
                else:
                    return {
                        "status": "empty",
                        "message": "NO HAY CANCIONES EN LA COLA"
                    }

    @staticmethod
    def _calculate_progress(song: Dict[str, Any]) -> int:
        """Calcula % de progreso de canción en reproducción."""
        started_at_str = song.get("started_at")
        duracion = song.get("duracion_seconds")
        
        if not started_at_str or not duracion:
            return 0

        try:
            from datetime import datetime
            now = now_bogota()
            started = datetime.fromisoformat(started_at_str)
            
            if started.tzinfo is None and now.tzinfo is not None:
                started = started.replace(tzinfo=now.tzinfo)
            
            elapsed = (now - started).total_seconds()
            progress = min(100, int((elapsed / duracion) * 100))
            return max(0, progress)
        except Exception:
            return 0

    @staticmethod
    def get_ui_vs_reality_comparison(db: Session, ui_queue_state: Dict) -> Dict[str, Any]:
        """
        Compara lo que la UI está mostrando vs la realidad en CACHE.
        """
        enriched_songs = QueueDebugger._get_enriched_songs(db)
        
        now_playing_real = next((s for s in enriched_songs if s.get("estado") == "reproduciendo"), None)
        
        approved_real = [s for s in enriched_songs if s.get("estado") == "aprobado"]
        approved_real.sort(key=lambda s: (s.get("orden_manual", 999999) or 999999, s.get("id", 0)))

        ui_now_playing_id = ui_queue_state.get("now_playing", {}).get("id") if ui_queue_state.get("now_playing") else None
        ui_upcoming_ids = [s.get("id") for s in ui_queue_state.get("upcoming", [])]

        reality_now_playing_id = now_playing_real.get("id") if now_playing_real else None
        reality_upcoming_ids = [s.get("id") for s in approved_real]

        discrepancies = []

        if ui_now_playing_id != reality_now_playing_id:
            discrepancies.append({
                "type": "now_playing_mismatch",
                "severity": "CRITICAL",
                "ui_shows": ui_now_playing_id,
                "reality_is": reality_now_playing_id,
                "message": "La canción que UI muestra como reproduciendo NO ES la real"
            })

        hidden_songs_ids = set(reality_upcoming_ids) - set(ui_upcoming_ids)
        if hidden_songs_ids:
            hidden_songs = [s for s in approved_real if s.get("id") in hidden_songs_ids]
            discrepancies.append({
                "type": "hidden_songs",
                "severity": "CRITICAL",
                "count": len(hidden_songs),
                "hidden_song_ids": list(hidden_songs_ids),
                "hidden_songs_details": [
                    {
                        "id": s.get("id"),
                        "titulo": s.get("titulo"),
                        "usuario": s.get("usuario", {}).get("nick")
                    }
                    for s in hidden_songs
                ],
                "message": f"{len(hidden_songs)} CANCIONES ESTÁN EN CACHE PERO NO MUESTRA LA UI"
            })

        phantom_songs_ids = set(ui_upcoming_ids) - set(reality_upcoming_ids)
        if phantom_songs_ids:
            discrepancies.append({
                "type": "phantom_songs",
                "severity": "WARNING",
                "count": len(phantom_songs_ids),
                "phantom_song_ids": list(phantom_songs_ids),
                "message": f"{len(phantom_songs_ids)} CANCIONES EN UI PERO NO EN CACHE"
            })

        if ui_upcoming_ids != reality_upcoming_ids and ui_upcoming_ids and reality_upcoming_ids:
            discrepancies.append({
                "type": "order_mismatch",
                "severity": "WARNING",
                "message": "El orden de la cola está diferente entre UI y CACHE"
            })

        return {
            "timestamp": now_bogota().isoformat(),
            "ui_state": {
                "now_playing_id": ui_now_playing_id,
                "upcoming_count": len(ui_upcoming_ids)
            },
            "reality_state": {
                "now_playing_id": reality_now_playing_id,
                "upcoming_count": len(reality_upcoming_ids)
            },
            "discrepancies": discrepancies,
            "summary": {
                "is_synchronized": len(discrepancies) == 0,
                "issues_found": len(discrepancies)
            }
        }

