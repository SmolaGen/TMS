import os

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.config import settings
from src.core.logging import get_logger, configure_logging
from src.core.middleware import CorrelationIdMiddleware
from src.app_lifespan import lifespan

# Prometheus metrics
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

logger = get_logger(__name__)
configure_logging(settings.LOG_LEVEL)

# Prometheus Metrics
REQUEST_COUNT = Counter(
    'tms_requests_total',
    'Total request count',
    ['method', 'endpoint', 'status']
)
REQUEST_LATENCY = Histogram(
    'tms_request_latency_seconds',
    'Request latency in seconds',
    ['method', 'endpoint']
)

def create_fastapi_app() -> FastAPI:
    app = FastAPI(
        title="TMS - Transport Management System",
        description="Отказоустойчивая система управления транспортом",
        version="0.1.0",
        lifespan=lifespan,
    )
    return app

def configure_app_middleware(app: FastAPI):
    # Rate Limiting (SlowAPI with Redis backend)
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=settings.REDIS_URL,
        default_limits=[settings.RATE_LIMIT_DEFAULT],
        headers_enabled=True,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # CORS middleware (production: ограничено конкретными доменами)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS.split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Correlation ID and Logging context
    app.add_middleware(CorrelationIdMiddleware)

    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        import time
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
