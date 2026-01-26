"""add route models

Revision ID: add_route_models_01
Revises: f77ccb29aa5f
Create Date: 2026-01-27 03:06:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import geoalchemy2
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import ENUM


# revision identifiers, used by Alembic.
revision: str = 'add_route_models_01'
down_revision: Union[str, None] = 'bead1875fb36'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Создаём ENUM типы (если они ещё не существуют)
    # PostgreSQL требует это делать вне транзакции для CREATE TYPE
    op.execute("COMMIT")

    # route_status enum
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'route_status') THEN
                CREATE TYPE route_status AS ENUM ('planned', 'in_progress', 'completed', 'cancelled');
            END IF;
        END $$;
    """)

    # route_optimization_type enum
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'route_optimization_type') THEN
                CREATE TYPE route_optimization_type AS ENUM ('time', 'distance');
            END IF;
        END $$;
    """)

    # route_stop_type enum
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'route_stop_type') THEN
                CREATE TYPE route_stop_type AS ENUM ('pickup', 'dropoff', 'break', 'fuel', 'other');
            END IF;
        END $$;
    """)

    # route_change_type enum
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'route_change_type') THEN
                CREATE TYPE route_change_type AS ENUM ('created', 'status_changed', 'driver_assigned', 'point_added', 'point_removed', 'point_reordered', 'optimized', 'cancelled', 'completed');
            END IF;
        END $$;
    """)

    # 2. Создаём таблицу routes
    op.create_table(
        'routes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=True, comment='FK на водителя'),
        sa.Column('status', ENUM(name='route_status', create_type=False), server_default=sa.text("'planned'"), nullable=False, comment='Статус маршрута'),
        sa.Column('optimization_type', ENUM(name='route_optimization_type', create_type=False), server_default=sa.text("'time'"), nullable=False, comment='Тип оптимизации (время/расстояние)'),
        sa.Column('total_distance_meters', sa.Float(), nullable=True, comment='Общая дистанция маршрута в метрах'),
        sa.Column('total_duration_seconds', sa.Float(), nullable=True, comment='Общее время маршрута в секундах'),
        sa.Column('started_at', sa.DateTime(), nullable=True, comment='Время начала выполнения маршрута'),
        sa.Column('completed_at', sa.DateTime(), nullable=True, comment='Время завершения маршрута'),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True, comment='Время отмены маршрута'),
        sa.Column('cancellation_reason', sa.Text(), nullable=True, comment='Причина отмены маршрута'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_routes_driver_id'), 'routes', ['driver_id'], unique=False)
    op.create_foreign_key(
        'fk_routes_driver_id',
        'routes', 'drivers',
        ['driver_id'], ['id'],
        ondelete='SET NULL'
    )

    # 3. Создаём таблицу route_points
    op.create_table(
        'route_points',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('route_id', sa.Integer(), nullable=False, comment='FK на маршрут'),
        sa.Column('sequence', sa.Integer(), nullable=False, comment='Порядковый номер точки в маршруте'),
        sa.Column('location', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326), nullable=False, comment='Координаты точки (WGS84)'),
        sa.Column('address', sa.String(length=500), nullable=True, comment='Адрес точки'),
        sa.Column('order_id', sa.Integer(), nullable=True, comment='FK на связанный заказ (если применимо)'),
        sa.Column('stop_type', ENUM(name='route_stop_type', create_type=False), server_default=sa.text("'other'"), nullable=False, comment='Тип остановки'),
        sa.Column('estimated_arrival', sa.DateTime(), nullable=True, comment='Планируемое время прибытия'),
        sa.Column('actual_arrival', sa.DateTime(), nullable=True, comment='Фактическое время прибытия'),
        sa.Column('is_completed', sa.Boolean(), server_default=sa.text('false'), nullable=False, comment='Флаг выполнения точки'),
        sa.Column('note', sa.Text(), nullable=True, comment='Заметки к точке маршрута'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_route_points_route_id'), 'route_points', ['route_id'], unique=False)
    op.create_index(op.f('ix_route_points_order_id'), 'route_points', ['order_id'], unique=False)
    op.create_index(op.f('ix_route_points_route_sequence'), 'route_points', ['route_id', 'sequence'], unique=False)
    op.create_foreign_key(
        'fk_route_points_route_id',
        'route_points', 'routes',
        ['route_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_route_points_order_id',
        'route_points', 'orders',
        ['order_id'], ['id'],
        ondelete='SET NULL'
    )

    # 4. Создаём таблицу route_change_history
    op.create_table(
        'route_change_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('route_id', sa.Integer(), nullable=False, comment='FK на маршрут'),
        sa.Column('change_type', ENUM(name='route_change_type', create_type=False), nullable=False, comment='Тип изменения'),
        sa.Column('changed_by_id', sa.Integer(), nullable=True, comment='ID пользователя, внесшего изменение'),
        sa.Column('changed_field', sa.String(length=255), nullable=True, comment='Название изменённого поля'),
        sa.Column('old_value', sa.Text(), nullable=True, comment='Значение до изменения (JSON)'),
        sa.Column('new_value', sa.Text(), nullable=True, comment='Значение после изменения (JSON)'),
        sa.Column('description', sa.Text(), nullable=True, comment='Описание изменения'),
        sa.Column('change_metadata', sa.Text(), nullable=True, comment='Дополнительные метаданные (JSON)'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='Время внесения изменения'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_route_change_history_route_id'), 'route_change_history', ['route_id'], unique=False)
    op.create_index(op.f('ix_route_change_history_changed_by_id'), 'route_change_history', ['changed_by_id'], unique=False)
    op.create_index(op.f('ix_route_change_history_route_time'), 'route_change_history', ['route_id', 'created_at'], unique=False)
    op.create_foreign_key(
        'fk_route_change_history_route_id',
        'route_change_history', 'routes',
        ['route_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_route_change_history_changed_by_id',
        'route_change_history', 'drivers',
        ['changed_by_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    # Удаляем таблицы в обратном порядке из-за foreign keys
    op.drop_constraint('fk_route_change_history_changed_by_id', 'route_change_history', type_='foreignkey')
    op.drop_constraint('fk_route_change_history_route_id', 'route_change_history', type_='foreignkey')
    op.drop_index(op.f('ix_route_change_history_route_time'), table_name='route_change_history')
    op.drop_index(op.f('ix_route_change_history_changed_by_id'), table_name='route_change_history')
    op.drop_index(op.f('ix_route_change_history_route_id'), table_name='route_change_history')
    op.drop_table('route_change_history')

    op.drop_constraint('fk_route_points_order_id', 'route_points', type_='foreignkey')
    op.drop_constraint('fk_route_points_route_id', 'route_points', type_='foreignkey')
    op.drop_index(op.f('ix_route_points_route_sequence'), table_name='route_points')
    op.drop_index(op.f('ix_route_points_order_id'), table_name='route_points')
    op.drop_index(op.f('ix_route_points_route_id'), table_name='route_points')
    op.drop_table('route_points')

    op.drop_constraint('fk_routes_driver_id', 'routes', type_='foreignkey')
    op.drop_index(op.f('ix_routes_driver_id'), table_name='routes')
    op.drop_table('routes')

    # Удаляем ENUM типы
    op.execute('DROP TYPE route_change_type')
    op.execute('DROP TYPE route_stop_type')
    op.execute('DROP TYPE route_optimization_type')
    op.execute('DROP TYPE route_status')
