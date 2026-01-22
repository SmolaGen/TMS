"""
TMS - Transport Management System

FastAPI приложение для управления транспортом.
"""

from src.app import create_app
from src.config import settings

app = create_app(settings)


