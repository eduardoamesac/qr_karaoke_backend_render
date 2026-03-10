"""
Compatibility shim — re-exports from app.db.crud.
Use `from app.db.crud import ...` or `from app.db import crud` for new code.
"""

from app.db.crud import *  # noqa: F401, F403
from app.db.crud import __all__
