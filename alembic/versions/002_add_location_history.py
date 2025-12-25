"""Add driver_location_history table

Revision ID: 002_add_location_history
Revises: 001_initial
Create Date: 2025-12-26

Добавляет:
- Таблицу driver_location_history для хранения истории перемещений
- Индекс для быстрого поиска по водителю и времени
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry

# revision identifiers, used by Alembic.
revision: str = "002_add_location_history"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Применение миграции."""
    
    # Создаём таблицу driver_location_history
    op.create_table(
        "driver_location_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "driver_id",
            sa.Integer(),
            sa.ForeignKey("drivers.id", ondelete="CASCADE"),
            nullable=False,
            comment="ID водителя"
        ),
        sa.Column(
            "location",
            Geometry(geometry_type="POINT", srid=4326),
            nullable=False,
            comment="Координаты (WGS84)"
        ),
        sa.Column(
            "recorded_at",
            sa.DateTime(),
            nullable=False,
            comment="Время фиксации координат водителем"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="Время записи в БД"
        ),
        sa.PrimaryKeyConstraint("id")
    )
    
    # Индекс для ускорения запросов по водителю и времени
    op.create_index(
        "ix_driver_location_time", 
        "driver_location_history", 
        ["driver_id", "recorded_at"]
    )


def downgrade() -> None:
    """Откат миграции."""
    op.drop_index("ix_driver_location_time", table_name="driver_location_history")
    op.drop_table("driver_location_history")
