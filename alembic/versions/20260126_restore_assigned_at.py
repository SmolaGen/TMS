"""restore assigned_at to orders

Revision ID: 52a1b2c3d4e5
Revises: bead1875fb36
Create Date: 2026-01-26 01:25:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '52a1b2c3d4e5'
down_revision: Union[str, None] = 'bead1875fb36'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('orders', sa.Column('assigned_at', sa.DateTime(), nullable=True, comment='Время назначения водителя на заказ'))


def downgrade() -> None:
    op.drop_column('orders', 'assigned_at')
