from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models.usuario_local import UsuarioLocal
from app.db.models.usuario_empleado import UsuarioEmpleadoLocal
from app.schemas import (
    UsuarioLocalCreate, UsuarioLocalOut, UsuarioLocalLogin,
    UsuarioEmpleadoLocalCreate, UsuarioEmpleadoLocalOut,
    TokenOut
)
from app.security import hash_password, verify_password, create_access_token, security
from typing import List

router = APIRouter()

@router.post("/register", response_model=UsuarioLocalOut)
def register_owner(owner_in: UsuarioLocalCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    existing = db.query(UsuarioLocal).filter(UsuarioLocal.email == owner_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya está registrado."
        )
    
    hashed_pwd = hash_password(owner_in.password)
    new_owner = UsuarioLocal(
        email=owner_in.email,
        password_hash=hashed_pwd,
        nombre=owner_in.nombre,
        telefono=owner_in.telefono
    )
    db.add(new_owner)
    db.commit()
    db.refresh(new_owner)
    return new_owner

@router.post("/login", response_model=TokenOut)
def login_owner(login_in: UsuarioLocalLogin, db: Session = Depends(get_db)):
    owner = db.query(UsuarioLocal).filter(UsuarioLocal.email == login_in.email).first()
    if not owner or not verify_password(login_in.password, owner.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas."
        )
    
    if not owner.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo."
        )

    # Get their local slugs
    slugs = [local.slug for local in owner.locales]

    token_data = {
        "sub": owner.email,
        "role": "owner",
        "name": owner.nombre,
        "id": owner.id
    }
    token = create_access_token(token_data)
    
    return TokenOut(
        access_token=token,
        role="owner",
        email=owner.email,
        name=owner.nombre,
        local_slugs=slugs
    )

@router.post("/employee/login", response_model=TokenOut)
def login_employee(login_in: UsuarioLocalLogin, db: Session = Depends(get_db)):
    employee = db.query(UsuarioEmpleadoLocal).filter(UsuarioEmpleadoLocal.email == login_in.email).first()
    if not employee or not verify_password(login_in.password, employee.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas."
        )
    
    if not employee.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo."
        )

    token_data = {
        "sub": employee.email,
        "role": employee.rol,
        "name": employee.nombre,
        "id": employee.id,
        "local_id": employee.local_id,
        "local_slug": employee.local.slug if employee.local else ""
    }
    token = create_access_token(token_data)
    
    return TokenOut(
        access_token=token,
        role=employee.rol,
        email=employee.email,
        name=employee.nombre,
        local_slugs=[employee.local.slug] if employee.local else []
    )

# Helper functions for dependency injection
from jose import jwt, JWTError
from app.security import SECRET_KEY, ALGORITHM

def get_current_user_payload(credentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado."
        )

def get_current_owner(payload: dict = Depends(get_current_user_payload), db: Session = Depends(get_db)) -> UsuarioLocal:
    if payload.get("role") != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permisos insuficientes."
        )
    email = payload.get("sub")
    owner = db.query(UsuarioLocal).filter(UsuarioLocal.email == email).first()
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado."
        )
    return owner
