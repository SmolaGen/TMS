from uuid import uuid4
import structlog
from starlette.types import ASGIApp, Scope, Receive, Send

class CorrelationIdMiddleware:
    """
    ASGI Middleware для добавления Correlation ID к каждому запросу (HTTP и WebSocket).
    Позволяет отслеживать цепочку логов для конкретного соединения или запроса.
    """
    
    def __init__(self, app: ASGIApp):
        self.app = app
        self.header_name = "X-Correlation-ID"
        self.header_key = self.header_name.lower().encode("latin-1")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        # Извлекаем Correlation ID из заголовков
        correlation_id = None
        for key, value in scope.get("headers", []):
            if key == self.header_key:
                correlation_id = value.decode("latin-1")
                break
        
        if not correlation_id:
            correlation_id = str(uuid4())

        # Привязываем ID к контексту structlog
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        
        if scope["type"] == "http":
            structlog.contextvars.bind_contextvars(
                method=scope["method"],
                path=scope["path"],
            )

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Добавляем ID в заголовки HTTP ответа
                headers = list(message.get("headers", []))
                headers.append((self.header_key, correlation_id.encode("latin-1")))
                message["headers"] = headers
            await send(message)

        try:
            if scope["type"] == "http":
                await self.app(scope, receive, send_wrapper)
            else:
                # Для WebSocket просто пробрасываем
                await self.app(scope, receive, send)
        finally:
            # Очищаем контекст после завершения
            structlog.contextvars.unbind_contextvars("correlation_id", "method", "path")
