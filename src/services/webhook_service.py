import httpx
from typing import Optional
from src.database.models import Order
from src.core.logging import get_logger

logger = get_logger(__name__)

class WebhookService:
    """Сервис для отправки вебхуков внешним подрядчикам."""
    
    def __init__(self):
        # Мы создаем клиент здесь, но в идеале его лучше инжектировать или держать один на приложение
        self.client = httpx.AsyncClient(timeout=10.0)

    async def notify_status_change(self, order: Order):
        """Уведомить подрядчика об изменении статуса заказа."""
        if not order.contractor_id or not order.contractor:
            # Если нет подрядчика, некого уведомлять
            return

        if not order.contractor.webhook_url:
            logger.debug("webhook_skip_no_url", order_id=order.id, contractor_id=order.contractor_id)
            return

        payload = {
            "order_id": order.id,
            "external_id": order.external_id,
            "status": order.status.value,
            "event": "status_changed",
            "timestamp": order.updated_at.isoformat() if order.updated_at else None,
            "data": {
                "driver_id": order.driver_id,
                "pickup_address": order.pickup_address,
                "dropoff_address": order.dropoff_address
            }
        }

        try:
            logger.info("webhook_sending", order_id=order.id, url=order.contractor.webhook_url)
            response = await self.client.post(
                order.contractor.webhook_url,
                json=payload,
                headers={"X-TMS-Event": "order.status_changed"}
            )
            response.raise_for_status()
            logger.info("webhook_sent_success", order_id=order.id)
        except Exception as e:
            logger.error("webhook_failed", order_id=order.id, url=order.contractor.webhook_url, error=str(e))

    async def close(self):
        """Закрытие клиента."""
        await self.client.aclose()
