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

    # Get their local slugs and ids
    slugs = [local.slug for local in owner.locales]
    local_ids = [local.id for local in owner.locales]
    all_modules = ['dashboard', 'queue', 'inventory', 'accounts', 'reports', 'settings', 'tables']

    token_data = {
        "sub": owner.email,
        "role": "owner",
        "name": owner.nombre,
        "id": owner.id,
        "local_slugs": slugs,
        "local_ids": local_ids,
        "modulos_permitidos": all_modules
    }
    token = create_access_token(token_data)
    
    return TokenOut(
        access_token=token,
        role="owner",
        email=owner.email,
        name=owner.nombre,
        local_slugs=slugs,
        local_ids=local_ids,
        modulos_permitidos=all_modules
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

    modulos = []
    if employee.modulos_permitidos:
        try:
            modulos = json.loads(employee.modulos_permitidos)
        except Exception:
            modulos = [m.strip() for m in employee.modulos_permitidos.split(",") if m.strip()]
    if not modulos:
        if employee.rol == 'admin':
            modulos = ['dashboard', 'queue', 'inventory', 'accounts', 'reports', 'settings', 'tables']
        elif employee.rol == 'cajero':
            modulos = ['dashboard', 'accounts', 'tables', 'reports']
        elif employee.rol == 'mesero':
            modulos = ['accounts', 'tables', 'queue']
        elif employee.rol == 'dj':
            modulos = ['queue']
        else:
            modulos = ['dashboard', 'accounts', 'queue', 'tables']

    local_slugs = [employee.local.slug] if employee.local else []
    local_ids = [employee.local_id] if employee.local_id else []

    token_data = {
        "sub": employee.email,
        "role": employee.rol,
        "name": employee.nombre,
        "id": employee.id,
        "local_id": employee.local_id,
        "local_ids": local_ids,
        "local_slug": employee.local.slug if employee.local else "",
        "modulos_permitidos": modulos
    }
    token = create_access_token(token_data)
    
    return TokenOut(
        access_token=token,
        role=employee.rol,
        email=employee.email,
        name=employee.nombre,
        local_slugs=local_slugs,
        local_ids=local_ids,
        modulos_permitidos=modulos
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
