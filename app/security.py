"""
Compatibility shim — re-exports from app.core.security.
Use `from app.core.security import ...` for new code.
"""

from app.core.security import (  # noqa: F401
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_HOURS,
    REFRESH_TOKEN_EXPIRE_DAYS,
    security,
    security_optional,
    create_access_token,
    create_refresh_token,
    verify_token,
    verify_token_optional,
    verify_refresh_token,
    log_admin_action,
    hash_password,
    verify_password,
)

# Keep MASTER_API_KEY for backward compat (some routers import it from here)
import os
MASTER_API_KEY = os.getenv("MASTER_API_KEY", "zxc12345")

__all__ = [
    "SECRET_KEY", "ALGORITHM", "ACCESS_TOKEN_EXPIRE_HOURS", "REFRESH_TOKEN_EXPIRE_DAYS",
    "security", "security_optional", "MASTER_API_KEY",
    "create_access_token", "create_refresh_token",
    "verify_token", "verify_token_optional", "verify_refresh_token",
    "log_admin_action", "hash_password", "verify_password",
]
