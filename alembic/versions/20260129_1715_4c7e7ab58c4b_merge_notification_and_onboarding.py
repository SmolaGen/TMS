"""merge_notification_and_onboarding

Revision ID: 4c7e7ab58c4b
Revises: 9c4d8a7e2b1f, 46ecd9dfaa2c
Create Date: 2026-01-29 17:15:59.157921+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
import geoalchemy2
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '4c7e7ab58c4b'
down_revision: Union[str, None] = ('9c4d8a7e2b1f', '46ecd9dfaa2c')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
