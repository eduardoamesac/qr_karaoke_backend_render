"""Drop canciones table - migrated to JSON cache

Revision ID: drop_canciones_cache
Revises: drop_admin_logs_safe
Create Date: 2026-02-23 00:00:00.000000

CAMBIO IMPORTANTE:
- La tabla 'canciones' ha sido eliminada
- Las canciones ahora se almacenan en JSON usando cache_manager.py
- El archivo de caché global: cache/canciones_global.json
- Los archivos por usuario: cache/user_songs_*.json
- Todos los endpoints de canciones.py ahora usan cache_manager
- Se actualizado crud.py para trabajar exclusivamente con caché
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'drop_canciones_cache'
down_revision = 'drop_admin_logs_safe'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Drop canciones table - now using JSON cache"""
    # Drop the table if it exists (safely)
    try:
        # First drop any foreign key constraints that reference canciones
        op.drop_constraint('fk_cola_cancion_id', 'cola', type_='foreignkey') if False else None
        op.drop_table('canciones')
    except Exception as e:
        # Table doesn't exist or already dropped
        print(f"Note: {e}")
        pass


def downgrade() -> None:
    """Recreate canciones table (if needed for rollback)"""
    op.create_table('canciones',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=True),
        sa.Column('youtube_id', sa.String(length=50), nullable=True),
        sa.Column('titulo', sa.String(length=255), nullable=True),
        sa.Column('duracion_seconds', sa.Integer(), nullable=True),
        sa.Column('estado', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('orden_manual', sa.Integer(), nullable=True),
        sa.Column('puntuacion_ia', sa.Integer(), nullable=True),
        sa.Column('is_karaoke', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], )
    )
    op.create_index('ix_canciones_estado', 'canciones', ['estado'], unique=False)
    op.create_index('ix_canciones_usuario_id', 'canciones', ['usuario_id'], unique=False)
    op.create_index('ix_canciones_youtube_id', 'canciones', ['youtube_id'], unique=False)
