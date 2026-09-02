import json
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
    LocalCreate, LocalUpdate, LocalOut,
    UsuarioEmpleadoLocalCreate, UsuarioEmpleadoLocalOut, UsuarioEmpleadoLocalUpdate
)
from app.routers.auth_saas import get_current_owner
from app.security import hash_password
from typing import List

router = APIRouter()

def format_employee_out(emp: UsuarioEmpleadoLocal) -> UsuarioEmpleadoLocalOut:
    modulos = []
    if emp.modulos_permitidos:
        try:
            modulos = json.loads(emp.modulos_permitidos)
        except Exception:
            modulos = [m.strip() for m in emp.modulos_permitidos.split(",") if m.strip()]
    return UsuarioEmpleadoLocalOut(
        id=emp.id,
        email=emp.email,
        nombre=emp.nombre,
        rol=emp.rol,
        local_id=emp.local_id,
        modulos_permitidos=modulos,
        is_active=emp.is_active,
        created_at=emp.created_at
    )

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
        telefono=local_in.telefono,
        hora_cierre=local_in.hora_cierre or "03:00",
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

@router.put("/{local_id}", response_model=LocalOut)
@router.put("/{local_id}/", response_model=LocalOut)
@router.patch("/{local_id}", response_model=LocalOut)
@router.patch("/{local_id}/", response_model=LocalOut)
@router.post("/{local_id}/update", response_model=LocalOut)
def update_local(
    local_id: int,
    local_in: LocalUpdate,
    db: Session = Depends(get_db),
    owner: UsuarioLocal = Depends(get_current_owner)
):
    local = db.query(Local).filter(Local.id == local_id).first()
    if not local or owner not in local.administradores:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para administrar este establecimiento."
        )

    if local_in.slug is not None and local_in.slug != local.slug:
        existing = db.query(Local).filter(Local.slug == local_in.slug, Local.id != local_id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La URL personalizada (slug) ya está en uso."
            )
        local.slug = local_in.slug

    if local_in.nombre is not None:
        local.nombre = local_in.nombre
    if local_in.direccion is not None:
        local.direccion = local_in.direccion
    if local_in.telefono is not None:
        local.telefono = local_in.telefono
    if local_in.hora_cierre is not None:
        local.hora_cierre = local_in.hora_cierre
    if local_in.logo_url is not None:
        local.logo_url = local_in.logo_url
    if local_in.is_active is not None:
        local.is_active = local_in.is_active

    db.commit()
    db.refresh(local)
    return local

@router.delete("/{local_id}")
@router.delete("/{local_id}/")
@router.post("/{local_id}/delete")
def delete_local(
    local_id: int,
    db: Session = Depends(get_db),
    owner: UsuarioLocal = Depends(get_current_owner)
):
    local = db.query(Local).filter(Local.id == local_id).first()
    if not local or owner not in local.administradores:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para administrar este establecimiento."
        )

    if len(owner.locales) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes eliminar tu única sede activa."
        )

    db.delete(local)
    db.commit()
    return {"ok": True, "message": "Establecimiento eliminado correctamente."}

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
    modulos_json = json.dumps(employee_in.modulos_permitidos or ["dashboard", "accounts", "queue", "tables"])
    new_employee = UsuarioEmpleadoLocal(
        local_id=local_id,
        email=employee_in.email,
        password_hash=hashed_pwd,
        nombre=employee_in.nombre,
        rol=employee_in.rol,
        modulos_permitidos=modulos_json
    )
    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)
    return format_employee_out(new_employee)

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
    return [format_employee_out(emp) for emp in local.empleados]

@router.put("/{local_id}/employees/{employee_id}", response_model=UsuarioEmpleadoLocalOut)
def update_employee(
    local_id: int,
    employee_id: int,
    employee_in: UsuarioEmpleadoLocalUpdate,
    db: Session = Depends(get_db),
    owner: UsuarioLocal = Depends(get_current_owner)
):
    local = db.query(Local).filter(Local.id == local_id).first()
    if not local or owner not in local.administradores:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para administrar este establecimiento."
        )

    employee = db.query(UsuarioEmpleadoLocal).filter(
        UsuarioEmpleadoLocal.id == employee_id,
        UsuarioEmpleadoLocal.local_id == local_id
    ).first()

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empleado no encontrado."
        )

    if employee_in.nombre is not None:
        employee.nombre = employee_in.nombre
    if employee_in.rol is not None:
        employee.rol = employee_in.rol
    if employee_in.modulos_permitidos is not None:
        employee.modulos_permitidos = json.dumps(employee_in.modulos_permitidos)
    if employee_in.is_active is not None:
        employee.is_active = employee_in.is_active
    if employee_in.password:
        employee.password_hash = hash_password(employee_in.password)

    db.commit()
    db.refresh(employee)
    return format_employee_out(employee)

@router.delete("/{local_id}/employees/{employee_id}")
def delete_employee(
    local_id: int,
    employee_id: int,
    db: Session = Depends(get_db),
    owner: UsuarioLocal = Depends(get_current_owner)
):
    local = db.query(Local).filter(Local.id == local_id).first()
    if not local or owner not in local.administradores:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para administrar este establecimiento."
        )

    employee = db.query(UsuarioEmpleadoLocal).filter(
        UsuarioEmpleadoLocal.id == employee_id,
        UsuarioEmpleadoLocal.local_id == local_id
    ).first()

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empleado no encontrado."
        )

    db.delete(employee)
    db.commit()
    return {"ok": True, "message": "Empleado eliminado correctamente."}

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

    total_sales = db.query(Pago).count() * 12500.0
    active_customers = db.query(Usuario).filter(Usuario.is_active == True).count()
    total_products = db.query(Producto).filter(Producto.local_id == local_id, Producto.is_active == True).count()
    
    return {
        "local_name": local.nombre,
        "active_tables": 6,
        "active_customers": active_customers,
        "total_sales": total_sales,
        "total_products": total_products
    }

