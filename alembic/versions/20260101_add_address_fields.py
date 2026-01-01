"""add order address and customer fields

Revision ID: add_address_fields_01
Revises: f7d2e3b4a5c6_add_route_geometry
Create Date: 2026-01-01 16:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_address_fields_01'
down_revision = 'f7d2e3b4a5c6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add address and customer fields to orders table
    op.add_column('orders', sa.Column('pickup_address', sa.Text(), nullable=True))
    op.add_column('orders', sa.Column('dropoff_address', sa.Text(), nullable=True))
    op.add_column('orders', sa.Column('customer_phone', sa.String(50), nullable=True))
    op.add_column('orders', sa.Column('customer_name', sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column('orders', 'customer_name')
    op.drop_column('orders', 'customer_phone')
    op.drop_column('orders', 'dropoff_address')
    op.drop_column('orders', 'pickup_address')
