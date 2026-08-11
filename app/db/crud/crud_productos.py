"""CRUD operations for Products (in database)."""

from sqlalchemy.orm import Session
from decimal import Decimal
from typing import Optional

from app.db.models import Producto, Compra
from app.schemas import ProductoCreate
from app.utils.cache_manager import cache_manager as cache


def get_producto_by_id(db: Session, producto_id: int):
    """Obtiene un producto por ID."""
    return db.query(Producto).filter(Producto.id == producto_id).first()


def get_producto_by_nombre_and_local(db: Session, nombre: str, local_id: Optional[int] = None):
    """Obtiene un producto por nombre y local."""
    query = db.query(Producto).filter(Producto.nombre == nombre)
    if local_id is not None:
        query = query.filter(Producto.local_id == local_id)
    else:
        query = query.filter(Producto.local_id.is_(None))
    return query.first()


def get_all_productos(db: Session, local_id: Optional[int] = None):
    """Obtiene todos los productos activos."""
    query = db.query(Producto).filter(Producto.is_active == True)
    if local_id is not None:
        query = query.filter(Producto.local_id == local_id)
    else:
        query = query.filter(Producto.local_id.is_(None))
    return query.all()


def get_productos(db: Session, skip: int = 0, limit: int = 100, local_id: Optional[int] = None):
    """Obtiene productos con paginación (sin filtrar por is_active)."""
    query = db.query(Producto)
    if local_id is not None:
        query = query.filter(Producto.local_id == local_id)
    else:
        query = query.filter(Producto.local_id.is_(None))
    return query.offset(skip).limit(limit).all()


def create_producto(db: Session, producto: ProductoCreate, local_id: Optional[int] = None):
    """Crea un nuevo producto."""
    db_producto = Producto(**producto.dict())
    if local_id is not None:
        db_producto.local_id = local_id
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


def registrar_compra(db: Session, compra_data, local_id: int):
    """
    Registra una nueva compra, incrementa el stock y actualiza el costo del producto.
    """
    total_costo = Decimal(compra_data.cantidad) * Decimal(compra_data.precio_compra)
    db_compra = Compra(
        local_id=local_id,
        producto_id=compra_data.producto_id,
        cantidad=compra_data.cantidad,
        precio_compra=compra_data.precio_compra,
        total_costo=total_costo,
        proveedor=compra_data.proveedor
    )
    db.add(db_compra)
    
    # Aumentar stock y actualizar costo del producto
    db_producto = db.query(Producto).filter(Producto.id == compra_data.producto_id).first()
    if db_producto:
        db_producto.stock += compra_data.cantidad
        db_producto.costo = compra_data.precio_compra

    db.commit()
    db.refresh(db_compra)
    return db_compra


def get_compras_by_local(db: Session, local_id: int):
    """Obtiene el historial de compras para un local."""
    return db.query(Compra).filter(Compra.local_id == local_id).order_by(Compra.fecha.desc()).all()


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
