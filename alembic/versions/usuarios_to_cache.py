"""Move usuarios from DB to JSON cache (no schema change needed)

Revision ID: usuarios_to_cache
Revises: consolidate_missing_columns
Create Date: 2026-03-29

Session users (mesas + usuarios) are now managed entirely in JSON cache.
- The `usuarios` DB table is kept for backwards-compatibility but is no longer
  written to for new sessions.
- The `mesas` DB table is kept as a shadow record for FK integrity (cuentas → mesas).
- On payment completion OR mesa deletion, user session data is cleared from cache.

No DDL changes required for this migration.
"""
from alembic import op
import sqlalchemy as sa

revision = 'usuarios_to_cache'
down_revision = 'consolidate_missing_columns'
branch_labels = None
depends_on = None


def upgrade():
    # No schema changes — users now live in cache/usuarios.json
    # The usuarios table remains but is no longer the source of truth
    pass


def downgrade():
    # No schema changes to revert
    pass

