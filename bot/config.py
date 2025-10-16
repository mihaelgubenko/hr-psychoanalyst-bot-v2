"""
Конфигурация бота с поддержкой YAML и Pydantic
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotConfig(BaseSettings):
    """Конфигурация бота с валидацией"""
    
    # API ключи
    bot_token: str = Field(..., description="Telegram Bot Token")
    openai_api_key: str = Field(..., description="OpenAI API Key")
    payment_token: Optional[str] = Field(None, description="Payment Token")
    
    # Настройки токенов
    max_tokens: int = Field(4000, ge=100, le=8000, description="Maximum tokens")
    context_window: int = Field(3000, ge=500, le=6000, description="Context window size")
    response_tokens: int = Field(1000, ge=100, le=2000, description="Response tokens reserve")
    min_tokens: int = Field(100, ge=50, le=500, description="Minimum tokens")
    
    # Настройки сообщений
    max_message_length: int = Field(4000, ge=1000, le=8000, description="Max message length")
    max_conversation_length: int = Field(20, ge=5, le=50, description="Max conversation length")
    
    # Настройки кэширования
    cache_ttl: int = Field(3600, ge=300, le=86400, description="Cache TTL in seconds")
    cache_size: int = Field(1000, ge=100, le=10000, description="Cache size")
    
    # Настройки мониторинга
    monitoring_enabled: bool = Field(True, description="Enable monitoring")
    auto_optimization: bool = Field(True, description="Enable auto optimization")
    
    # Настройки базы данных
    database_path: str = Field("psychoanalyst.db", description="Database path")
    
    # Настройки логирования
    log_level: str = Field("INFO", description="Log level")
    log_file: Optional[str] = Field(None, description="Log file path")
    
    # Настройки безопасности
    rate_limiting_enabled: bool = Field(True, description="Enable rate limiting")
    max_requests_per_minute: int = Field(10, ge=1, le=100, description="Max requests per minute")
    
    # Настройки разработки
    debug: bool = Field(False, description="Debug mode")
    testing: bool = Field(False, description="Testing mode")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @validator('log_level')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of {valid_levels}')
        return v.upper()
    
    @validator('bot_token', 'openai_api_key')
    def validate_required_tokens(cls, v):
        if not v or v.startswith('your_') or v.endswith('_here'):
            raise ValueError('Please provide a valid API key')
        return v
    
    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'BotConfig':
        """Загрузка конфигурации из YAML файла"""
        yaml_file = Path(yaml_path)
        if not yaml_file.exists():
            raise FileNotFoundError(f"YAML config file not found: {yaml_path}")
        
        with open(yaml_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        # Извлекаем настройки из YAML
        bot_config = config_data.get('bot', {})
        ai_config = config_data.get('ai', {})
        db_config = config_data.get('database', {})
        log_config = config_data.get('logging', {})
        security_config = config_data.get('security', {})
        
        # Объединяем настройки
        merged_config = {
            **bot_config,
            'openai_api_key': os.getenv('OPENAI_API_KEY', ''),
            'bot_token': os.getenv('BOT_TOKEN', ''),
            'payment_token': os.getenv('PAYMENT_TOKEN'),
            'database_path': db_config.get('path', 'psychoanalyst.db'),
            'log_level': log_config.get('level', 'INFO'),
            'log_file': log_config.get('files', {}).get('main'),
            'rate_limiting_enabled': security_config.get('rate_limiting', {}).get('enabled', True),
            'max_requests_per_minute': security_config.get('rate_limiting', {}).get('requests_per_minute', 10),
        }
        
        return cls(**merged_config)
    
    def get_user_limits(self, user_type: str = "free") -> Dict[str, int]:
        """Получить лимиты для типа пользователя"""
        limits = {
            "free": {
                "max_tokens": self.max_tokens,
                "max_messages": 10,
                "cache_ttl": self.cache_ttl
            },
            "premium": {
                "max_tokens": self.max_tokens + 1000,
                "max_messages": 20,
                "cache_ttl": self.cache_ttl * 2
            }
        }
        return limits.get(user_type, limits["free"])
    
    def get_adaptive_limits(self, conversation_length: int, user_type: str = "free") -> Dict[str, int]:
        """Получить адаптивные лимиты на основе контекста"""
        base_limits = self.get_user_limits(user_type)
        
        # Адаптация на основе длины диалога
        if conversation_length > 15:
            base_limits["max_tokens"] = max(
                self.min_tokens,
                base_limits["max_tokens"] - 500
            )
        elif conversation_length < 5:
            base_limits["max_tokens"] = min(
                self.max_tokens + 500,
                base_limits["max_tokens"] + 200
            )
        
        return base_limits
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование конфигурации в словарь"""
        return self.model_dump()
    
    def is_valid(self) -> bool:
        """Проверка валидности конфигурации"""
        try:
            self.validate()
            return True
        except Exception:
            return False