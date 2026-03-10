"""CRUD operations for Products (in database)."""

from sqlalchemy.orm import Session
from decimal import Decimal

from app.db.models import Producto
from app.schemas import ProductoCreate
from app.utils.cache_manager import cache_manager as cache


def get_producto_by_id(db: Session, producto_id: int):
    """Obtiene un producto por ID."""
    return db.query(Producto).filter(Producto.id == producto_id).first()


def get_producto_by_nombre(db: Session, nombre: str):
    """Obtiene un producto por nombre."""
    return db.query(Producto).filter(Producto.nombre == nombre).first()


def get_all_productos(db: Session):
    """Obtiene todos los productos activos."""
    return db.query(Producto).filter(Producto.is_active == True).all()


def get_productos(db: Session, skip: int = 0, limit: int = 100):
    """Obtiene productos con paginación (sin filtrar por is_active)."""
    return db.query(Producto).offset(skip).limit(limit).all()


def create_producto(db: Session, producto: ProductoCreate):
    """Crea un nuevo producto."""
    db_producto = Producto(**producto.dict())
    db.add(db_producto)
    db.commit()
    db.refresh(db_producto)
    return db_producto


def update_producto(db: Session, producto_id: int, producto_update: ProductoCreate):
    """Actualiza un producto."""
    db_producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not db_producto:
        return None

    producto_data = producto_update.dict(exclude_unset=True)
    for key, value in producto_data.items():
        if hasattr(db_producto, key) and value is not None:
            setattr(db_producto, key, value)

    db.commit()
    db.refresh(db_producto)
    return db_producto


def delete_producto(db: Session, producto_id: int):
    """
    Elimina un producto de la base de datos por su ID.
    Si tiene consumos asociados en el CACHE, solo lo desactiva.
    """
    db_producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not db_producto:
        return None, "Producto no encontrado."

    consumos_globales = cache.get_all_consumos()
    tiene_consumos = any(c.get("producto_id") == producto_id for c in consumos_globales)

    if tiene_consumos:
        db_producto.is_active = False
        db.commit()
        db.refresh(db_producto)
        return db_producto, "El producto tiene consumos asociados y ha sido desactivado."
    else:
        db.delete(db_producto)
        db.commit()
        return None, "Producto eliminado permanentemente."


def update_producto_valor(db: Session, producto_id: int, nuevo_valor: Decimal):
    """Actualiza el precio de un producto."""
    db_producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if db_producto:
        db_producto.valor = nuevo_valor
        db.commit()
        db.refresh(db_producto)
    return db_producto


def update_producto_active_status(db: Session, producto_id: int, is_active: bool):
    """Actualiza el estado de activación de un producto."""
    db_producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if db_producto:
        db_producto.is_active = is_active
        db.commit()
        db.refresh(db_producto)
    return db_producto
