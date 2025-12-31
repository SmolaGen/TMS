#!/bin/bash
# init_osrm.sh - Инициализация данных OSRM для Дальневосточного ФО
# Запускать на сервере в директории /root/tms

set -e

OSRM_DIR="./osrm-data"
DATA_FILE="far-eastern-fed-district-latest.osm.pbf"
DATA_URL="https://download.geofabrik.de/russia/${DATA_FILE}"

echo "=== OSRM Data Initialization ==="
echo "Region: Far Eastern Federal District (Primorsky Krai, Yakutia, etc.)"

# 1. Создание директории
echo "[1/5] Creating directory..."
mkdir -p "$OSRM_DIR"
cd "$OSRM_DIR"

# 2. Скачивание данных OSM
if [ -f "$DATA_FILE" ]; then
    echo "[2/5] OSM data already exists, skipping download..."
else
    echo "[2/5] Downloading OSM data (~1.5 GB)..."
    wget -c "$DATA_URL" -O "$DATA_FILE"
fi

# 3. Извлечение графа (osrm-extract)
echo "[3/5] Extracting road graph (this may take 20-30 minutes)..."
docker run -t --rm -v "$(pwd):/data" osrm/osrm-backend \
    osrm-extract -p /opt/car.lua /data/$DATA_FILE

# 4. Разбиение на ячейки (osrm-partition)
echo "[4/5] Partitioning graph..."
docker run -t --rm -v "$(pwd):/data" osrm/osrm-backend \
    osrm-partition /data/far-eastern-fed-district-latest.osrm

# 5. Настройка весов (osrm-customize)
echo "[5/5] Customizing weights..."
docker run -t --rm -v "$(pwd):/data" osrm/osrm-backend \
    osrm-customize /data/far-eastern-fed-district-latest.osrm

cd ..
echo ""
echo "=== OSRM Initialization Complete ==="
echo "You can now start OSRM with: docker-compose --profile routing up -d"
