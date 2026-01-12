BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 001_initial

CREATE EXTENSION IF NOT EXISTS btree_gist;;

CREATE EXTENSION IF NOT EXISTS postgis;;

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
        END $$;;

CREATE TYPE driver_status AS ENUM ('available', 'busy', 'offline');

CREATE TABLE drivers (
    id SERIAL NOT NULL, 
    telegram_id BIGINT NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    phone VARCHAR(20), 
    status driver_status DEFAULT 'offline' NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (telegram_id)
);

COMMENT ON COLUMN drivers.telegram_id IS 'Telegram user ID';

COMMENT ON COLUMN drivers.name IS 'Имя водителя';

COMMENT ON COLUMN drivers.phone IS 'Номер телефона';

COMMENT ON COLUMN drivers.status IS 'Текущий статус';

CREATE UNIQUE INDEX ix_drivers_telegram_id ON drivers (telegram_id);

CREATE TYPE order_status AS ENUM ('pending', 'assigned', 'in_progress', 'completed', 'cancelled');

CREATE TYPE order_priority AS ENUM ('low', 'normal', 'high', 'urgent');

CREATE TABLE orders (
    id SERIAL NOT NULL, 
    driver_id INTEGER, 
    status order_status DEFAULT 'pending' NOT NULL, 
    priority order_priority DEFAULT 'normal' NOT NULL, 
    time_range TSTZRANGE, 
    pickup_location geometry(POINT,4326), 
    dropoff_location geometry(POINT,4326), 
    comment TEXT, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(driver_id) REFERENCES drivers (id) ON DELETE SET NULL
);

CREATE INDEX idx_orders_dropoff_location ON orders USING gist (dropoff_location);

CREATE INDEX idx_orders_pickup_location ON orders USING gist (pickup_location);

COMMENT ON COLUMN orders.driver_id IS 'FK на водителя';

COMMENT ON COLUMN orders.status IS 'Статус заказа';

COMMENT ON COLUMN orders.priority IS 'Приоритет заказа';

COMMENT ON COLUMN orders.time_range IS 'Временной интервал выполнения (с таймзоной)';

COMMENT ON COLUMN orders.pickup_location IS 'Координаты точки погрузки (WGS84)';

COMMENT ON COLUMN orders.dropoff_location IS 'Координаты точки выгрузки (WGS84)';

COMMENT ON COLUMN orders.comment IS 'Комментарий к заказу';

CREATE INDEX ix_orders_driver_id ON orders (driver_id);

CREATE INDEX ix_orders_status_priority ON orders (status, priority);

CREATE INDEX ix_orders_time_range_gist ON orders 
        USING gist (time_range);;

ALTER TABLE orders ADD CONSTRAINT no_driver_time_overlap
        EXCLUDE USING gist (
            driver_id WITH =,
            time_range WITH &&
        )
        WHERE (
            driver_id IS NOT NULL 
            AND status NOT IN ('completed', 'cancelled')
        );;

INSERT INTO alembic_version (version_num) VALUES ('001_initial') RETURNING alembic_version.version_num;

-- Running upgrade 001_initial -> 002_add_location_history

CREATE TABLE driver_location_history (
    id SERIAL NOT NULL, 
    driver_id INTEGER NOT NULL, 
    location geometry(POINT,4326) NOT NULL, 
    recorded_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(driver_id) REFERENCES drivers (id) ON DELETE CASCADE
);

CREATE INDEX idx_driver_location_history_location ON driver_location_history USING gist (location);

COMMENT ON COLUMN driver_location_history.driver_id IS 'ID водителя';

COMMENT ON COLUMN driver_location_history.location IS 'Координаты (WGS84)';

COMMENT ON COLUMN driver_location_history.recorded_at IS 'Время фиксации координат водителем';

COMMENT ON COLUMN driver_location_history.created_at IS 'Время записи в БД';

CREATE INDEX ix_driver_location_time ON driver_location_history (driver_id, recorded_at);

UPDATE alembic_version SET version_num='002_add_location_history' WHERE alembic_version.version_num = '001_initial';

-- Running upgrade 002_add_location_history -> 003_partitioned_location_history

ALTER TABLE driver_location_history RENAME TO driver_location_history_old;;

DROP INDEX IF EXISTS ix_driver_location_time;;

CREATE TABLE driver_location_history (
            id BIGSERIAL,
            driver_id INTEGER NOT NULL REFERENCES drivers(id) ON DELETE CASCADE,
            location GEOMETRY(POINT, 4326) NOT NULL,
            recorded_at TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
            PRIMARY KEY (id, recorded_at)
        ) PARTITION BY RANGE (recorded_at);;

