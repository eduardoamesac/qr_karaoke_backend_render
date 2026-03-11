"""Add missing columns to usuarios table

Revision ID: add_missing_usuario_columns
Revises: consolidate_missing_columns
Create Date: 2026-03-11

Agrega las columnas que le faltaban a la tabla `usuarios` y que el modelo
SQLAlchemy ya define.  Cada ALTER TABLE está protegido por una comprobación
previa del inspector, por lo que es seguro ejecutar esta migración contra
una base de datos que ya tenga alguna de las columnas.

Columnas añadidas:
  - last_active       DATETIME,  nullable
  - is_silenced       BOOLEAN,   default False
  - is_banned         BOOLEAN,   default False
  - credits_added_at  DATETIME,  nullable
  - last_song_added_at DATETIME, nullable
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# ============================================================
# Identificadores de revisión
# ============================================================
revision = 'add_missing_usuario_columns'
down_revision = 'consolidate_missing_columns'
branch_labels = None
depends_on = None


def _existing_columns(table_name):
    """Devuelve el conjunto de nombres de columna que ya existen en *table_name*."""
    inspector = inspect(op.get_bind())
    return {c['name'] for c in inspector.get_columns(table_name)}


def upgrade():
    # ============================================================
    # usuarios — columnas faltantes
    # ============================================================
    cols = _existing_columns('usuarios')

    if 'last_active' not in cols:
        op.add_column(
            'usuarios',
            sa.Column('last_active', sa.DateTime(), nullable=True),
        )

    if 'is_silenced' not in cols:
        op.add_column(
            'usuarios',
            sa.Column('is_silenced', sa.Boolean(), nullable=False, server_default='0'),
        )

    if 'is_banned' not in cols:
        op.add_column(
            'usuarios',
            sa.Column('is_banned', sa.Boolean(), nullable=False, server_default='0'),
        )

    if 'credits_added_at' not in cols:
        op.add_column(
            'usuarios',
            sa.Column('credits_added_at', sa.DateTime(), nullable=True),
        )

    if 'last_song_added_at' not in cols:
        op.add_column(
            'usuarios',
            sa.Column('last_song_added_at', sa.DateTime(), nullable=True),
        )


def downgrade():
    # ============================================================
    # Se usa batch_alter_table para compatibilidad con SQLite
    # (SQLite no soporta DROP COLUMN directamente).
    # Se comprueba la existencia de cada columna antes de eliminarla
    # para que el downgrade sea idempotente.
    # ============================================================
    cols = _existing_columns('usuarios')
    columns_to_drop = [
        'last_song_added_at',
        'credits_added_at',
        'is_banned',
        'is_silenced',
        'last_active',
    ]
    # Solo hace el batch si hay al menos una columna que eliminar
    if any(c in cols for c in columns_to_drop):
        with op.batch_alter_table('usuarios') as batch_op:
            for col in columns_to_drop:
                if col in cols:
                    batch_op.drop_column(col)
