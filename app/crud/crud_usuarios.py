"""
Módulo CRUD para Usuarios y Ranking.
Gestiona usuarios en BD y estadísticas de actividad.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from collections import Counter
import datetime

import models
import schemas
from cache_manager import cache_manager as cache


# ================================================================================
# FUNCIONES PARA USUARIOS (En BD)
# ================================================================================

def get_usuario_by_id(db: Session, usuario_id: int):
    """Busca un usuario por su ID."""
    return db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()


def get_usuario_by_nick(db: Session, nick: str):
    """Busca un usuario por su nick (case-insensitive)."""
    return db.query(models.Usuario).filter(
        func.lower(models.Usuario.nick) == func.lower(nick)
    ).first()


def create_usuario(db: Session, usuario: schemas.UsuarioCreate):
    """Crea un nuevo usuario en la BD."""
    db_usuario = models.Usuario(nick=usuario.nick)
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario


def create_usuario_en_mesa(db: Session, usuario: schemas.UsuarioCreate, mesa_id: int):
    """Crea un nuevo usuario y lo asocia a una mesa."""
    db_usuario = models.Usuario(nick=usuario.nick, mesa_id=mesa_id)
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario


def get_o_crear_usuario_admin_para_mesa(db: Session, mesa_id: int):
    """Obtiene o crea un usuario admin/DJ para una mesa específica."""
    nick = f"MESA_{mesa_id}_ADMIN"
    user = get_usuario_by_nick(db, nick)
    if not user:
        user = models.Usuario(nick=nick, mesa_id=mesa_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def get_all_usuarios(db: Session):
    """Obtiene todos los usuarios."""
    return db.query(models.Usuario).all()


def update_usuario(db: Session, usuario_id: int, usuario_data: dict):
    """Actualiza un usuario."""
    db_usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not db_usuario:
        return None

    for key, value in usuario_data.items():
        if hasattr(db_usuario, key) and value is not None:
            setattr(db_usuario, key, value)

    db.commit()
    db.refresh(db_usuario)
    return db_usuario


def delete_usuario(db: Session, usuario_id: int):
    """Elimina un usuario."""
    db_usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if db_usuario:
        db.delete(db_usuario)
        db.commit()
    return db_usuario


def get_or_create_dj_user(db: Session):
    """Obtiene o crea el usuario DJ para reproducir canciones."""
    dj_user = get_usuario_by_nick(db, "DJ_KARAOKE")
    if not dj_user:
        dj_user = create_usuario(db, schemas.UsuarioCreate(nick="DJ_KARAOKE"))
    return dj_user


# ================================================================================
# ESTADÍSTICAS DE USUARIOS
# ================================================================================

def get_total_consumido_por_usuario(db: Session, usuario_id: int):
    """Calcula el total consumido por un usuario (CACHE)."""
    from decimal import Decimal
    consumos = cache.get_consumos_by_usuario(usuario_id)
    if not consumos:
        return Decimal('0.00')
    return sum(Decimal(str(c.get("valor_total", 0))) for c in consumos)


def get_ranking_usuarios(db: Session):
    """Obtiene el ranking de usuarios ordenado por puntos."""
    usuarios = db.query(models.Usuario).order_by(models.Usuario.puntos.desc()).all()
    return [
        {
            "usuario_id": u.id,
            "nick": u.nick,
            "puntos": u.puntos,
            "nivel": u.nivel,
            "last_active": u.last_active
        }
        for u in usuarios
    ]


def get_usuarios_sin_consumo(db: Session):
    """Usuarios que no han realizado consumos."""
    consumos = cache.get_all_consumos()
    usuarios_con_consumo = {c.get("usuario_id") for c in consumos}
    return db.query(models.Usuario).filter(
        ~models.Usuario.id.in_(usuarios_con_consumo)
    ).all()


def get_usuarios_una_cancion(db: Session):
    """Usuarios que han cantado exactamente una canción."""
    all_songs = cache.get_all_songs()
    cantadas = [s for s in all_songs if s.get("estado") == "cantada"]
    user_counts = Counter(s.get("usuario_id") for s in cantadas)

    one_hit_ids = [u_id for u_id, count in user_counts.items() if count == 1]
    return db.query(models.Usuario).filter(models.Usuario.id.in_(one_hit_ids)).all()


def get_usuarios_inactivos_consumo(db: Session, horas: int = 2):
    """Usuarios sin consumos en las últimas N horas."""
    consumos = cache.get_all_consumos()
    usuarios = db.query(models.Usuario).all()

    last_consumo = {}
    from datetime import datetime, timedelta

    for c in consumos:
        uid = c.get("usuario_id")
        created = c.get("created_at")
        if uid and created:
            try:
                created = created.replace("Z", "+00:00")
                dt = datetime.fromisoformat(created)
                if uid not in last_consumo or dt > last_consumo[uid]:
                    last_consumo[uid] = dt
            except ValueError:
                pass

    from timezone_utils import now_bogota
    now = now_bogota()

    for uid in last_consumo:
        if last_consumo[uid].tzinfo is None:
            last_consumo[uid] = last_consumo[uid].replace(tzinfo=now.tzinfo)

    inactivos = []
    for u in usuarios:
        if u.id not in last_consumo:
            inactivos.append(u)
        else:
            diff = now - last_consumo[u.id]
            if diff > timedelta(hours=horas):
                inactivos.append(u)

    return inactivos


def get_usuarios_consumen_pero_no_cantan(db: Session, umbral_consumo: float = 100.0):
    """Usuarios que consumen pero no cantan."""
    canciones = cache.get_all_songs()
    consumos = cache.get_all_consumos()
    usuarios = db.query(models.Usuario).all()

    cantores = {c.get("usuario_id") for c in canciones if c.get("usuario_id")}

    gastos = {}
    for c in consumos:
        uid = c.get("usuario_id")
        if uid:
            gastos[uid] = gastos.get(uid, 0) + float(c.get("valor_total", 0))

    result = []
    for u in usuarios:
        if u.id not in cantores and gastos.get(u.id, 0) > umbral_consumo:
            result.append(u)

    return result


def get_usuarios_mas_rechazados(db: Session, limit: int = 10):
    """Usuarios con más canciones rechazadas."""
    all_songs = cache.get_all_songs()
    rechazadas = [s for s in all_songs if s.get("estado") == "rechazada"]

    user_counts = Counter(s.get("usuario_id") for s in rechazadas)
    user_ids = [u_id for u_id, _ in user_counts.most_common(limit)]

    usuarios = db.query(models.Usuario).filter(models.Usuario.id.in_(user_ids)).all()
    user_map = {u.id: u.nick for u in usuarios}

    return [
        (user_map.get(u_id, f"Usuario #{u_id}"), count)
        for u_id, count in user_counts.most_common(limit)
    ]
