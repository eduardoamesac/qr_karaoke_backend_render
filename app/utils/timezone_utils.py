from datetime import datetime
import pytz

BOGOTA_TZ = pytz.timezone('America/Bogota')


def now_bogota():
    """Returns the current date and time in the Bogotá timezone."""
    return datetime.now(BOGOTA_TZ)


def to_bogota(dt):
    """Converts a datetime to the Bogotá timezone."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    return dt.astimezone(BOGOTA_TZ)


def ensure_aware(dt):
    """
    Ensures a datetime is timezone-aware.
    If naive, treats it as UTC and converts to Bogotá.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    return dt.astimezone(BOGOTA_TZ)


def safe_datetime_diff(dt_aware, dt_possibly_naive):
    """
    Safely calculates the difference between two datetimes,
    handling the case where one is naive and the other is aware.

    Returns the difference in seconds.
    """
    if dt_possibly_naive is None or dt_aware is None:
        return 0

    dt_aware_target = ensure_aware(dt_aware)
    dt_other = ensure_aware(dt_possibly_naive)

    return (dt_aware_target - dt_other).total_seconds()
