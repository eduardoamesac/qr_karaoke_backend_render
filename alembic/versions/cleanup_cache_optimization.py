"""Drop unnecessary tables and move to JSON cache

Revision ID: cleanup_cache_optimization
Revises: 
Create Date: 2026-02-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cleanup_cache_optimization'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop foreign key constraints first
    op.drop_constraint('consumos_ibfk_3', 'consumos', type_='foreignkey')
    op.drop_constraint('consumos_ibfk_4', 'consumos', type_='foreignkey')
    op.drop_constraint('pagos_ibfk_1', 'pagos', type_='foreignkey')
    op.drop_constraint('pagos_ibfk_2', 'pagos', type_='foreignkey')
    op.drop_constraint('usuario_mesa_fk', 'usuarios', type_='foreignkey')
    op.drop_constraint('cancion_usuario_fk', 'canciones', type_='foreignkey')
    op.drop_constraint('song_credits_usuario_fk', 'song_credits', type_='foreignkey')
    op.drop_constraint('song_credits_cancion_fk', 'song_credits', type_='foreignkey')
    op.drop_constraint('cuentas_mesa_fk', 'cuentas', type_='foreignkey')
    op.drop_constraint('consumos_usuario_fk', 'consumos', type_='foreignkey')
    op.drop_constraint('consumos_mesa_fk', 'consumos', type_='foreignkey')
    op.drop_constraint('consumos_producto_fk', 'consumos', type_='foreignkey')
    op.drop_constraint('pagos_usuario_fk', 'pagos', type_='foreignkey')
    
    # Drop tables
    op.drop_table('song_credits')
    op.drop_table('consumos')
    op.drop_table('cuentas')
    op.drop_table('canciones')
    op.drop_table('pagos')
    op.drop_table('mesas')
    
    # Modify usuarios table to remove mesa_id
    op.drop_column('usuarios', 'mesa_id')
    
    # Modify pagos table to add mesa_id without FK
    op.create_table(
        'pagos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('monto', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('metodo_pago', sa.String(length=50), nullable=True, server_default='Efectivo'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('mesa_id', sa.Integer(), nullable=True),
        sa.Column('usuario_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Update products table to remove consumos relationship if exists
    with op.batch_alter_table('productos', schema=None) as batch_op:
        pass  # Products table stays as-is


def downgrade() -> None:
    # This is a one-way migration
    pass
