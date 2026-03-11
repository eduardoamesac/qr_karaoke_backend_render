"""Consolidate missing columns — safe upgrade for existing databases

Revision ID: consolidate_missing_columns
Revises: 52459363f20d
Create Date: 2026-03-11

Adds columns and tables that may be missing in databases that were
created before the full schema was defined.  Every ADD COLUMN is
guarded by an inspector check so it is safe to run against a DB
that was just created by the base migration (52459363f20d) as well
as against older databases that already exist.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'consolidate_missing_columns'
down_revision = '52459363f20d'
branch_labels = None
depends_on = None


def _existing_columns(table_name):
    """Return a set of column names that already exist in *table_name*."""
    inspector = inspect(op.get_bind())
    return {c['name'] for c in inspector.get_columns(table_name)}


def _table_exists(table_name):
    """Return True if *table_name* already exists in the database."""
    inspector = inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def upgrade():
    # ------------------------------------------------------------------
    # canciones
    # ------------------------------------------------------------------
    if _table_exists('canciones'):
        cols = _existing_columns('canciones')
        if 'puntuacion_ia' not in cols:
            op.add_column('canciones', sa.Column('puntuacion_ia', sa.Integer(), nullable=False, server_default='0'))
        if 'is_karaoke' not in cols:
            op.add_column('canciones', sa.Column('is_karaoke', sa.Boolean(), nullable=False, server_default='1'))
        if 'approved_at' not in cols:
            op.add_column('canciones', sa.Column('approved_at', sa.DateTime(), nullable=True))

    # ------------------------------------------------------------------
    # productos
    # ------------------------------------------------------------------
    if _table_exists('productos'):
        cols = _existing_columns('productos')
        if 'costo' not in cols:
            op.add_column('productos', sa.Column('costo', sa.Numeric(10, 2), nullable=False, server_default='0'))
        if 'imagen_url' not in cols:
            op.add_column('productos', sa.Column('imagen_url', sa.String(500), nullable=True))

    # ------------------------------------------------------------------
    # consumos
    # ------------------------------------------------------------------
    if _table_exists('consumos'):
        cols = _existing_columns('consumos')
        if 'is_dispatched' not in cols:
            op.add_column('consumos', sa.Column('is_dispatched', sa.Boolean(), nullable=False, server_default='0'))
        if 'cuenta_id' not in cols:
            op.add_column('consumos', sa.Column('cuenta_id', sa.Integer(), nullable=True))

    # ------------------------------------------------------------------
    # usuarios
    # ------------------------------------------------------------------
    if _table_exists('usuarios'):
        cols = _existing_columns('usuarios')
        if 'song_credits' not in cols:
            op.add_column('usuarios', sa.Column('song_credits', sa.Integer(), nullable=False, server_default='3'))
        if 'is_active' not in cols:
            op.add_column('usuarios', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'))

    # ------------------------------------------------------------------
    # mesas
    # ------------------------------------------------------------------
    if _table_exists('mesas'):
        cols = _existing_columns('mesas')
        if 'is_active' not in cols:
            op.add_column('mesas', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'))

    # ------------------------------------------------------------------
    # Create tables that may not exist yet
    # ------------------------------------------------------------------
    if not _table_exists('cuentas'):
        op.create_table(
            'cuentas',
            sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
            sa.Column('mesa_id', sa.Integer(), nullable=False),
            sa.Column('estado', sa.String(20), nullable=False, server_default='abierta'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('closed_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['mesa_id'], ['mesas.id'], name='fk_cuentas_mesa_id'),
        )

    if not _table_exists('pagos'):
        op.create_table(
            'pagos',
            sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
            sa.Column('mesa_id', sa.Integer(), nullable=False),
            sa.Column('monto', sa.Numeric(10, 2), nullable=False),
            sa.Column('metodo', sa.String(50), nullable=False, server_default='efectivo'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['mesa_id'], ['mesas.id'], name='fk_pagos_mesa_id'),
        )

    if not _table_exists('configuracion_global'):
        op.create_table(
            'configuracion_global',
            sa.Column('id', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('karaoke_activo', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('hora_cierre', sa.String(10), nullable=False, server_default='02:00'),
            sa.Column('max_canciones_por_usuario', sa.Integer(), nullable=False, server_default='5'),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )

    if not _table_exists('banned_nicks'):
        op.create_table(
            'banned_nicks',
            sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
            sa.Column('nick', sa.String(100), nullable=False),
            sa.Column('banned_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('nick', name='uq_banned_nicks_nick'),
        )

    if not _table_exists('admin_logs'):
        op.create_table(
            'admin_logs',
            sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
            sa.Column('timestamp', sa.DateTime(), nullable=True),
            sa.Column('action', sa.String(100), nullable=True),
            sa.Column('details', sa.String(1000), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )

    if not _table_exists('admin_api_keys'):
        op.create_table(
            'admin_api_keys',
            sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
            sa.Column('key', sa.String(200), nullable=False),
            sa.Column('description', sa.String(200), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('last_used', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('key', name='uq_admin_api_keys_key'),
        )


def downgrade():
    # Downgrade is intentionally a no-op: removing columns from existing
    # databases could cause data loss and is not safe to automate.
    pass
