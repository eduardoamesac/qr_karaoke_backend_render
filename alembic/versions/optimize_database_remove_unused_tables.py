"""Optimize database - remove unused tables and consolidate banned_nicks into usuarios

Revision ID: optimize_db_2025_02_20
Revises: 52459363f20d
Create Date: 2025-02-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'optimize_db_2025_02_20'
down_revision = '52459363f20d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Agregar columna is_banned a usuarios
    op.add_column('usuarios', sa.Column('is_banned', sa.Boolean(), server_default='0', nullable=False))
    
    # 2. Migrar datos de banned_nicks a usuarios (si existen)
    # Primero, marcar todos los usuarios cuyos nicks están en banned_nicks
    op.execute("""
        UPDATE usuarios 
        SET is_banned = 1 
        WHERE nick IN (SELECT nick FROM banned_nicks)
    """)
    
    # 3. Eliminar tabla banned_nicks
    op.drop_table('banned_nicks')
    
    # 4. Eliminar tabla admin_logs
    op.drop_table('admin_logs')
    
    # 5. Eliminar tabla configuracion_global
    op.drop_table('configuracion_global')


def downgrade() -> None:
    # 1. Recrear tabla configuracion_global
    op.create_table('configuracion_global',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('clave', sa.String(length=100), nullable=False),
        sa.Column('valor', sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('clave')
    )
    
    # 2. Recrear tabla admin_logs
    op.create_table('admin_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=True),
        sa.Column('details', sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_admin_logs_action', 'admin_logs', ['action'], unique=False)
    op.create_index('ix_admin_logs_id', 'admin_logs', ['id'], unique=False)
    
    # 3. Recrear tabla banned_nicks
    op.create_table('banned_nicks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nick', sa.String(length=100), nullable=True),
        sa.Column('banned_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ix_banned_nicks_nick', 'nick')
    )
    op.create_index('ix_banned_nicks_id', 'banned_nicks', ['id'], unique=False)
    op.create_index('ix_banned_nicks_nick', 'banned_nicks', ['nick'], unique=True)
    
    # 4. Migrar datos de vuelta: crear registros en banned_nicks desde usuarios.is_banned
    op.execute("""
        INSERT INTO banned_nicks (nick, banned_at)
        SELECT nick, NOW() FROM usuarios WHERE is_banned = 1
    """)
    
    # 5. Eliminar columna is_banned de usuarios
    op.drop_column('usuarios', 'is_banned')
