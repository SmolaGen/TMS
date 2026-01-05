"""add_order_lifecycle

Revision ID: 2e807d974556
Revises: 003_partitioned_location_history
Create Date: 2025-12-31 14:30:18.503703+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '2e807d974556'
down_revision: Union[str, None] = '003_partitioned_location_history'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add driver_arrived status to order_status enum
    # PostgreSQL requires this to be done outside of a transaction for ADD VALUE
    op.execute("COMMIT")
    op.execute("ALTER TYPE order_status ADD VALUE 'driver_arrived' AFTER 'assigned'")

    # 2. Add lifecycle timestamp fields
    op.add_column('orders', sa.Column('arrived_at', sa.DateTime(), nullable=True))
    op.add_column('orders', sa.Column('started_at', sa.DateTime(), nullable=True))
    op.add_column('orders', sa.Column('end_time', sa.DateTime(), nullable=True))
    op.add_column('orders', sa.Column('cancelled_at', sa.DateTime(), nullable=True))
    op.add_column('orders', sa.Column('cancellation_reason', sa.String(length=500), nullable=True))


def downgrade() -> None:
    # 1. Remove columns
    op.drop_column('orders', 'cancellation_reason')
    op.drop_column('orders', 'cancelled_at')
    op.drop_column('orders', 'end_time')
    op.drop_column('orders', 'started_at')
    op.drop_column('orders', 'arrived_at')

    # 2. Revert enum - PostgreSQL doesn't support dropping enum values easily.
    # We leave it as is for safety, or implement a complex recreation if strictly needed.
    # In most cases for TMS, leaving an unused value in enum is acceptable.
    pass
