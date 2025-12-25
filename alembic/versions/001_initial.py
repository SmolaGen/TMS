"""Initial migration - Create drivers and orders tables

Revision ID: 001
Revises: 
Create Date: 2024-12-26

Создаёт:
- Расширения btree_gist и postgis
- Enum типы для статусов
- Таблицы drivers и orders
- Exclusion Constraint для блокировки пересечения заказов по времени
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Применение миграции.
    
    Важно: Порядок операций критичен!
    1. btree_gist ДОЛЖЕН быть создан ДО создания exclusion constraint с integer
    2. postgis ДОЛЖЕН быть создан ДО создания колонок с типом Geometry
    """
    
    # 1. Создаём необходимые расширения PostgreSQL
    # btree_gist - нужен для использования оператора = с integer внутри GiST индекса
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist;")
    
    # postgis - нужен для работы с географическими данными
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    
    # 2. Создаём ENUM типы (идемпотентно)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'driver_status') THEN
                CREATE TYPE driver_status AS ENUM ('available', 'busy', 'offline');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'order_status') THEN
                CREATE TYPE order_status AS ENUM ('pending', 'assigned', 'in_progress', 'completed', 'cancelled');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'order_priority') THEN
                CREATE TYPE order_priority AS ENUM ('low', 'normal', 'high', 'urgent');
            END IF;
        END $$;
    """)
    
    # 3. Создаём таблицу drivers
    op.create_table(
        "drivers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "telegram_id",
            sa.BigInteger(),
            nullable=False,
            unique=True,
            comment="Telegram user ID"
        ),
        sa.Column(
            "name",
            sa.String(length=255),
            nullable=False,
            comment="Имя водителя"
        ),
        sa.Column(
            "phone",
            sa.String(length=20),
            nullable=True,
            comment="Номер телефона"
        ),
        sa.Column(
            "status",
            sa.Enum("available", "busy", "offline", name="driver_status", create_type=False),
            server_default="offline",
            nullable=False,
            comment="Текущий статус"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False
        ),
        sa.PrimaryKeyConstraint("id")
    )
    
    # Индекс для быстрого поиска по telegram_id
    op.create_index("ix_drivers_telegram_id", "drivers", ["telegram_id"], unique=True)
    
    # 4. Создаём таблицу orders
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "driver_id",
            sa.Integer(),
            sa.ForeignKey("drivers.id", ondelete="SET NULL"),
            nullable=True,
            comment="FK на водителя"
        ),
        sa.Column(
            "status",
            sa.Enum("pending", "assigned", "in_progress", "completed", "cancelled", name="order_status", create_type=False),
            server_default="pending",
            nullable=False,
            comment="Статус заказа"
        ),
        sa.Column(
            "priority",
            sa.Enum("low", "normal", "high", "urgent", name="order_priority", create_type=False),
            server_default="normal",
            nullable=False,
            comment="Приоритет заказа"
        ),
        # Временной интервал выполнения заказа
        # Используем tstzrange для хранения диапазона времени с таймзоной
        sa.Column(
            "time_range",
            sa.dialects.postgresql.TSTZRANGE(),
            nullable=True,
            comment="Временной интервал выполнения (с таймзоной)"
        ),
        sa.Column(
            "pickup_location",
            Geometry(geometry_type="POINT", srid=4326),
            nullable=True,
            comment="Координаты точки погрузки (WGS84)"
        ),
        sa.Column(
            "dropoff_location",
            Geometry(geometry_type="POINT", srid=4326),
            nullable=True,
            comment="Координаты точки выгрузки (WGS84)"
        ),
        sa.Column(
            "comment",
            sa.Text(),
            nullable=True,
            comment="Комментарий к заказу"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False
        ),
        sa.PrimaryKeyConstraint("id")
    )
    
    # Индексы
    op.create_index("ix_orders_driver_id", "orders", ["driver_id"])
    op.create_index("ix_orders_status_priority", "orders", ["status", "priority"])
    
    # 5. GiST индекс для time_range (нужен для exclusion constraint)
    op.execute("""
        CREATE INDEX ix_orders_time_range_gist ON orders 
        USING gist (time_range);
    """)
    
    # 6. Exclusion Constraint для предотвращения пересечения заказов
    # Гарантирует, что один водитель НЕ МОЖЕТ иметь два заказа
    # с пересекающимися временными интервалами, ЕСЛИ заказы активны
    # 
    # driver_id WITH = : один и тот же водитель
    # time_range WITH && : временные интервалы пересекаются
    # WHERE : только для активных заказов (не completed/cancelled)
    op.execute("""
        ALTER TABLE orders ADD CONSTRAINT no_driver_time_overlap
        EXCLUDE USING gist (
            driver_id WITH =,
            time_range WITH &&
        )
        WHERE (
            driver_id IS NOT NULL 
            AND status NOT IN ('completed', 'cancelled')
        );
    """)


def downgrade() -> None:
    """Откат миграции."""
    
    # Удаляем constraint
    op.execute("ALTER TABLE orders DROP CONSTRAINT IF EXISTS no_driver_time_overlap;")
    
    # Удаляем индексы
    op.execute("DROP INDEX IF EXISTS ix_orders_time_range_gist;")
    op.drop_index("ix_orders_status_priority", table_name="orders")
    op.drop_index("ix_orders_driver_id", table_name="orders")
    
    # Удаляем таблицы
    op.drop_table("orders")
    
    op.drop_index("ix_drivers_telegram_id", table_name="drivers")
    op.drop_table("drivers")
    
    # Удаляем ENUM типы
    op.execute("DROP TYPE IF EXISTS order_priority;")
    op.execute("DROP TYPE IF EXISTS order_status;")
    op.execute("DROP TYPE IF EXISTS driver_status;")
    
    # Расширения обычно не удаляются, т.к. могут использоваться другими
