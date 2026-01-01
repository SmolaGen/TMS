"""add route_geometry to orders

Revision ID: f7d2e3b4a5c6
Revises: ada6f256ebbf
Create Date: 2026-01-01 14:15:00.000000+00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f7d2e3b4a5c6'
down_revision: Union[str, None] = 'ada6f256ebbf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('orders', sa.Column('route_geometry', sa.Text(), nullable=True, comment='Закодированная геометрия маршрута (polyline)'))

def downgrade() -> None:
    op.drop_column('orders', 'route_geometry')
