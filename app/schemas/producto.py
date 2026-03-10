"""Schemas for Products (Productos)."""

from pydantic import BaseModel, ConfigDict
from typing import Optional
from decimal import Decimal


class ProductoBase(BaseModel):
    nombre: str
    categoria: str
    valor: Decimal
    costo: Decimal = Decimal("0")
    stock: int
    imagen_url: Optional[str] = None
    is_active: bool = True


class ProductoCreate(ProductoBase):
    pass


class Producto(ProductoBase):
    id: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class ProductoValorUpdate(BaseModel):
    valor: Decimal


class ProductoMasConsumido(BaseModel):
    nombre: str
    cantidad_total: int


class CompraProducto(BaseModel):
    producto_id: int
    cantidad_comprada: int
    nuevo_precio_compra: Optional[Decimal] = None
    model_config = ConfigDict(from_attributes=True)


class ReporteCategoriaMasVendida(BaseModel):
    categoria: str
    cantidad_total: int


class ReporteIngresosPorCategoria(BaseModel):
    categoria: str
    ingresos_totales: Decimal
