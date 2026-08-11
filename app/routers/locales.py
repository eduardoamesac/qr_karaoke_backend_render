from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models.local import Local
from app.db.models.usuario_local import UsuarioLocal
from app.db.models.usuario_empleado import UsuarioEmpleadoLocal
from app.db.models.pago import Pago
from app.db.models.usuario import Usuario
from app.db.models.producto import Producto
from app.schemas import (
    LocalCreate, LocalOut,
    UsuarioEmpleadoLocalCreate, UsuarioEmpleadoLocalOut
)
from app.routers.auth_saas import get_current_owner
from app.security import hash_password
from typing import List

router = APIRouter()

@router.post("", response_model=LocalOut)
def create_local(local_in: LocalCreate, db: Session = Depends(get_db), owner: UsuarioLocal = Depends(get_current_owner)):
    # Check if slug is unique
    existing = db.query(Local).filter(Local.slug == local_in.slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La URL personalizada (slug) ya está en uso."
        )
    
    new_local = Local(
        nombre=local_in.nombre,
        slug=local_in.slug,
        direccion=local_in.direccion,
        logo_url=local_in.logo_url
    )
    
    # Associate owner
    new_local.administradores.append(owner)
    
    db.add(new_local)
    db.commit()
    db.refresh(new_local)
    return new_local

@router.get("", response_model=List[LocalOut])
def get_my_locales(db: Session = Depends(get_db), owner: UsuarioLocal = Depends(get_current_owner)):
    return owner.locales

@router.get("/{slug}", response_model=LocalOut)
def get_local_by_slug(slug: str, db: Session = Depends(get_db)):
    local = db.query(Local).filter(Local.slug == slug).first()
    if not local:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Establecimiento no encontrado."
        )
    return local

@router.post("/{local_id}/employees", response_model=UsuarioEmpleadoLocalOut)
def create_employee(
    local_id: int,
    employee_in: UsuarioEmpleadoLocalCreate,
    db: Session = Depends(get_db),
    owner: UsuarioLocal = Depends(get_current_owner)
):
    # Verify owner owns this local
    local = db.query(Local).filter(Local.id == local_id).first()
    if not local or owner not in local.administradores:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para administrar este establecimiento."
        )
        
    # Check if email is unique
    existing = db.query(UsuarioEmpleadoLocal).filter(UsuarioEmpleadoLocal.email == employee_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico del empleado ya está registrado."
        )
        
    hashed_pwd = hash_password(employee_in.password)
    new_employee = UsuarioEmpleadoLocal(
        local_id=local_id,
        email=employee_in.email,
        password_hash=hashed_pwd,
        nombre=employee_in.nombre,
        rol=employee_in.rol
    )
    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)
    return new_employee

@router.get("/{local_id}/employees", response_model=List[UsuarioEmpleadoLocalOut])
def list_employees(
    local_id: int,
    db: Session = Depends(get_db),
    owner: UsuarioLocal = Depends(get_current_owner)
):
    local = db.query(Local).filter(Local.id == local_id).first()
    if not local or owner not in local.administradores:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver los empleados de este establecimiento."
        )
    return local.empleados

@router.get("/{local_id}/dashboard-summary")
def get_dashboard_summary(
    local_id: int,
    db: Session = Depends(get_db),
    owner: UsuarioLocal = Depends(get_current_owner)
):
    # Verify owner owns this local
    local = db.query(Local).filter(Local.id == local_id).first()
    if not local or owner not in local.administradores:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado."
        )

    # Calculate some dashboard stats (total sales, active sessions, product count, etc.)
    # In a fully multi-tenant setup, pagos/usuarios would filter by local_id.
    # Let's write simple queries (even if the tables don't have local_id yet, we query totals for now or stub them gracefully)
    total_sales = db.query(Pago).count() * 12500.0  # mock/placeholder or read pagos
    active_customers = db.query(Usuario).filter(Usuario.is_active == True).count()
    total_products = db.query(Producto).filter(Producto.is_active == True).count()
    
    return {
        "local_name": local.nombre,
        "active_tables": 6,  # Placeholder/mock or count tables
        "active_customers": active_customers,
        "total_sales": total_sales,
        "total_products": total_products
    }
