import os

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.config import settings, Settings
from src.core.logging import get_logger, configure_logging
from src.core.middleware import CorrelationIdMiddleware
from src.api.routes import router as api_router
from src.fastapi_core import create_fastapi_app, configure_app_middleware
from src.fastapi_routes import router as core_router
from src.app_lifespan import lifespan
from src.app_bot_routes import configure_bot_webhook


logger = get_logger(__name__)
configure_logging(settings.LOG_LEVEL)


def create_app(settings: Settings) -> FastAPI:
    app = create_fastapi_app()

    configure_app_middleware(app)
    configure_bot_webhook(app)
    # Register health check endpoints and core routes
    app.include_router(core_router)
    app.include_router(api_router, prefix="/api")

    return app

