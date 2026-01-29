"""Add scheduling models - driver availability and order templates

Revision ID: b3ece8e67413
Revises: 4c7e7ab58c4b
Create Date: 2026-01-29 17:16:48.780229+00:00

Создаёт:
- ENUM тип availability_type для типов недоступности водителей
- Таблицу driver_availability для отслеживания отпусков и выходных
- Таблицу order_templates для шаблонов повторяющихся заказов
- Поле scheduled_date в таблице orders для планирования заказов
- Exclusion Constraint для предотвращения пересечения периодов недоступности
"""

from typing import Sequence, Union

import sqlalchemy as sa
import geoalchemy2
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b3ece8e67413'
down_revision: Union[str, None] = '4c7e7ab58c4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Применение миграции.

    Создаёт модели для планирования:
    1. driver_availability - периоды недоступности водителей
    2. order_templates - шаблоны повторяющихся заказов
    3. scheduled_date - поле для запланированной даты заказа
    """

    # 1. Создаём таблицу driver_availability
    # ENUM тип availability_type будет создан автоматически при создании таблицы
    op.create_table(
        'driver_availability',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            'driver_id',
            sa.Integer(),
            nullable=False,
            comment='FK на водителя'
        ),
        sa.Column(
            'availability_type',
            sa.Enum('vacation', 'sick_leave', 'day_off', 'personal', 'other',
                   name='availability_type'),
            server_default=sa.text("'other'"),
            nullable=False,
            comment='Тип недоступности'
        ),
        sa.Column(
            'time_range',
            postgresql.TSTZRANGE(),
            nullable=False,
            comment='Временной интервал недоступности (с таймзоной)'
        ),
        sa.Column(
            'description',
            sa.Text(),
            nullable=True,
            comment='Описание/причина недоступности'
        ),
        sa.Column(
            'created_at',
            sa.DateTime(),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False
        ),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Индекс для быстрого поиска по водителю
    op.create_index(
        'ix_driver_availability_driver_id',
        'driver_availability',
        ['driver_id'],
        unique=False
    )

    # Exclusion Constraint для предотвращения пересечения периодов недоступности
    # Гарантирует, что у одного водителя не может быть пересекающихся периодов
    op.execute("""
        ALTER TABLE driver_availability ADD CONSTRAINT no_driver_availability_overlap
        EXCLUDE USING gist (
            driver_id WITH =,
            time_range WITH &&
        );
    """)

    # 2. Создаём таблицу order_templates
    op.create_table(
        'order_templates',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            'name',
            sa.String(length=255),
            nullable=False,
            comment='Название шаблона'
        ),
        sa.Column(
            'contractor_id',
            sa.Integer(),
            nullable=True,
            comment='FK на подрядчика-владельца шаблона'
        ),
        sa.Column(
            'priority',
            postgresql.ENUM('low', 'normal', 'high', 'urgent', name='order_priority', create_type=False),
            server_default=sa.text("'normal'"),
            nullable=False,
            comment='Приоритет заказа по умолчанию'
        ),
        sa.Column(
            'pickup_location',
            Geometry(geometry_type='POINT', srid=4326),
            nullable=True,
            comment='Координаты точки погрузки (WGS84)'
        ),
        sa.Column(
            'dropoff_location',
            Geometry(geometry_type='POINT', srid=4326),
            nullable=True,
            comment='Координаты точки выгрузки (WGS84)'
        ),
        sa.Column('pickup_address', sa.String(length=500), nullable=True),
        sa.Column('dropoff_address', sa.String(length=500), nullable=True),
        sa.Column('customer_phone', sa.String(length=20), nullable=True),
        sa.Column('customer_name', sa.String(length=255), nullable=True),
        sa.Column(
            'customer_telegram_id',
            sa.BigInteger(),
            nullable=True,
            comment='Telegram ID заказчика для уведомлений'
        ),
        sa.Column(
            'customer_webhook_url',
            sa.String(length=500),
            nullable=True,
            comment='URL вебхука заказчика для уведомлений'
        ),
        sa.Column(
            'price',
            sa.Numeric(precision=10, scale=2),
            nullable=True,
            comment='Стоимость заказа по умолчанию'
        ),
        sa.Column(
            'comment',
            sa.Text(),
            nullable=True,
            comment='Комментарий к шаблону'
        ),
        sa.Column(
            'is_active',
            sa.Boolean(),
            server_default=sa.text('true'),
            nullable=False,
            comment='Флаг активности шаблона'
        ),
        sa.Column(
            'created_at',
            sa.DateTime(),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False
        ),
        sa.ForeignKeyConstraint(['contractor_id'], ['contractors.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Индексы для order_templates
    op.create_index(
        'ix_order_templates_contractor',
        'order_templates',
        ['contractor_id'],
        unique=False
    )
    op.create_index(
        'ix_order_templates_customer_telegram_id',
        'order_templates',
        ['customer_telegram_id'],
        unique=False
    )

    # GiST индексы для географических полей (для быстрого поиска по координатам)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_order_templates_pickup_location ON order_templates
        USING gist (pickup_location);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_order_templates_dropoff_location ON order_templates
        USING gist (dropoff_location);
    """)

    # 3. Добавляем поле scheduled_date в таблицу orders
    op.add_column(
        'orders',
        sa.Column(
            'scheduled_date',
            sa.DateTime(),
            nullable=True,
            comment='Запланированная дата выполнения заказа'
        )
    )


def downgrade() -> None:
    """
    Откат миграции.

    Удаляет все созданные таблицы, индексы и поля.
    """

    # 1. Удаляем поле scheduled_date из orders
    op.drop_column('orders', 'scheduled_date')

    # 2. Удаляем таблицу order_templates и её индексы
    op.execute("DROP INDEX IF EXISTS idx_order_templates_dropoff_location;")
    op.execute("DROP INDEX IF EXISTS idx_order_templates_pickup_location;")
    op.drop_index('ix_order_templates_customer_telegram_id', table_name='order_templates')
    op.drop_index('ix_order_templates_contractor', table_name='order_templates')
    op.drop_table('order_templates')

    # 3. Удаляем таблицу driver_availability
    # Сначала удаляем exclusion constraint, затем индекс и таблицу
    op.execute("ALTER TABLE driver_availability DROP CONSTRAINT IF EXISTS no_driver_availability_overlap;")
    op.drop_index('ix_driver_availability_driver_id', table_name='driver_availability')
    op.drop_table('driver_availability')

    # 4. Удаляем ENUM тип availability_type
    op.execute("DROP TYPE IF EXISTS availability_type;")
