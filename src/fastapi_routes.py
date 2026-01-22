import os

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from src.config import settings
from src.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "tms-backend"}


@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket эндпоинт для real-time обновлений."""
    origin = websocket.headers.get("origin")
    host = websocket.headers.get("host")
    upgrade = websocket.headers.get("upgrade")
    connection = websocket.headers.get("connection")

    logger.info("websocket_attempt", origin=origin, host=host, upgrade=upgrade, connection=connection)

    allowed_origins = settings.CORS_ORIGINS.split(",")

    if origin and origin not in allowed_origins:
        logger.warning("websocket_rejected_origin", origin=origin, allowed=allowed_origins)
        await websocket.close(code=1008, reason="Origin not allowed")
        return

    try:
        await websocket.accept()
        logger.info("websocket_accepted", origin=origin)
    except Exception as e:
        logger.error("websocket_accept_failed", error=str(e), origin=origin)
        return

    try:
        await websocket.send_json({
            "type": "HELLO",
            "payload": {"message": "Connected to TMS WS"}
        })
    except Exception as e:
        logger.error("websocket_hello_failed", error=str(e))

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("websocket_disconnected")


@router.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "TMS - Transport Management System",
        "docs": "/docs",
        "redoc": "/redoc",
    }
