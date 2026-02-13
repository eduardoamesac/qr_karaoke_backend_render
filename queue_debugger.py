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
    def get_full_debug_report(db: Session) -> Dict[str, Any]:
        """
        Retorna un reporte COMPLETO de depuración que muestra:
        - Canción reproduciendo EN REALIDAD
        - Próximas 20 canciones en orden REAL
        - Canciones en BD por estado
        - Discrepancias detectadas
        - Historial reciente de cambios
        """
        from queue_synchronizer import QueueSynchronizer

        now = now_bogota()

        # ========== SECCIÓN 1: Estado actual ==========
        now_playing = db.query(models.Cancion).filter(
            models.Cancion.estado == "reproduciendo"
        ).first()

        # ========== SECCIÓN 2: Cola aprobada EXACTA ==========
        all_approved = db.query(models.Cancion).filter(
            models.Cancion.estado == "aprobado"
        ).order_by(
            # Orden manual primero, luego por id
            models.Cancion.orden_manual.asc(),
            models.Cancion.id.asc()
        ).all()

        # ========== SECCIÓN 3: Cola lazy EXACTA ==========
        all_lazy = db.query(models.Cancion).filter(
            models.Cancion.estado == "pendiente_lazy"
        ).order_by(
            models.Cancion.orden_manual.asc() if False else models.Cancion.id.asc()
        ).all()

        # ========== SECCIÓN 4: Pending EXACTA ==========
        all_pending = db.query(models.Cancion).filter(
            models.Cancion.estado == "pendiente"
        ).order_by(models.Cancion.created_at.asc()).all()

        # ========== SECCIÓN 5: Historial reciente ==========
        recent_logs = db.query(models.AdminLog).order_by(
            models.AdminLog.timestamp.desc()
        ).limit(20).all()

        # ========== SECCIÓN 6: Validaciones ==========
        issues = []

        # Chequeo 1: now_playing NO debería estar en approved
        if now_playing:
            if now_playing.id in [s.id for s in all_approved]:
                issues.append(
                    {
                        "severity": "CRITICAL",
                        "issue": "now_playing está TAMBIÉN en approved queue",
                        "cancion_id": now_playing.id,
                        "titulo": now_playing.titulo
                    }
                )

        # Chequeo 2: Validar orden_manual
        for i, song in enumerate(all_approved):
            if song.orden_manual and song.orden_manual != i + 1:
                # Advertencia si orden_manual es inconsistente
                issues.append(
                    {
                        "severity": "WARNING",
                        "issue": f"orden_manual inconsistente: {song.orden_manual} pero posición es {i+1}",
                        "cancion_id": song.id,
                        "titulo": song.titulo
                    }
                )

        # Chequeo 3: Verificar que no haya duplicados
        all_ids = (
            ([now_playing.id] if now_playing else [])
            + [s.id for s in all_approved]
            + [s.id for s in all_lazy]
            + [s.id for s in all_pending]
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

            # SECCIÓN: QUÉ VA A REPRODUCIR REALMENTE
            "what_will_play": {
                "now_playing_id": now_playing.id if now_playing else None,
                "now_playing_title": now_playing.titulo if now_playing else None,
                "now_playing_user": (
                    now_playing.usuario.nick if now_playing and now_playing.usuario else None
                ),
                "now_playing_duration": now_playing.duracion_seconds if now_playing else None,
                "now_playing_started_at": (
                    now_playing.started_at.isoformat() if now_playing and now_playing.started_at else None
                ),
                "next_20_in_queue": [
                    {
                        "position": i + 1,
                        "id": song.id,
                        "titulo": song.titulo,
                        "usuario": song.usuario.nick if song.usuario else None,
                        "duracion": song.duracion_seconds,
                        "orden_manual": song.orden_manual,
                        "estado": song.estado,
                        "created_at": song.created_at.isoformat()
                    }
                    for i, song in enumerate(all_approved[:20])
                ]
            },

            # SECCIÓN: ESTADO DETALLADO DE LA BD
            "database_state": {
                "reproduciendo_count": 1 if now_playing else 0,
                "aprobado_count": len(all_approved),
                "aprobado_list": [
                    {
                        "id": s.id,
                        "titulo": s.titulo,
                        "usuario": s.usuario.nick if s.usuario else None,
                        "orden_manual": s.orden_manual,
                        "created_at": s.created_at.isoformat(),
                        "approved_at": s.approved_at.isoformat() if s.approved_at else None
                    }
                    for s in all_approved
                ],
                "pendiente_lazy_count": len(all_lazy),
                "pendiente_lazy_list": [
                    {
                        "id": s.id,
                        "titulo": s.titulo,
                        "usuario": s.usuario.nick if s.usuario else None,
                        "orden_manual": s.orden_manual,
                        "created_at": s.created_at.isoformat()
                    }
                    for s in all_lazy[:20]
                ],
                "pendiente_count": len(all_pending),
                "pendiente_list": [
                    {
                        "id": s.id,
                        "titulo": s.titulo,
                        "usuario": s.usuario.nick if s.usuario else None,
                        "created_at": s.created_at.isoformat()
                    }
                    for s in all_pending[:10]
                ]
            },

            # SECCIÓN: VALIDACIONES
            "integrity_checks": {
                "now_playing_not_in_approved": (
                    now_playing.id not in [s.id for s in all_approved]
                    if now_playing else True
                ),
                "no_duplicates": len(all_ids) == len(set(all_ids)),
                "all_approved_have_correct_status": all(
                    s.estado == "aprobado" for s in all_approved
                ),
                "all_lazy_have_correct_status": all(
                    s.estado == "pendiente_lazy" for s in all_lazy
                ),
                "issues_detected": len(issues) > 0
            },

            # SECCIÓN: PROBLEMAS
            "issues": issues,

            # SECCIÓN: HISTORIAL
            "recent_queue_operations": [
                {
                    "timestamp": log.timestamp.isoformat(),
                    "action": log.action,
                    "details": log.details
                }
                for log in recent_logs
                if "QUEUE" in log.action or "LAZY" in log.action or "MOVE" in log.action or "APPROVE" in log.action
            ]
        }

    @staticmethod
    def get_next_song_to_play(db: Session) -> Dict[str, Any]:
        """
        Retorna LA PRÓXIMA CANCIÓN que va a reproducir el player.
        EXACTAMENTE la que se va a tocar, sin ambigüedades.
        """
        # 1. ¿Hay algo reproduciendo?
        now_playing = db.query(models.Cancion).filter(
            models.Cancion.estado == "reproduciendo"
        ).first()

        # Si está reproduciendo, la próxima es la primera aprobada
        if now_playing:
            next_song = db.query(models.Cancion).filter(
                models.Cancion.estado == "aprobado"
            ).order_by(
                models.Cancion.orden_manual.asc(),
                models.Cancion.id.asc()
            ).first()

            return {
                "status": "something_is_playing",
                "now_playing": {
                    "id": now_playing.id,
                    "titulo": now_playing.titulo,
                    "usuario": now_playing.usuario.nick if now_playing.usuario else None,
                    "started_at": now_playing.started_at.isoformat() if now_playing.started_at else None,
                    "duracion_seconds": now_playing.duracion_seconds,
                    "progress_percent": QueueDebugger._calculate_progress(now_playing)
                },
                "next_after_current": {
                    "id": next_song.id,
                    "titulo": next_song.titulo,
                    "usuario": next_song.usuario.nick if next_song.usuario else None,
                    "orden_manual": next_song.orden_manual,
                    "created_at": next_song.created_at.isoformat()
                } if next_song else None
            }
        else:
            # Si no hay nada reproduciendo, la próxima es la primera aprobada
            next_song = db.query(models.Cancion).filter(
                models.Cancion.estado == "aprobado"
            ).order_by(
                models.Cancion.orden_manual.asc(),
                models.Cancion.id.asc()
            ).first()

            if next_song:
                return {
                    "status": "ready_to_play",
                    "nothing_playing": True,
                    "next_to_play": {
                        "id": next_song.id,
                        "titulo": next_song.titulo,
                        "usuario": next_song.usuario.nick if next_song.usuario else None,
                        "duracion_seconds": next_song.duracion_seconds,
                        "urgency": "PLAY NOW"
                    }
                }
            else:
                # Si no hay aprobadas, revisar lazy
                lazy_song = db.query(models.Cancion).filter(
                    models.Cancion.estado == "pendiente_lazy"
                ).order_by(
                    models.Cancion.orden_manual.asc() if False else models.Cancion.id.asc()
                ).first()

                if lazy_song:
                    return {
                        "status": "waiting_for_approval",
                        "no_approved": True,
                        "first_lazy_waiting": {
                            "id": lazy_song.id,
                            "titulo": lazy_song.titulo,
                            "usuario": lazy_song.usuario.nick if lazy_song.usuario else None,
                            "message": "DEBE SER APROBADA PRIMERO"
                        }
                    }
                else:
                    return {
                        "status": "empty",
                        "message": "NO HAY CANCIONES EN LA COLA"
                    }

    @staticmethod
    def _calculate_progress(song: models.Cancion) -> int:
        """Calcula % de progreso de canción en reproducción."""
        if not song.started_at or not song.duracion_seconds:
            return 0

        try:
            now = now_bogota()
            started = song.started_at
            
            # Asegurar que ambos tienen la misma tz awareness
            if started.tzinfo is None and now.tzinfo is not None:
                # song.started_at es naive, convertir a aware usando tzinfo de now
                started = started.replace(tzinfo=now.tzinfo)
            elif started.tzinfo is not None and now.tzinfo is None:
                # now es naive (unlikely), usar naive
                now = now.replace(tzinfo=started.tzinfo)
            
            elapsed = (now - started).total_seconds()
            progress = min(100, int((elapsed / song.duracion_seconds) * 100))
            return max(0, progress)
        except Exception:
            return 0

    @staticmethod
    def get_ui_vs_reality_comparison(db: Session, ui_queue_state: Dict) -> Dict[str, Any]:
        """
        Compara lo que la UI está mostrando vs la realidad en BD.
        ÚTIL PARA ENCONTRAR CANCIONES "ESCONDIDAS".
        """
        # Obtener realidad del backend
        now_playing_real = db.query(models.Cancion).filter(
            models.Cancion.estado == "reproduciendo"
        ).first()

        approved_real = db.query(models.Cancion).filter(
            models.Cancion.estado == "aprobado"
        ).order_by(
            models.Cancion.orden_manual.asc(),
            models.Cancion.id.asc()
        ).all()

        # Extraer IDs de lo que muestra la UI
        ui_now_playing_id = (
            ui_queue_state.get("now_playing", {}).get("id")
            if ui_queue_state.get("now_playing") else None
        )

        ui_upcoming_ids = [
            s.get("id") for s in ui_queue_state.get("upcoming", [])
        ]

        # Realidad
        reality_now_playing_id = now_playing_real.id if now_playing_real else None
        reality_upcoming_ids = [s.id for s in approved_real]

        # Comparación
        discrepancies = []

        # Check 1: now_playing diferente
        if ui_now_playing_id != reality_now_playing_id:
            discrepancies.append(
                {
                    "type": "now_playing_mismatch",
                    "severity": "CRITICAL",
                    "ui_shows": ui_now_playing_id,
                    "reality_is": reality_now_playing_id,
                    "message": "La canción que UI muestra como reproduciendo NO ES la real"
                }
            )

        # Check 2: Canciones escondidas (en BD pero no en UI)
        hidden_songs_ids = set(reality_upcoming_ids) - set(ui_upcoming_ids)
        if hidden_songs_ids:
            hidden_songs = [s for s in approved_real if s.id in hidden_songs_ids]
            discrepancies.append(
                {
                    "type": "hidden_songs",
                    "severity": "CRITICAL",
                    "count": len(hidden_songs),
                    "hidden_song_ids": list(hidden_songs_ids),
                    "hidden_songs_details": [
                        {
                            "id": s.id,
                            "titulo": s.titulo,
                            "usuario": s.usuario.nick if s.usuario else None
                        }
                        for s in hidden_songs
                    ],
                    "message": f"{len(hidden_songs)} CANCIONES ESTÁN EN BD PERO NO MUESTRA LA UI"
                }
            )

        # Check 3: Canciones fantasma (en UI pero no en BD)
        phantom_songs_ids = set(ui_upcoming_ids) - set(reality_upcoming_ids)
        if phantom_songs_ids:
            discrepancies.append(
                {
                    "type": "phantom_songs",
                    "severity": "WARNING",
                    "count": len(phantom_songs_ids),
                    "phantom_song_ids": list(phantom_songs_ids),
                    "message": f"{len(phantom_songs_ids)} CANCIONES EN UI PERO NO EN BD (fueron eliminadas?)"
                }
            )

        # Check 4: Orden diferente
        if ui_upcoming_ids and reality_upcoming_ids:
            if ui_upcoming_ids != reality_upcoming_ids:
                # Encontrar diferencias de orden
                position_mismatches = []
                for i in range(min(len(ui_upcoming_ids), len(reality_upcoming_ids))):
                    if ui_upcoming_ids[i] != reality_upcoming_ids[i]:
                        position_mismatches.append({
                            "position": i + 1,
                            "ui_has": ui_upcoming_ids[i],
                            "reality_has": reality_upcoming_ids[i]
                        })

                if position_mismatches:
                    discrepancies.append(
                        {
                            "type": "order_mismatch",
                            "severity": "WARNING",
                            "mismatches": position_mismatches[:5],
                            "message": "El orden de la cola está diferente entre UI y realidad"
                        }
                    )

        return {
            "timestamp": now_bogota().isoformat(),
            "ui_state": {
                "now_playing_id": ui_now_playing_id,
                "upcoming_count": len(ui_upcoming_ids),
                "upcoming_ids": ui_upcoming_ids[:20]
            },
            "reality_state": {
                "now_playing_id": reality_now_playing_id,
                "upcoming_count": len(reality_upcoming_ids),
                "upcoming_ids": reality_upcoming_ids[:20]
            },
            "discrepancies": discrepancies,
            "summary": {
                "is_synchronized": len(discrepancies) == 0,
                "issues_found": len(discrepancies),
                "critical_issues": len([d for d in discrepancies if d.get("severity") == "CRITICAL"]),
                "warnings": len([d for d in discrepancies if d.get("severity") == "WARNING"])
            }
        }
