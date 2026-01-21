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

    async def notify_status_change(self, order: Order, event: str = "status_changed", extra_data: Optional[dict] = None):
        """Уведомить подрядчика или клиента об изменении статуса заказа."""
        # 1. Уведомление подрядчика (если есть)
        if order.contractor_id and order.contractor and order.contractor.webhook_url:
            await self._send_webhook(
                order.contractor.webhook_url,
                order,
                event,
                {"X-TMS-Event": f"order.{event}"},
                extra_data
            )
        elif order.contractor_id and order.contractor:
            logger.debug("webhook_skip_no_url", order_id=order.id, contractor_id=order.contractor_id)

        # 2. Уведомление клиента (если есть customer_webhook_url в заказе)
        if order.customer_webhook_url:
            await self._send_webhook(
                order.customer_webhook_url,
                order,
                event,
                {"X-TMS-Event": f"order.{event}"},
                extra_data
            )

    async def _send_webhook(self, url: str, order: Order, event: str, headers: dict, extra_data: Optional[dict] = None):
        """Вспомогательный метод для отправки вебхука."""
        payload = {
            "order_id": order.id,
            "external_id": order.external_id,
            "status": order.status.value,
            "event": event,
            "timestamp": order.updated_at.isoformat() if order.updated_at else None,
            "data": {
                "driver_id": order.driver_id,
                "pickup_address": order.pickup_address,
                "dropoff_address": order.dropoff_address,
                "customer_name": order.customer_name
            }
        }
        if extra_data:
            payload["data"].update(extra_data)

        try:
            logger.info("webhook_sending", order_id=order.id, url=url, webhook_event=event)
            response = await self.client.post(
                url,
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            logger.info("webhook_sent_success", order_id=order.id, url=url)
        except Exception as e:
            logger.error("webhook_failed", order_id=order.id, url=url, error=str(e))

    async def close(self):
        """Закрытие клиента."""
        await self.client.aclose()
