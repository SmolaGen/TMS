"""
Конфигурация pytest для тестов.
Определяет фикстуры и предотвращает circular imports.
"""

import sys
import pytest
from unittest.mock import MagicMock

# Предотвращаем circular import между driver_service и dependencies
sys.modules['src.api.dependencies'] = MagicMock()


@pytest.fixture
def telegram_bot_token():
    """Токен Telegram бота для тестов."""
    return "test_bot_token_12345"


@pytest.fixture
def db_session():
    """Mock сессия базы данных для тестов."""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.refresh = MagicMock()
    session.delete = MagicMock()
    session.execute = MagicMock()
    return session
