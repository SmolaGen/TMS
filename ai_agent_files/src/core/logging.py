import logging
import sys
import structlog
from structlog.types import Processor

def configure_logging(log_level: str = "INFO"):
    """
    Настройка structlog для JSON-логирования в продакшене 
    и красивого вывода в консоль при разработке.
    """
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if sys.stderr.isatty():
        # Красивый вывод для терминала
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        # JSON вывод для продакшена (логи в Docker/K8s)
        processors.append(structlog.processors.format_exc_info)
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Настройка стандартного логгера для перехвата логов библиотек
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

def get_logger(name: str | None = None) -> structlog.BoundLogger:
    return structlog.get_logger(name)