CREATE TABLE driver_location_history_y2026_w03 PARTITION OF driver_location_history
            FOR VALUES FROM ('2026-01-12') TO ('2026-01-19');;

CREATE INDEX ix_driver_location_history_y2026_w03_driver_time 
            ON driver_location_history_y2026_w03 (driver_id, recorded_at);;

CREATE TABLE driver_location_history_y2026_w04 PARTITION OF driver_location_history
            FOR VALUES FROM ('2026-01-19') TO ('2026-01-26');;

CREATE INDEX ix_driver_location_history_y2026_w04_driver_time 
            ON driver_location_history_y2026_w04 (driver_id, recorded_at);;

CREATE TABLE driver_location_history_y2026_w05 PARTITION OF driver_location_history
            FOR VALUES FROM ('2026-01-26') TO ('2026-02-02');;

CREATE INDEX ix_driver_location_history_y2026_w05_driver_time 
            ON driver_location_history_y2026_w05 (driver_id, recorded_at);;

CREATE TABLE driver_location_history_y2026_w06 PARTITION OF driver_location_history
            FOR VALUES FROM ('2026-02-02') TO ('2026-02-09');;

CREATE INDEX ix_driver_location_history_y2026_w06_driver_time 
            ON driver_location_history_y2026_w06 (driver_id, recorded_at);;

CREATE TABLE driver_location_history_y2026_w07 PARTITION OF driver_location_history
            FOR VALUES FROM ('2026-02-09') TO ('2026-02-16');;

CREATE INDEX ix_driver_location_history_y2026_w07_driver_time 
            ON driver_location_history_y2026_w07 (driver_id, recorded_at);;

CREATE TABLE driver_location_history_default 
        PARTITION OF driver_location_history DEFAULT;;

CREATE INDEX ix_driver_location_history_default_driver_time 
        ON driver_location_history_default (driver_id, recorded_at);;

INSERT INTO driver_location_history (id, driver_id, location, recorded_at, created_at)
        SELECT id, driver_id, location, 
               COALESCE(recorded_at, CURRENT_TIMESTAMP), 
               COALESCE(created_at, CURRENT_TIMESTAMP)
        FROM driver_location_history_old;;

SELECT setval(
            pg_get_serial_sequence('driver_location_history', 'id'),
            COALESCE((SELECT MAX(id) FROM driver_location_history), 0) + 1,
            false
        );;

DROP TABLE driver_location_history_old;;

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
        $$ LANGUAGE plpgsql;;

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
        $$ LANGUAGE plpgsql;;

UPDATE alembic_version SET version_num='003_partitioned_location_history' WHERE alembic_version.version_num = '002_add_location_history';

-- Running upgrade 003_partitioned_location_history -> 2e807d974556

COMMIT;

ALTER TYPE order_status ADD VALUE 'driver_arrived' AFTER 'assigned';

ALTER TABLE orders ADD COLUMN arrived_at TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE orders ADD COLUMN started_at TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE orders ADD COLUMN end_time TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE orders ADD COLUMN cancelled_at TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE orders ADD COLUMN cancellation_reason VARCHAR(500);

UPDATE alembic_version SET version_num='2e807d974556' WHERE alembic_version.version_num = '003_partitioned_location_history';

-- Running upgrade 2e807d974556 -> 7cd55e5e7f3e

ALTER TABLE orders ADD COLUMN distance_meters FLOAT;

COMMENT ON COLUMN orders.distance_meters IS 'Дистанция в метрах (от OSRM)';

ALTER TABLE orders ADD COLUMN duration_seconds FLOAT;

COMMENT ON COLUMN orders.duration_seconds IS 'Время в пути в секундах (от OSRM)';

ALTER TABLE orders ADD COLUMN price NUMERIC(10, 2);

COMMENT ON COLUMN orders.price IS 'Итоговая стоимость заказа';

UPDATE alembic_version SET version_num='7cd55e5e7f3e' WHERE alembic_version.version_num = '2e807d974556';

-- Running upgrade 7cd55e5e7f3e -> ada6f256ebbf

ALTER TABLE driver_location_history ADD COLUMN created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL;

COMMENT ON COLUMN driver_location_history.created_at IS 'Время записи в БД';

ALTER TABLE driver_location_history ALTER COLUMN id TYPE INTEGER;

COMMENT ON COLUMN driver_location_history.driver_id IS 'ID водителя';

COMMENT ON COLUMN driver_location_history.location IS 'Координаты (WGS84)';

ALTER TABLE driver_location_history ALTER COLUMN recorded_at TYPE TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE driver_location_history ALTER COLUMN recorded_at DROP DEFAULT;

COMMENT ON COLUMN driver_location_history.recorded_at IS 'Время фиксации координат водителем';

CREATE INDEX idx_driver_location_history_location ON driver_location_history USING gist (location);

