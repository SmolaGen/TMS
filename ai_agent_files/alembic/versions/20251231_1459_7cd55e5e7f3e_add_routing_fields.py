"""add_routing_fields

Revision ID: 7cd55e5e7f3e
Revises: 2e807d974556
Create Date: 2025-12-31 14:59:01.696634+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '7cd55e5e7f3e'
down_revision: Union[str, None] = '2e807d974556'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем поля для хранения результатов RoutingService
    op.add_column('orders', sa.Column('distance_meters', sa.Float(), nullable=True, comment="Дистанция в метрах (от OSRM)"))
    op.add_column('orders', sa.Column('duration_seconds', sa.Float(), nullable=True, comment="Время в пути в секундах (от OSRM)"))
    op.add_column('orders', sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=True, comment="Итоговая стоимость заказа"))


def downgrade() -> None:
    op.drop_column('orders', 'price')
    op.drop_column('orders', 'duration_seconds')
    op.drop_column('orders', 'distance_meters')
