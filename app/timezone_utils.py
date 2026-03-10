from datetime import datetime
import pytz

# Zona horaria de Bogotá, Colombia
BOGOTA_TZ = pytz.timezone('America/Bogota')

def now_bogota():
    """Retorna la fecha y hora actual en zona horaria de Bogotá"""
    return datetime.now(BOGOTA_TZ)

def to_bogota(dt):
    """Convierte un datetime a zona horaria de Bogotá"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Si no tiene timezone, asumimos que es UTC
        dt = pytz.utc.localize(dt)
    return dt.astimezone(BOGOTA_TZ)

def ensure_aware(dt):
    """
    Asegura que un datetime sea aware (con timezone).
    Si es naive, lo convierte como UTC y luego a Bogotá.
    Si ya es aware, lo convierte a Bogotá.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Es naive, asumir UTC
        dt = pytz.utc.localize(dt)
    return dt.astimezone(BOGOTA_TZ)

def safe_datetime_diff(dt_aware, dt_possibly_naive):
    """
    Calcula la diferencia segura entre dos datetimes,
    manejando el caso donde uno es naive y otro es aware.
    
    Retorna la diferencia en segundos.
    """
    if dt_possibly_naive is None or dt_aware is None:
        return 0
    
    # Convertir ambos a aware si es necesario
    dt_aware_target = ensure_aware(dt_aware)
    dt_other = ensure_aware(dt_possibly_naive)
    
    return (dt_aware_target - dt_other).total_seconds()
