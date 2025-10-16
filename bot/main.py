#!/usr/bin/env python3
"""
HR-Психоаналитик Бот v2.0 - Главная точка входа
Оптимизированная архитектура с интегрированным управлением токенами
"""

import asyncio
import logging
import sys
import signal
from pathlib import Path
from typing import Optional

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.config import BotConfig
from bot.database import DatabaseManager
from core.bot import HRPsychoanalystBot

# Настройка логирования
def setup_logging(config: BotConfig):
    """Настройка системы логирования"""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    # Добавляем файловый обработчик только если указан файл
    log_file = config.get('log_file')
    if log_file:
        try:
            # Создаем папку для логов если нужно
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            handlers.append(logging.FileHandler(log_file))
        except Exception as e:
            print(f"Не удалось создать файловый обработчик логов: {e}")
    
    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format=log_format,
        handlers=handlers
    )
    
    # Настройка логирования для внешних библиотек
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)

class BotApplication:
    """Главное приложение бота с управлением жизненным циклом"""
    
    def __init__(self):
        self.config: Optional[BotConfig] = None
        self.database: Optional[DatabaseManager] = None
        self.bot: Optional[HRPsychoanalystBot] = None
        self.running = False
        
    async def initialize(self) -> bool:
        """Инициализация приложения"""
        try:
            # Загрузка конфигурации
            self.config = BotConfig.from_yaml("config/settings.yaml")
            
            # Настройка логирования
            setup_logging(self.config)
            logger = logging.getLogger(__name__)
            
            logger.info(f"Инициализация HR-Психоаналитик Бота v{self.config.get('version', '2.0')}")
            
            # Инициализация базы данных
            self.database = DatabaseManager(self.config)
            if not await self.database.init_database():
                logger.error("Не удалось инициализировать базу данных")
                return False
            
            # Инициализация бота
            self.bot = HRPsychoanalystBot(self.config, self.database)
            
            logger.info("Приложение инициализировано успешно")
            return True
            
        except Exception as e:
            try:
                logger = logging.getLogger(__name__)
                logger.error(f"Ошибка инициализации: {e}")
            except:
                print(f"Ошибка инициализации: {e}")
            return False
    
    async def start(self) -> bool:
        """Запуск приложения"""
        try:
            logger = logging.getLogger(__name__)
            
            if not self.bot:
                logger.error("Бот не инициализирован")
                return False
            
            # Настройка обработчиков сигналов
            self._setup_signal_handlers()
            
            # Запуск бота
            await self.bot.start()
            self.running = True
            
            logger.info("HR-Психоаналитик Бот v2.0 запущен успешно")
            return True
            
        except Exception as e:
            try:
                logger = logging.getLogger(__name__)
                logger.error(f"Ошибка запуска: {e}")
            except:
                print(f"Ошибка запуска: {e}")
            return False
    
    async def stop(self) -> bool:
        """Остановка приложения"""
        try:
            logger = logging.getLogger(__name__)
            
            if self.bot:
                await self.bot.stop()
            
            if self.database:
                await self.database.close()
            
            self.running = False
            logger.info("Приложение остановлено")
            return True
            
        except Exception as e:
            try:
                logger = logging.getLogger(__name__)
                logger.error(f"Ошибка остановки: {e}")
            except:
                print(f"Ошибка остановки: {e}")
            return False
    
    def _setup_signal_handlers(self):
        """Настройка обработчиков сигналов для graceful shutdown"""
        def signal_handler(signum, frame):
            logger = logging.getLogger(__name__)
            logger.info(f"Получен сигнал {signum}, инициируется остановка...")
            asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def run(self):
        """Основной цикл приложения"""
        try:
            # Инициализация
            if not await self.initialize():
                logger.error("Не удалось инициализировать приложение")
                return False
            
            # Запуск
            if not await self.start():
                logger.error("Не удалось запустить приложение")
                return False
            
            # Основной цикл
            while self.running:
                await asyncio.sleep(1)
            
            return True
            
        except KeyboardInterrupt:
            logger = logging.getLogger(__name__)
            logger.info("Получен сигнал прерывания")
            return True
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Критическая ошибка: {e}")
            return False
        finally:
            await self.stop()

async def main():
    """Главная функция"""
    app = BotApplication()
    success = await app.run()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nПрограмма прервана пользователем")
        sys.exit(0)
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        sys.exit(1)