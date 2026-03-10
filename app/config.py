"""
Compatibility shim — re-exports from app.core.config.
Use `from app.core.config import ...` for new code.
"""

from app.core.config import AppSettings, settings  # noqa: F401

__all__ = ["AppSettings", "settings"]
