"""Schemas for Payments (Pagos)."""

from pydantic import BaseModel, ConfigDict
from typing import Optional
from decimal import Decimal
from datetime import datetime


class PagoBase(BaseModel):
    monto: Decimal
    metodo_pago: Optional[str] = "Efectivo"


class PagoCreate(PagoBase):
    mesa_id: int


class PagoView(PagoBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ReporteIngresos(BaseModel):
    ingresos_totales: Decimal
    model_config = ConfigDict(from_attributes=True)


class ReporteIngresosPorMesa(BaseModel):
    mesa_nombre: str
    ingresos_totales: Decimal


class ReporteIngresosPromedio(BaseModel):
    ingresos_promedio_por_usuario: Decimal


class ReporteIngresosPromedioPorMesa(BaseModel):
    mesa_nombre: str
    ingresos_promedio_por_usuario: Decimal


class ResumenNoche(BaseModel):
    ingresos_totales: Decimal
    ganancias_totales: Decimal
    canciones_cantadas: int
    usuarios_activos: int


class CuentaInfo(BaseModel):
    id: int
    mesa_id: int
    is_active: bool
    created_at: datetime
    closed_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
