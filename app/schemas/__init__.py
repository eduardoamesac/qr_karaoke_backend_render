"""
app/schemas — Pydantic schemas.

Re-exports all schemas from this package so existing code using
`from app.schemas import Mesa, Usuario, ...` or `from app import schemas`
continues to work seamlessly.
"""

# Re-export everything from the existing schemas.py (now shadowed by this package)
# We duplicate the content here so both old and new import paths work.

from app.schemas.cancion import (
    CancionBase,
    CancionCreate,
    Cancion,
    CancionAdminView,
    CancionMasCantada,
    ReordenarCola,
    ReporteCancionesPorUsuario,
    ReporteCancionesPorMesa,
    ReporteCancionesRechazadas,
    ReporteCancionMasPedida,
    ReporteActividadPorHora,
    ReporteTiempoEsperaPromedio,
    PlayNextResponse,
    ColaView,
    ColaViewExtended,
)

from app.schemas.usuario import (
    UsuarioBase,
    UsuarioCreate,
    Usuario,
    UsuarioConectado,
    UsuarioPerfil,
    UsuarioPublico,
    UsuarioNickUpdate,
    UsuarioMoverMesa,
    UsuarioPuntosUpdate,
    ReporteGastoUsuarioPorCategoria,
    ReporteUsuarioRechazado,
    HistorialUsuario,
    BannedNickView,
    NickUnban,
)

from app.schemas.mesa import (
    MesaBase,
    MesaCreate,
    Mesa,
    MesaSimple,
    MesaInfo,
    MesaEstado,
    MesaEstadoPago,
    ResumenMesa,
    MesaConsumoResumen,
)

from app.schemas.consumo import (
    ConsumoBase,
    ConsumoCreate,
    Consumo,
    CarritoItem,
    CarritoCreate,
    ConsumoReciente,
    ConsumoHistorial,
    ConsumoItemDetalle,
)

from app.schemas.producto import (
    ProductoBase,
    ProductoCreate,
    Producto,
    ProductoValorUpdate,
    ProductoMasConsumido,
    CompraProducto,
    ReporteCategoriaMasVendida,
    ReporteIngresosPorCategoria,
)

from app.schemas.pago import (
    PagoBase,
    PagoCreate,
    PagoView,
    ReporteIngresos,
    ReporteIngresosPorMesa,
    ReporteIngresosPromedio,
    ReporteIngresosPromedioPorMesa,
    ResumenNoche,
    CuentaInfo,
)

from app.schemas.token import (
    AdminApiKeyCreate,
    AdminApiKeyInfo,
    AdminApiKeyView,
    AdminLoginRequest,
    AdminLoginResponse,
    ConfiguracionGlobalBase,
    ConfiguracionGlobal,
    ClosingTimeUpdate,
    Notificacion,
)

__all__ = [
    # Cancion
    "CancionBase", "CancionCreate", "Cancion", "CancionAdminView",
    "CancionMasCantada", "ReordenarCola", "ReporteCancionesPorUsuario",
    "ReporteCancionesPorMesa", "ReporteCancionesRechazadas", "ReporteCancionMasPedida",
    "ReporteActividadPorHora", "ReporteTiempoEsperaPromedio",
    "PlayNextResponse", "ColaView", "ColaViewExtended",
    # Usuario
    "UsuarioBase", "UsuarioCreate", "Usuario", "UsuarioConectado",
    "UsuarioPerfil", "UsuarioPublico", "UsuarioNickUpdate",
    "UsuarioMoverMesa", "UsuarioPuntosUpdate", "ReporteGastoUsuarioPorCategoria",
    "ReporteUsuarioRechazado", "HistorialUsuario", "BannedNickView", "NickUnban",
    # Mesa
    "MesaBase", "MesaCreate", "Mesa", "MesaSimple", "MesaInfo",
    "MesaEstado", "MesaEstadoPago", "ResumenMesa", "MesaConsumoResumen",
    # Consumo
    "ConsumoBase", "ConsumoCreate", "Consumo", "CarritoItem", "CarritoCreate",
    "ConsumoReciente", "ConsumoHistorial", "ConsumoItemDetalle",
    # Producto
    "ProductoBase", "ProductoCreate", "Producto", "ProductoValorUpdate",
    "ProductoMasConsumido", "CompraProducto", "ReporteCategoriaMasVendida",
    "ReporteIngresosPorCategoria",
    # Pago
    "PagoBase", "PagoCreate", "PagoView", "ReporteIngresos",
    "ReporteIngresosPorMesa", "ReporteIngresosPromedio",
    "ReporteIngresosPromedioPorMesa", "ResumenNoche", "CuentaInfo",
    # Token / Auth
    "AdminApiKeyCreate", "AdminApiKeyInfo", "AdminApiKeyView",
    "AdminLoginRequest", "AdminLoginResponse",
    "ConfiguracionGlobalBase", "ConfiguracionGlobal", "ClosingTimeUpdate",
    "Notificacion",
]
