from fastapi import APIRouter
from pydantic import BaseModel
from settings_storage import load_settings, save_settings

router = APIRouter(prefix="/api/v1/admin/settings", tags=["Admin Settings"])


# ============= MODELOS =============
class GeneralSettings(BaseModel):
    app_name: str
    theme: str
    enable_notifications: bool


class ClosingTime(BaseModel):
    closing_hour: int
    closing_minute: int


class LazyQueueConfig(BaseModel):
    """Configuración para la entrada de canciones a la cola lazy"""
    credit_multiplier: float  # Multiplicador del crédito inicial (ej: 1.0, 1.5, 2.0)
    decay_rate: int  # Créditos que decaen por minuto (ej: 100)
    allow_unrestricted: bool  # Si True, permite agregar canciones sin límite
    max_concurrent_songs: int  # Máximo de canciones que puede agregar un usuario de una vez


# ============= ENDPOINTS =============

@router.get("/")
def get_all_settings():
    """Obtiene toda la configuración"""
    return load_settings()


@router.get("/general")
def get_general_settings():
    """Obtiene la configuración general (nombre, tema, notificaciones)"""
    settings = load_settings()
    return {
        "app_name": settings.get("app_name", "QR Karaoke"),
        "theme": settings.get("theme", "dark"),
        "enable_notifications": settings.get("enable_notifications", True)
    }


@router.post("/general")
def update_general_settings(data: GeneralSettings):
    """Actualiza la configuración general"""
    settings = load_settings()
    
    settings["app_name"] = data.app_name
    settings["theme"] = data.theme
    settings["enable_notifications"] = data.enable_notifications
    
    save_settings(settings)
    
    return {
        "status": "success",
        "message": "General settings updated",
        "data": {
            "app_name": data.app_name,
            "theme": data.theme,
            "enable_notifications": data.enable_notifications
        }
    }


@router.post("/closing-time")
def update_closing_time(data: ClosingTime):
    """Actualiza la hora de cierre"""
    settings = load_settings()
    
    # Validar horas válidas
    if not (0 <= data.closing_hour <= 23):
        return {"status": "error", "message": "Hora debe estar entre 0 y 23"}
    
    if not (0 <= data.closing_minute <= 59):
        return {"status": "error", "message": "Minuto debe estar entre 0 y 59"}
    
    settings["closing_hour"] = data.closing_hour
    settings["closing_minute"] = data.closing_minute
    
    save_settings(settings)
    
    return {
        "status": "success",
        "message": "Closing time updated",
        "data": {
            "closing_hour": data.closing_hour,
            "closing_minute": data.closing_minute
        }
    }


@router.get("/closing-time")
def get_closing_time():
    """Obtiene la hora de cierre actual"""
    settings = load_settings()
    return {
        "closing_hour": settings.get("closing_hour", 3),
        "closing_minute": settings.get("closing_minute", 0)
    }


@router.get("/lazy-queue")
def get_lazy_queue_config():
    """Obtiene la configuración de la cola lazy"""
    settings = load_settings()
    return {
        "credit_multiplier": settings.get("lazy_queue_credit_multiplier", 1.0),
        "decay_rate": settings.get("lazy_queue_decay_rate", 100),
        "allow_unrestricted": settings.get("lazy_queue_allow_unrestricted", False),
        "max_concurrent_songs": settings.get("lazy_queue_max_concurrent_songs", 10)
    }


@router.post("/lazy-queue")
def update_lazy_queue_config(data: LazyQueueConfig):
    """
    Actualiza la configuración de la cola lazy.
    
    Parámetros:
    - credit_multiplier: Multiplicador del crédito inicial (ej: 1.0 = valor del gasto)
    - decay_rate: Créditos que decaen por minuto (ej: 100)
    - allow_unrestricted: Si True, permite agregar canciones sin restricción de créditos
    - max_concurrent_songs: Límite de canciones concurrentes por usuario
    """
    settings = load_settings()
    
    # Validar valores razonables
    if data.credit_multiplier <= 0:
        return {"status": "error", "message": "El multiplicador debe ser mayor a 0"}
    
    if data.decay_rate < 0:
        return {"status": "error", "message": "La tasa de decaimiento no puede ser negativa"}
    
    if data.max_concurrent_songs < 1:
        return {"status": "error", "message": "El máximo de canciones debe ser al menos 1"}
    
    settings["lazy_queue_credit_multiplier"] = data.credit_multiplier
    settings["lazy_queue_decay_rate"] = data.decay_rate
    settings["lazy_queue_allow_unrestricted"] = data.allow_unrestricted
    settings["lazy_queue_max_concurrent_songs"] = data.max_concurrent_songs
    
    save_settings(settings)
    
    return {
        "status": "success",
        "message": "Lazy queue configuration updated",
        "data": {
            "credit_multiplier": data.credit_multiplier,
            "decay_rate": data.decay_rate,
            "allow_unrestricted": data.allow_unrestricted,
            "max_concurrent_songs": data.max_concurrent_songs
        }
    }
