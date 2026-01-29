"""
Worker Health Check Server

Simple HTTP health check server for workers to support Docker/Kubernetes health probes.

This server can be:
1. Started as a sidecar alongside workers
2. Embedded into worker processes for health reporting

Usage:
    from src.workers.health_check_server import start_health_check_server, stop_health_check_server

    # Start server (returns immediately, runs in background)
    server = await start_health_check_server(host="0.0.0.0", port=8081)

    # Later, stop the server
    await stop_health_check_server(server)
"""

import asyncio
import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field

from src.core.logging import get_logger
from src.core.health_check import (
    HealthCheckResult,
    HealthStatus,
    SyncHealthChecker,
    CompositeHealthChecker,
)
from src.config import settings

logger = get_logger(__name__)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class WorkerHealthStatus:
    """Status of a worker process."""
    name: str
    is_running: bool = False
    last_heartbeat: Optional[float] = None
    error_count: int = 0
    last_error: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "is_running": self.is_running,
            "last_heartbeat": self.last_heartbeat,
            "heartbeat_age_seconds": (
                time.time() - self.last_heartbeat if self.last_heartbeat else None
            ),
            "error_count": self.error_count,
            "last_error": self.last_error,
            "metrics": self.metrics,
        }


# ============================================================================
# Worker Health Checker
# ============================================================================

class WorkerProcessHealthChecker(SyncHealthChecker):
    """
    Health checker for a worker process.

    Checks if the worker has sent a heartbeat recently.
    """

    def __init__(
        self,
        name: str,
        worker_status: WorkerHealthStatus,
        max_heartbeat_age: float = 60.0,
    ):
        """
        Initialize worker process health checker.

        Args:
            name: Name of the worker
            worker_status: WorkerHealthStatus instance to check
            max_heartbeat_age: Maximum age of heartbeat in seconds
        """
        super().__init__(name=name, timeout=settings.HEALTH_CHECK_TIMEOUT)
        self.worker_status = worker_status
        self.max_heartbeat_age = max_heartbeat_age

    def check(self) -> HealthCheckResult:
        """
        Check worker health based on heartbeat.

        Returns:
            HealthCheckResult with worker status
        """
        if not self.worker_status.is_running:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.FAILED,
                message=f"Worker {self.name} is not running",
                details=self.worker_status.to_dict(),
            )

        if self.worker_status.last_heartbeat is None:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.DEGRADED,
                message=f"Worker {self.name} has not sent a heartbeat yet",
                details=self.worker_status.to_dict(),
            )

        heartbeat_age = time.time() - self.worker_status.last_heartbeat
        if heartbeat_age > self.max_heartbeat_age:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.FAILED,
                message=f"Worker {self.name} heartbeat is stale ({heartbeat_age:.1f}s old)",
                details=self.worker_status.to_dict(),
            )

        return HealthCheckResult(
            name=self.name,
            status=HealthStatus.OK,
            message=f"Worker {self.name} is healthy",
            details=self.worker_status.to_dict(),
        )


# ============================================================================
# HTTP Request Handler
# ============================================================================

class HealthCheckRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for health check endpoints."""

    # Class-level reference to the server instance
    server_instance: Optional["WorkerHealthCheckServer"] = None

    def log_message(self, format: str, *args) -> None:
        """Suppress default HTTP server logging."""
        pass

    def _send_json_response(self, status_code: int, data: Dict[str, Any]) -> None:
        """Send JSON response."""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_GET(self) -> None:
        """Handle GET requests."""
        if self.path == "/health" or self.path == "/health/":
            self._handle_health_check()
        elif self.path == "/health/live" or self.path == "/health/liveness":
            self._handle_liveness_check()
        elif self.path == "/health/ready" or self.path == "/health/readiness":
            self._handle_readiness_check()
        else:
            self._send_json_response(404, {"error": "Not found"})

    def _handle_health_check(self) -> None:
        """Handle comprehensive health check."""
        if self.server_instance is None:
            self._send_json_response(503, {"status": "failed", "message": "Server not initialized"})
            return

        result = self.server_instance.get_health_status()
        status_code = 200 if result.status == HealthStatus.OK else 503

        response = {
            "status": result.status.value,
            "timestamp": result.timestamp,
            "message": result.message,
            "checks": {
                name: check.to_dict()
                for name, check in result.details.get("checks", {}).items()
            },
        }

        self._send_json_response(status_code, response)

    def _handle_liveness_check(self) -> None:
        """
        Handle liveness check (is the process alive?).

        Kubernetes uses this to determine if a container should be restarted.
        Returns OK if the HTTP server is responding.
        """
        self._send_json_response(200, {
            "status": "ok",
            "timestamp": time.time(),
            "message": "Process is alive",
        })

    def _handle_readiness_check(self) -> None:
        """
        Handle readiness check (is the worker ready to process tasks?).

        Kubernetes uses this to determine if traffic should be sent to the pod.
        """
        if self.server_instance is None:
            self._send_json_response(503, {"status": "failed", "message": "Server not initialized"})
            return

        result = self.server_instance.get_health_status()
        is_ready = result.status in (HealthStatus.OK, HealthStatus.DEGRADED)
        status_code = 200 if is_ready else 503

        self._send_json_response(status_code, {
            "status": "ok" if is_ready else "not_ready",
            "timestamp": time.time(),
            "message": result.message,
        })


# ============================================================================
# Worker Health Check Server
# ============================================================================

class WorkerHealthCheckServer:
    """
    Simple HTTP server for worker health checks.

    Provides health endpoints compatible with Docker HEALTHCHECK and Kubernetes probes:
    - /health - Comprehensive health check
    - /health/live - Liveness probe (is process alive?)
    - /health/ready - Readiness probe (is worker ready to process tasks?)
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8081,
        worker_name: str = "worker",
    ):
        """
        Initialize health check server.

        Args:
            host: Host to bind to
            port: Port to bind to
            worker_name: Name of the worker for health reporting
        """
        self.host = host
        self.port = port
        self.worker_name = worker_name

        self._server: Optional[HTTPServer] = None
        self._thread: Optional[Thread] = None
        self._running = False

        # Health check infrastructure
        self._workers: Dict[str, WorkerHealthStatus] = {}
        self._health_checker = CompositeHealthChecker(name=f"{worker_name}_health")

        # Register main worker by default
        self.register_worker(worker_name)

    def register_worker(
        self,
        name: str,
        max_heartbeat_age: float = 60.0,
    ) -> WorkerHealthStatus:
        """
        Register a worker for health monitoring.

        Args:
            name: Worker name
            max_heartbeat_age: Maximum heartbeat age in seconds

        Returns:
            WorkerHealthStatus instance for the worker
        """
        status = WorkerHealthStatus(name=name)
        self._workers[name] = status

        checker = WorkerProcessHealthChecker(
            name=name,
            worker_status=status,
            max_heartbeat_age=max_heartbeat_age,
        )
        self._health_checker.add_sync_checker(checker)

        logger.info("worker_registered_for_health_check", worker_name=name)
        return status

    def update_worker_status(
        self,
        name: str,
        is_running: bool = True,
        metrics: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        """
        Update worker status and send heartbeat.

        Args:
            name: Worker name
            is_running: Whether worker is running
            metrics: Optional metrics to include
            error: Optional error message
        """
        if name not in self._workers:
            self._workers[name] = WorkerHealthStatus(name=name)

        status = self._workers[name]
        status.is_running = is_running
        status.last_heartbeat = time.time()

        if metrics:
            status.metrics.update(metrics)

        if error:
            status.error_count += 1
            status.last_error = error

    def heartbeat(self, name: Optional[str] = None, metrics: Optional[Dict[str, Any]] = None) -> None:
        """
        Send heartbeat for a worker.

        Args:
            name: Worker name (defaults to main worker)
            metrics: Optional metrics to include
        """
        worker_name = name or self.worker_name
        self.update_worker_status(worker_name, is_running=True, metrics=metrics)

    def get_health_status(self) -> HealthCheckResult:
        """
        Get current health status.

        Returns:
            HealthCheckResult with overall status
        """
        return self._health_checker.check_sync()

    def start(self) -> None:
        """Start the health check server in a background thread."""
        if self._running:
            logger.warning("health_check_server_already_running", port=self.port)
            return

        # Set up request handler with reference to this server
        HealthCheckRequestHandler.server_instance = self

        self._server = HTTPServer((self.host, self.port), HealthCheckRequestHandler)
        self._thread = Thread(target=self._serve, daemon=True)
        self._running = True
        self._thread.start()

        # Mark main worker as running
        self.update_worker_status(self.worker_name, is_running=True)

        logger.info(
            "health_check_server_started",
            host=self.host,
            port=self.port,
            worker_name=self.worker_name,
        )

    def _serve(self) -> None:
        """Serve HTTP requests (runs in background thread)."""
        if self._server:
            self._server.serve_forever()

    def stop(self) -> None:
        """Stop the health check server."""
        if not self._running:
            return

        self._running = False

        # Mark worker as not running
        if self.worker_name in self._workers:
            self._workers[self.worker_name].is_running = False

        if self._server:
            self._server.shutdown()
            self._server = None

        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None

        HealthCheckRequestHandler.server_instance = None

        logger.info("health_check_server_stopped", port=self.port)

    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running


# ============================================================================
# Module-level convenience functions
# ============================================================================

_default_server: Optional[WorkerHealthCheckServer] = None


async def start_health_check_server(
    host: str = "0.0.0.0",
    port: int = 8081,
    worker_name: str = "worker",
) -> WorkerHealthCheckServer:
    """
    Start a health check server (async convenience function).

    Args:
        host: Host to bind to
        port: Port to bind to
        worker_name: Name of the worker

    Returns:
        WorkerHealthCheckServer instance
    """
    global _default_server

    server = WorkerHealthCheckServer(host=host, port=port, worker_name=worker_name)
    server.start()
    _default_server = server

    return server


async def stop_health_check_server(server: Optional[WorkerHealthCheckServer] = None) -> None:
    """
    Stop a health check server (async convenience function).

    Args:
        server: Server to stop (uses default if not specified)
    """
    global _default_server

    target = server or _default_server
    if target:
        target.stop()

    if target == _default_server:
        _default_server = None


def get_default_server() -> Optional[WorkerHealthCheckServer]:
    """Get the default health check server instance."""
    return _default_server
