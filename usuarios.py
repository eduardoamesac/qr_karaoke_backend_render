from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from auth import verify_token, log_admin_action # New import

import crud, schemas
from database import SessionLocal

router = APIRouter()

# Dependencia para obtener la sesión de la base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/{nick}", response_model=schemas.Usuario, summary="Obtener un usuario por su nick")
def get_user_by_nick(nick: str, db: Session = Depends(get_db), admin: dict = Depends(verify_token)):
    log_admin_action(admin.get("sub"), "get_user_by_nick", f"Nick: {nick}")
    """
    **[Admin]** Busca y devuelve un usuario específico por su nick.
    Es útil para encontrar usuarios del sistema como 'DJ'.
    """
    db_usuario = crud.get_usuario_by_nick(db, nick=nick)
    if not db_usuario:
        raise HTTPException(status_code=404, detail=f"Usuario con nick '{nick}' no encontrado.")
    
    return db_usuario

@router.get("/{usuario_id}", response_model=schemas.UsuarioPublico, summary="Ver el perfil público de un usuario")
def ver_perfil_usuario(usuario_id: int, db: Session = Depends(get_db)):
    """
    Devuelve la información pública de un usuario, como su nivel y puntos.
    No incluye información sensible como el consumo total.
    """
    db_usuario = crud.get_usuario_by_id(db, usuario_id=usuario_id)
    if not db_usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    return db_usuario

@router.get("/{usuario_id}/song-credits", response_model=dict, summary="Ver créditos de canciones disponibles")
def ver_creditos_cancion(usuario_id: int, db: Session = Depends(get_db)):
    """
    Devuelve los créditos de canciones disponibles para un usuario.
    Muestra el valor actual de créditos y cuánto tiempo le queda antes de que decaigan a 0.
    """
    db_usuario = crud.get_usuario_by_id(db, usuario_id=usuario_id)
    if not db_usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    credits_detail = crud.get_user_credits_detail(db, usuario_id)
    return credits_detail

@router.get("/{usuario_id}/cuenta-regresiva", response_model=dict, summary="Ver cuenta regresiva de créditos")
def ver_cuenta_regresiva(usuario_id: int, db: Session = Depends(get_db)):
    """
    Devuelve la información simplificada de los créditos para mostrar en la UI.
    """
    db_usuario = crud.get_usuario_by_id(db, usuario_id=usuario_id)
    if not db_usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    available_credits = crud.get_available_song_credits(db, usuario_id)
    return {
        "usuario_id": usuario_id,
        "credits_available": available_credits,
        "can_add_song": available_credits > 0,
        "needs_purchase": available_credits == 0
    }

@router.get("/", response_model=List[schemas.UsuarioPerfil], summary="Ver el ranking de usuarios")
def ver_ranking_usuarios(db: Session = Depends(get_db)):
    """
    Devuelve una lista de todos los usuarios ordenados por su consumo total
    de mayor a menor (ranking de clientes).
    """
    ranking_data = crud.get_ranking_usuarios(db)
    
    # Convertimos la lista de dicts a una lista de objetos UsuarioPerfil
    ranking_list = []
    for i, usuario_dict in enumerate(ranking_data):
        try:
            usuario = crud.get_usuario_by_id(db, usuario_dict["usuario_id"])
            if usuario:
                perfil = schemas.UsuarioPerfil(
                    id=usuario.id,
                    nick=usuario.nick,
                    puntos=usuario.puntos,
                    nivel=usuario.nivel,
                    last_active=usuario.last_active,
                    total_consumido=0,  # Calculado desde cache
                    rank=i + 1,
                    mesa=None  # La mesa ahora está en cache
                )
                ranking_list.append(perfil)
        except:
            pass

    
    return ranking_list