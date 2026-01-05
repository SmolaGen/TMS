from uuid import uuid4
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware для добавления Correlation ID к каждому запросу.
    Позволяет отслеживать цепочку логов для конкретного HTTP-запроса.
    """
    
    HEADER_NAME = "X-Correlation-ID"
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Берем ID из заголовка или генерируем новый
        correlation_id = request.headers.get(
            self.HEADER_NAME, 
            str(uuid4())
        )
        
        # Привязываем ID к контексту structlog
        token = structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
        )
        
        try:
            response = await call_next(request)
            # Добавляем ID в заголовки ответа
            response.headers[self.HEADER_NAME] = correlation_id
            return response
        finally:
            # Очищаем контекст после завершения запроса
            structlog.contextvars.unbind_contextvars("correlation_id", "method", "path")
