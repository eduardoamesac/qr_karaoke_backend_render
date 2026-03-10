"""CRUD operations for Users (in database)."""

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.models import Usuario
from app.schemas import UsuarioCreate


def get_usuario_by_id(db: Session, usuario_id: int):
    """Busca un usuario por su ID."""
    return db.query(Usuario).filter(Usuario.id == usuario_id).first()


def get_usuario_by_nick(db: Session, nick: str):
    """Busca un usuario por su nick (case-insensitive)."""
    return db.query(Usuario).filter(func.lower(Usuario.nick) == func.lower(nick)).first()


def create_usuario(db: Session, usuario: UsuarioCreate):
    """Crea un nuevo usuario en la BD."""
    db_usuario = Usuario(nick=usuario.nick)
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario


def create_usuario_en_mesa(db: Session, usuario: UsuarioCreate, mesa_id: int):
    """Crea un nuevo usuario y lo asocia a una mesa."""
    db_usuario = Usuario(nick=usuario.nick, mesa_id=mesa_id)
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario


def get_o_crear_usuario_admin_para_mesa(db: Session, mesa_id: int):
    """Obtiene o crea un usuario admin/DJ para una mesa específica."""
    nick = f"MESA_{mesa_id}_ADMIN"
    user = get_usuario_by_nick(db, nick)
    if not user:
        user = Usuario(nick=nick, mesa_id=mesa_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def get_all_usuarios(db: Session):
    """Obtiene todos los usuarios."""
    return db.query(Usuario).all()


def update_usuario(db: Session, usuario_id: int, usuario_data: dict):
    """Actualiza un usuario."""
    db_usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
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
    db_usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if db_usuario:
        db.delete(db_usuario)
        db.commit()
    return db_usuario


def get_or_create_dj_user(db: Session):
    """Obtiene o crea el usuario DJ para reproducir canciones."""
    dj_user = get_usuario_by_nick(db, "DJ_KARAOKE")
    if not dj_user:
        dj_user = create_usuario(db, UsuarioCreate(nick="DJ_KARAOKE"))
    return dj_user


def get_ranking_usuarios(db: Session):
    """Obtiene el ranking de usuarios ordenado por puntos."""
    usuarios = db.query(Usuario).order_by(Usuario.puntos.desc()).all()
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
