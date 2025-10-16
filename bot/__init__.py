"""
HR-Психоаналитик Бот v2.0
Оптимизированная архитектура с интегрированным управлением токенами
"""

__version__ = "2.0.0"
__author__ = "HR-Психоаналитик"
__description__ = "Профессиональный HR-психоаналитик и карьерный консультант"

from .main import main
from .config import BotConfig
from .database import DatabaseManager

__all__ = ['main', 'BotConfig', 'DatabaseManager']