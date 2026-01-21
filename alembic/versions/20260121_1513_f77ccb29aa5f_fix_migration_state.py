"""fix migration state

Revision ID: f77ccb29aa5f
Revises: 86621c51e171
Create Date: 2026-01-21 15:13:04.665623+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
import geoalchemy2
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f77ccb29aa5f'
down_revision: Union[str, None] = '86621c51e171'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
