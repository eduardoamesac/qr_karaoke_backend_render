"""
Compatibility shim — re-exports from app.core.security and app.core.auth.
Use `from app.core.auth import ...` or `from app.core.security import ...` for new code.
"""

from app.core.security import (  # noqa: F401
    create_access_token,
    create_refresh_token,
    verify_token,
    verify_token_optional,
    verify_refresh_token,
    log_admin_action,
)

from app.core.auth import (  # noqa: F401
    api_key_auth,
    optional_api_key_auth,
    MASTER_API_KEY,
    get_db,
)

__all__ = [
    "create_access_token", "create_refresh_token",
    "verify_token", "verify_token_optional", "verify_refresh_token",
    "log_admin_action",
    "api_key_auth", "optional_api_key_auth",
    "MASTER_API_KEY", "get_db",
]
