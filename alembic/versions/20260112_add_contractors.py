"""add contractors and external_id to orders

Revision ID: add_contractors_01
Revises: add_user_role_01
Create Date: 2026-01-12 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_contractors_01'
down_revision = 'add_user_role_01'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Создаём таблицу contractors
    op.create_table(
        'contractors',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('api_key', sa.String(length=255), nullable=False),
        sa.Column('webhook_url', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_contractors_api_key'), 'contractors', ['api_key'], unique=True)
    op.create_index(op.f('ix_contractors_name'), 'contractors', ['name'], unique=True)

    # 2. Добавляем колонки в orders
    op.add_column('orders', sa.Column('contractor_id', sa.Integer(), nullable=True, comment='FK на подрядчика'))
    op.add_column('orders', sa.Column('external_id', sa.String(length=255), nullable=True, comment='ID заказа во внешней системе'))
    
    op.create_index(op.f('ix_orders_contractor_id'), 'orders', ['contractor_id'], unique=False)
    op.create_index(op.f('ix_orders_external_id'), 'orders', ['external_id'], unique=False)
    
    op.create_foreign_key(
        'fk_orders_contractor_id', 
        'orders', 'contractors', 
        ['contractor_id'], ['id'], 
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_orders_contractor_id', 'orders', type_='foreignkey')
    op.drop_index(op.f('ix_orders_external_id'), table_name='orders')
    op.drop_index(op.f('ix_orders_contractor_id'), table_name='orders')
    op.drop_column('orders', 'external_id')
    op.drop_column('orders', 'contractor_id')
    
    op.drop_index(op.f('ix_contractors_name'), table_name='contractors')
    op.drop_index(op.f('ix_contractors_api_key'), table_name='contractors')
    op.drop_table('contractors')
