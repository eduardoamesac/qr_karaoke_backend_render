"""Drop admin_logs table safely

Revision ID: drop_admin_logs_safe
Revises: 52459363f20d
Create Date: 2026-02-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'drop_admin_logs_safe'
down_revision = '52459363f20d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Drop admin_logs table"""
    # Drop the table if it exists (safely)
    try:
        op.drop_table('admin_logs')
    except Exception:
        # Table doesn't exist or already dropped
        pass


def downgrade() -> None:
    """Recreate admin_logs table"""
    op.create_table('admin_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=True),
        sa.Column('details', sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_admin_logs_action', 'admin_logs', ['action'], unique=False)
    op.create_index('ix_admin_logs_id', 'admin_logs', ['id'], unique=False)
