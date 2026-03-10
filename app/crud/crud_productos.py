"""
Módulo CRUD para Productos / Inventario.
Gestiona el catálogo de productos almacenados en BD.
"""

from sqlalchemy.orm import Session
from decimal import Decimal
from collections import Counter

import models
import schemas
from cache_manager import cache_manager as cache


# ================================================================================
# FUNCIONES PARA PRODUCTOS (En BD)
# ================================================================================

def get_producto_by_id(db: Session, producto_id: int):
    """Obtiene un producto por ID."""
    return db.query(models.Producto).filter(models.Producto.id == producto_id).first()


def get_producto_by_nombre(db: Session, nombre: str):
    """Obtiene un producto por nombre."""
    return db.query(models.Producto).filter(models.Producto.nombre == nombre).first()


def get_all_productos(db: Session):
    """Obtiene todos los productos activos."""
    return db.query(models.Producto).filter(models.Producto.is_active == True).all()


def get_productos(db: Session, skip: int = 0, limit: int = 100):
    """Obtiene productos con paginación (sin filtrar por is_active)."""
    return db.query(models.Producto).offset(skip).limit(limit).all()


def create_producto(db: Session, producto: schemas.ProductoCreate):
    """Crea un nuevo producto."""
    db_producto = models.Producto(**producto.dict())
    db.add(db_producto)
    db.commit()
    db.refresh(db_producto)
    return db_producto


def update_producto(db: Session, producto_id: int, producto_update: schemas.ProductoCreate):
    """Actualiza un producto."""
    db_producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
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
    """Elimina un producto de la base de datos por su ID."""
    db_producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
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
    db_producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if db_producto:
        db_producto.valor = nuevo_valor
        db.commit()
        db.refresh(db_producto)
    return db_producto


def update_producto_active_status(db: Session, producto_id: int, is_active: bool):
    """Actualiza el estado de activación de un producto."""
    db_producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if db_producto:
        db_producto.is_active = is_active
        db.commit()
        db.refresh(db_producto)
    return db_producto


# ================================================================================
# ESTADÍSTICAS DE PRODUCTOS
# ================================================================================

def get_productos_mas_consumidos(db: Session, limit: int = 10):
    """Reporte de productos más consumidos."""
    consumos = cache.get_all_consumos()
    product_counts = Counter()
    for c in consumos:
        product_counts[c.get("producto_id")] += c.get("cantidad", 0)

    product_ids = [p_id for p_id, _ in product_counts.most_common(limit)]
    productos = db.query(models.Producto).filter(
        models.Producto.id.in_(product_ids)
    ).all()
    prod_map = {p.id: p.nombre for p in productos}

    return [
        (prod_map.get(p_id, f"Producto #{p_id}"), count)
        for p_id, count in product_counts.most_common(limit)
    ]


def get_productos_menos_consumidos(db: Session, limit: int = 5):
    """Reporte de productos menos consumidos."""
    consumos = cache.get_all_consumos()
    productos = db.query(models.Producto).all()
    cantidades = {p.id: 0 for p in productos}
    for c in consumos:
        pid = c.get("producto_id")
        if pid in cantidades:
            cantidades[pid] += c.get("cantidad", 1)

    prod_map = {p.id: p.nombre for p in productos}
    result = [(prod_map[pid], cant) for pid, cant in cantidades.items()]
    result.sort(key=lambda x: x[1])
    return result[:limit]


def get_productos_no_consumidos(db: Session):
    """Productos que no han sido consumidos."""
    consumos = cache.get_all_consumos()
    productos = db.query(models.Producto).all()

    consumidos_ids = {c.get("producto_id") for c in consumos}
    no_consumidos = [p for p in productos if p.id not in consumidos_ids]
    return no_consumidos


def get_productos_mas_consumidos_por_mesa(db: Session, mesa_id: int, limit: int = 5):
    """Reporte de productos más consumidos en una mesa específica."""
    consumos = [c for c in cache.get_all_consumos() if c.get("mesa_id") == mesa_id]
    productos = db.query(models.Producto).all()
    prod_map = {p.id: p.nombre for p in productos}

    counts = {}
    for c in consumos:
        pid = c.get("producto_id")
        counts[pid] = counts.get(pid, 0) + c.get("cantidad", 1)

    result = [(prod_map.get(pid, "Desconocido"), count) for pid, count in counts.items()]
    result.sort(key=lambda x: x[1], reverse=True)
    return result[:limit]
