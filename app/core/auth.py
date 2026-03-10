import os
from typing import Optional
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from fastapi import Depends

# Claves de API header
api_key_header = APIKeyHeader(name="X-API-Key")
api_key_header_optional = APIKeyHeader(name="X-API-Key", auto_error=False)

# --- Clave Maestra ---
MASTER_API_KEY = os.getenv("MASTER_API_KEY", "zxc12345")


def get_db():
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def api_key_auth(api_key: str = Security(api_key_header), db: Session = Depends(get_db)):
    """
    Dependencia que valida la API Key.
    Verifica si la clave coincide con la MAESTRA o si es válida en la base de datos.
    """
    if api_key == MASTER_API_KEY:
        return api_key

    from app.db.crud import get_admin_api_key
    db_api_key = get_admin_api_key(db, key=api_key)
    if not db_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Clave de API inválida o ausente."
        )
    return api_key


def optional_api_key_auth(
    api_key: Optional[str] = Security(api_key_header_optional),
    db: Session = Depends(get_db)
) -> Optional[str]:
    """
    Variante de validación de API key que no falla si no se proporciona la cabecera.
    """
    if not api_key:
        return None

    if api_key == MASTER_API_KEY:
        return api_key

    from app.db.crud import get_admin_api_key
    db_api_key = get_admin_api_key(db, key=api_key)
    if not db_api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Clave de API inválida o ausente.")

    return api_key
