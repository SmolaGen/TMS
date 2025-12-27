"""Partition driver_location_history by recorded_at

Revision ID: 003_partitioned_location_history
Revises: 002_add_location_history
Create Date: 2025-12-27

Добавляет:
- Партиционирование таблицы driver_location_history по RANGE(recorded_at)
- Автоматическое создание партиций на 5 недель вперёд
- Локальные индексы для каждой партиции
- Функции для управления партициями
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timedelta


revision: str = "003_partitioned_location_history"
down_revision: Union[str, None] = "002_add_location_history"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Применение миграции."""
    
    # 1. Переименовываем старую таблицу
    op.execute("ALTER TABLE driver_location_history RENAME TO driver_location_history_old;")
    
    # 2. Удаляем старый индекс
    op.execute("DROP INDEX IF EXISTS ix_driver_location_time;")
    
    # 3. Создаём новую партиционированную таблицу
    op.execute("""
        CREATE TABLE driver_location_history (
            id BIGSERIAL,
            driver_id INTEGER NOT NULL REFERENCES drivers(id) ON DELETE CASCADE,
            location GEOMETRY(POINT, 4326) NOT NULL,
            recorded_at TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
            PRIMARY KEY (id, recorded_at)
        ) PARTITION BY RANGE (recorded_at);
    """)
    
    # 4. Создаём партиции на текущую + 4 будущих недели
    today = datetime.utcnow().date()
    # Начало текущей недели (понедельник)
    start_of_week = today - timedelta(days=today.weekday())
    
    for i in range(5):  # Текущая + 4 будущих недели
        week_start = start_of_week + timedelta(weeks=i)
        week_end = week_start + timedelta(weeks=1)
        year = week_start.isocalendar()[0]
        week_num = week_start.isocalendar()[1]
        partition_name = f"driver_location_history_y{year}_w{week_num:02d}"
        
        op.execute(f"""
            CREATE TABLE {partition_name} PARTITION OF driver_location_history
            FOR VALUES FROM ('{week_start.isoformat()}') TO ('{week_end.isoformat()}');
        """)
        
        # Локальный индекс для партиции
        op.execute(f"""
            CREATE INDEX ix_{partition_name}_driver_time 
            ON {partition_name} (driver_id, recorded_at);
        """)
    
    # 5. Создаём DEFAULT партицию для "непопавших" данных
    op.execute("""
        CREATE TABLE driver_location_history_default 
        PARTITION OF driver_location_history DEFAULT;
    """)
    
    op.execute("""
        CREATE INDEX ix_driver_location_history_default_driver_time 
        ON driver_location_history_default (driver_id, recorded_at);
    """)
    
    # 6. Миграция данных из старой таблицы (если есть)
    op.execute("""
        INSERT INTO driver_location_history (id, driver_id, location, recorded_at, created_at)
        SELECT id, driver_id, location, 
               COALESCE(recorded_at, CURRENT_TIMESTAMP), 
               COALESCE(created_at, CURRENT_TIMESTAMP)
        FROM driver_location_history_old;
    """)
    
    # 7. Обновляем sequence для id
    op.execute("""
        SELECT setval(
            pg_get_serial_sequence('driver_location_history', 'id'),
            COALESCE((SELECT MAX(id) FROM driver_location_history), 0) + 1,
            false
        );
    """)
    
    # 8. Удаляем старую таблицу
    op.execute("DROP TABLE driver_location_history_old;")
    
    # 9. Функция для автоматического создания партиций
    op.execute("""
        CREATE OR REPLACE FUNCTION create_location_history_partition()
        RETURNS void AS $$
        DECLARE
            target_week_start DATE;
            target_week_end DATE;
            partition_name TEXT;
            i INTEGER;
        BEGIN
            -- Создаём партиции на 4 недели вперёд от текущей даты
            FOR i IN 0..4 LOOP
                target_week_start := date_trunc('week', CURRENT_DATE + (i || ' weeks')::interval)::date;
                target_week_end := target_week_start + interval '1 week';
                partition_name := 'driver_location_history_y' || 
                                  EXTRACT(ISOYEAR FROM target_week_start)::text || '_w' ||
                                  LPAD(EXTRACT(WEEK FROM target_week_start)::text, 2, '0');
                
                -- Проверяем, существует ли партиция
                IF NOT EXISTS (
                    SELECT 1 FROM pg_tables 
                    WHERE schemaname = 'public' AND tablename = partition_name
                ) THEN
                    EXECUTE format(
                        'CREATE TABLE %I PARTITION OF driver_location_history
                         FOR VALUES FROM (%L) TO (%L)',
                        partition_name, target_week_start, target_week_end
                    );
                    
                    EXECUTE format(
                        'CREATE INDEX ix_%I_driver_time ON %I (driver_id, recorded_at)',
                        partition_name, partition_name
                    );
                    
                    RAISE NOTICE 'Created partition: %', partition_name;
                END IF;
            END LOOP;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # 10. Функция для удаления старых партиций (retention policy)
    op.execute("""
        CREATE OR REPLACE FUNCTION drop_old_location_history_partitions(retention_weeks INTEGER DEFAULT 12)
        RETURNS void AS $$
        DECLARE
            partition_record RECORD;
            cutoff_date DATE;
            partition_year INTEGER;
            partition_week INTEGER;
            partition_start DATE;
        BEGIN
            cutoff_date := CURRENT_DATE - (retention_weeks || ' weeks')::interval;
            
            FOR partition_record IN
                SELECT c.relname AS partition_name
                FROM pg_inherits i
                JOIN pg_class c ON i.inhrelid = c.oid
                JOIN pg_class p ON i.inhparent = p.oid
                WHERE p.relname = 'driver_location_history'
                AND c.relname != 'driver_location_history_default'
                AND c.relname LIKE 'driver_location_history_y%'
            LOOP
                -- Извлекаем год и неделю из имени партиции
                -- Формат: driver_location_history_yYYYY_wWW
                BEGIN
                    partition_year := SUBSTRING(partition_record.partition_name FROM 'y([0-9]{4})')::INTEGER;
                    partition_week := SUBSTRING(partition_record.partition_name FROM 'w([0-9]{2})')::INTEGER;
                    partition_start := make_date(partition_year, 1, 1) + ((partition_week - 1) * 7 || ' days')::interval;
                    
                    IF partition_start < cutoff_date THEN
                        EXECUTE format('DROP TABLE %I', partition_record.partition_name);
                        RAISE NOTICE 'Dropped old partition: %', partition_record.partition_name;
                    END IF;
                EXCEPTION WHEN OTHERS THEN
                    RAISE WARNING 'Could not parse partition name: %', partition_record.partition_name;
                END;
            END LOOP;
        END;
        $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    """Откат миграции."""
    
    # Удаляем функции
    op.execute("DROP FUNCTION IF EXISTS drop_old_location_history_partitions;")
    op.execute("DROP FUNCTION IF EXISTS create_location_history_partition;")
    
    # Создаём временную таблицу
    op.execute("""
        CREATE TABLE driver_location_history_new (
            id SERIAL PRIMARY KEY,
            driver_id INTEGER NOT NULL REFERENCES drivers(id) ON DELETE CASCADE,
            location GEOMETRY(POINT, 4326) NOT NULL,
            recorded_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
        );
    """)
    
    # Мигрируем данные
    op.execute("""
        INSERT INTO driver_location_history_new (driver_id, location, recorded_at, created_at)
        SELECT driver_id, location, recorded_at, created_at
        FROM driver_location_history;
    """)
    
    # Удаляем партиционированную таблицу (cascade удалит все партиции)
    op.execute("DROP TABLE driver_location_history CASCADE;")
    
    # Переименовываем
    op.execute("ALTER TABLE driver_location_history_new RENAME TO driver_location_history;")
    
    # Восстанавливаем индекс
    op.execute("""
        CREATE INDEX ix_driver_location_time 
        ON driver_location_history (driver_id, recorded_at);
    """)
