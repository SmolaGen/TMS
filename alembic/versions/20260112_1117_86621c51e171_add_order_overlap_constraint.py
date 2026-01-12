"""add_order_overlap_constraint

Revision ID: 86621c51e171
Revises: add_contractors_01
Create Date: 2026-01-12 11:17:26.986212+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
import geoalchemy2
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '86621c51e171'
down_revision: Union[str, None] = 'add_contractors_01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создаем расширение btree_gist для поддержки GIST индексов
    op.execute('CREATE EXTENSION IF NOT EXISTS btree_gist')
    
    # Создаем ExclusionConstraint для предотвращения пересечений заказов
    # Constraint гарантирует, что один водитель не может иметь пересекающиеся по времени заказы
    op.execute('''
        ALTER TABLE orders ADD CONSTRAINT no_driver_time_overlap
        EXCLUDE USING gist (
            driver_id WITH =,
            time_range WITH &&
        )
        WHERE (driver_id IS NOT NULL AND status NOT IN ('completed', 'cancelled'))
    ''')


def downgrade() -> None:
    # Удаляем constraint
    op.execute('ALTER TABLE orders DROP CONSTRAINT IF EXISTS no_driver_time_overlap')
    
    # Примечание: не удаляем btree_gist extension, т.к. она может использоваться другими объектами