CREATE INDEX ix_driver_location_history_driver_id ON driver_location_history (driver_id);

CREATE INDEX ix_driver_location_history_recorded_at ON driver_location_history (recorded_at);

COMMENT ON COLUMN drivers.telegram_id IS 'Telegram user ID';

COMMENT ON COLUMN drivers.name IS 'Имя водителя';

COMMENT ON COLUMN drivers.phone IS 'Номер телефона';

COMMENT ON COLUMN drivers.status IS 'Текущий статус';

ALTER TABLE drivers ALTER COLUMN is_active SET NOT NULL;

COMMENT ON COLUMN drivers.is_active IS 'Флаг активности (разрешен ли вход в бот)';

ALTER TABLE drivers DROP CONSTRAINT drivers_telegram_id_key;

DROP INDEX ix_drivers_telegram_id;

CREATE UNIQUE INDEX ix_drivers_telegram_id ON drivers (telegram_id);

COMMENT ON COLUMN orders.driver_id IS 'FK на водителя';

COMMENT ON COLUMN orders.status IS 'Статус заказа';

COMMENT ON COLUMN orders.priority IS 'Приоритет заказа';

COMMENT ON COLUMN orders.time_range IS 'Временной интервал выполнения (с таймзоной)';

COMMENT ON COLUMN orders.pickup_location IS 'Координаты точки погрузки (WGS84)';

COMMENT ON COLUMN orders.dropoff_location IS 'Координаты точки выгрузки (WGS84)';

COMMENT ON COLUMN orders.comment IS 'Комментарий к заказу';

ALTER TABLE orders ALTER COLUMN cancellation_reason TYPE TEXT;

DROP INDEX ix_orders_time_range_gist;

CREATE INDEX idx_orders_dropoff_location ON orders USING gist (dropoff_location);

CREATE INDEX idx_orders_pickup_location ON orders USING gist (pickup_location);

UPDATE alembic_version SET version_num='ada6f256ebbf' WHERE alembic_version.version_num = '7cd55e5e7f3e';

-- Running upgrade ada6f256ebbf -> f7d2e3b4a5c6

ALTER TABLE orders ADD COLUMN route_geometry TEXT;

COMMENT ON COLUMN orders.route_geometry IS 'Закодированная геометрия маршрута (polyline)';

UPDATE alembic_version SET version_num='f7d2e3b4a5c6' WHERE alembic_version.version_num = 'ada6f256ebbf';

-- Running upgrade f7d2e3b4a5c6 -> add_address_fields_01

ALTER TABLE orders ADD COLUMN pickup_address TEXT;

ALTER TABLE orders ADD COLUMN dropoff_address TEXT;

ALTER TABLE orders ADD COLUMN customer_phone VARCHAR(50);

ALTER TABLE orders ADD COLUMN customer_name VARCHAR(255);

UPDATE alembic_version SET version_num='add_address_fields_01' WHERE alembic_version.version_num = 'f7d2e3b4a5c6';

-- Running upgrade add_address_fields_01 -> add_user_role_01

DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN
                CREATE TYPE user_role AS ENUM ('driver', 'dispatcher', 'admin', 'pending');
            END IF;
        END $$;;

ALTER TABLE drivers ADD COLUMN role user_role DEFAULT 'pending' NOT NULL;

COMMENT ON COLUMN drivers.role IS 'Роль пользователя в системе';

UPDATE alembic_version SET version_num='add_user_role_01' WHERE alembic_version.version_num = 'add_address_fields_01';

-- Running upgrade add_user_role_01 -> add_contractors_01

CREATE TABLE contractors (
    id SERIAL NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    api_key VARCHAR(255) NOT NULL, 
    webhook_url VARCHAR(500), 
    is_active BOOLEAN DEFAULT true NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_contractors_api_key ON contractors (api_key);

CREATE UNIQUE INDEX ix_contractors_name ON contractors (name);

ALTER TABLE orders ADD COLUMN contractor_id INTEGER;

COMMENT ON COLUMN orders.contractor_id IS 'FK на подрядчика';

ALTER TABLE orders ADD COLUMN external_id VARCHAR(255);

COMMENT ON COLUMN orders.external_id IS 'ID заказа во внешней системе';

CREATE INDEX ix_orders_contractor_id ON orders (contractor_id);

CREATE INDEX ix_orders_external_id ON orders (external_id);

ALTER TABLE orders ADD CONSTRAINT fk_orders_contractor_id FOREIGN KEY(contractor_id) REFERENCES contractors (id) ON DELETE SET NULL;

UPDATE alembic_version SET version_num='add_contractors_01' WHERE alembic_version.version_num = 'add_user_role_01';

COMMIT;

