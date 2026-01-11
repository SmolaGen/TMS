import pandas as pd
from datetime import datetime, time, date
from typing import List, Dict, Any
from fastapi import UploadFile
import io

from src.schemas.order import OrderCreate
from src.database.models import OrderPriority
from src.core.logging import get_logger

logger = get_logger(__name__)

class ExcelImportService:
    """
    Сервис для парсинга и импорта заказов из Excel.
    """
    
    def __init__(self, order_service):
        self.order_service = order_service

    async def parse_excel(self, file: UploadFile) -> List[OrderCreate]:
        """Парсинг Excel файла в список OrderCreate."""
        content = await file.read()
        df = pd.read_excel(io.BytesIO(content))
        
        # Ожидаемые колонки (на русском для удобства диспетчера):
        # Адрес погрузки | Адрес выгрузки | Дата | Время | Приоритет | Телефон | Имя | Комментарий
        
        orders = []
        for index, row in df.iterrows():
            try:
                # Маппинг колонок (гибкий - можно по индексу или по имени)
                # Предположим стандартный формат
                
                pickup_address = str(row.get('Адрес погрузки', ''))
                dropoff_address = str(row.get('Адрес выгрузки', ''))
                order_date = row.get('Дата')
                order_time = row.get('Время')
                priority_str = str(row.get('Приоритет', 'normal')).lower()
                
                if not pickup_address or not dropoff_address or pd.isna(order_date):
                    logger.warning(f"Skipping row {index} due to missing data")
                    continue

                # Обработка даты и времени
                if isinstance(order_date, str):
                    dt_date = datetime.strptime(order_date, "%Y-%m-%d").date()
                elif isinstance(order_date, datetime):
                    dt_date = order_date.date()
                else:
                    dt_date = order_date # assume date object
                
                if isinstance(order_time, str):
                    dt_time = datetime.strptime(order_time, "%H:%M").time()
                elif isinstance(order_time, time):
                    dt_time = order_time
                elif isinstance(order_time, datetime):
                    dt_time = order_time.time()
                else:
                    dt_time = time(10, 0) # default

                combined_dt = datetime.combine(dt_date, dt_time)
                
                # Приоритет
                priority = OrderPriority.NORMAL
                if priority_str == 'urgent': priority = OrderPriority.URGENT
                elif priority_str == 'high': priority = OrderPriority.HIGH
                elif priority_str == 'low': priority = OrderPriority.LOW

                # Мы не знаем координат из Excel, поэтому используем геокодинг
                # TODO: Интегрировать геокодинг в OrderService или здесь
                # Для начала предположим, что OrderService.create_order требует координат
                # Нам нужно сначала найти координаты по адресу.
                
                # Но если у нас нет координат, мы не можем создать заказ через текущий OrderService.
                # Нам нужно либо добавить геокодинг в импорт, либо разрешить создание без координат.
                
                # Временно пропустим те, где нет координат, если они не указаны в Excel.
                # Если в Excel есть колонки "Широта погрузки" и т.д.
                
                orders.append({
                    "pickup_address": pickup_address,
                    "dropoff_address": dropoff_address,
                    "time_start": combined_dt,
                    "priority": priority,
                    "customer_phone": str(row.get('Телефон', '')) if not pd.isna(row.get('Телефон')) else None,
                    "customer_name": str(row.get('Имя', '')) if not pd.isna(row.get('Имя')) else None,
                    "comment": str(row.get('Комментарий', '')) if not pd.isna(row.get('Комментарий')) else None,
                    # Координаты (если есть)
                    "pickup_lat": row.get('Широта погрузки'),
                    "pickup_lon": row.get('Долгота погрузки'),
                    "dropoff_lat": row.get('Широта выгрузки'),
                    "dropoff_lon": row.get('Долгота выгрузки'),
                })
            except Exception as e:
                logger.error(f"Error parsing row {index}: {e}")
                
        return orders

    async def import_orders(self, orders_data: List[Dict[str, Any]], geocoding_service) -> Dict[str, Any]:
        """Импорт заказов с геокодингом."""
        created = 0
        failed = 0
        errors = []
        
        for data in orders_data:
            try:
                # 1. Геокодинг если координат нет
                if not data.get('pickup_lat') or not data.get('pickup_lon'):
                    res = await geocoding_service.geocode(data['pickup_address'])
                    if res:
                        data['pickup_lat'] = res.lat
                        data['pickup_lon'] = res.lon
                    else:
                        raise ValueError(f"Не удалось найти адрес погрузки: {data['pickup_address']}")

                if not data.get('dropoff_lat') or not data.get('dropoff_lon'):
                    res = await geocoding_service.geocode(data['dropoff_address'])
                    if res:
                        data['dropoff_lat'] = res.lat
                        data['dropoff_lon'] = res.lon
                    else:
                        raise ValueError(f"Не удалось найти адрес выгрузки: {data['dropoff_address']}")
                
                # 2. Создание заказа
                dto = OrderCreate(**data)
                await self.order_service.create_order(dto)
                created += 1
            except Exception as e:
                failed += 1
                errors.append({"address": data['pickup_address'], "error": str(e)})
                
        return {"created": created, "failed": failed, "errors": errors}
