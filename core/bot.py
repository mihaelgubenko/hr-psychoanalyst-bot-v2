"""
Основной класс бота с интегрированным управлением токенами
"""

import logging
from typing import Dict, Any, Optional
from telegram import Update
from telegram.ext import Application, ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler as TGMessageHandler, ConversationHandler, CallbackQueryHandler, filters

# Импорт BotConfig будет сделан локально, чтобы избежать циклических импортов
from bot.database import DatabaseManager
from ai.openai_client import OpenAIClient
from ai.adaptive_prompt_manager import PromptType
from handlers.message_handler import MessageHandler as BotMessageHandler
from handlers.analysis_handler import AnalysisHandler
from handlers.conversation_handler import BotConversationHandler

logger = logging.getLogger(__name__)

class HRPsychoanalystBot:
    """Основной класс HR-Психоаналитик бота"""
    
    def __init__(self, config: Any, database=None):
        self.config = config
        self.db = DatabaseManager(config)
        self.ai_client = OpenAIClient(config)
        
        # Инициализируем обработчики
        self.message_handler = BotMessageHandler(self.ai_client, self.db)
        self.analysis_handler = AnalysisHandler(self.ai_client, self.db)
        self.conversation_handler = BotConversationHandler(self.ai_client, self.db)
        
        # Даем message_handler доступ к analysis_handler для кнопок теста
        self.message_handler.analysis_handler = self.analysis_handler
        
        # Создаем приложение
        self.application = ApplicationBuilder().token(config.bot_token).build()
        
        # Настраиваем обработчики
        self._setup_handlers()
        
        logger.info("HR-Психоаналитик бот инициализирован")
    
    def _setup_handlers(self):
        """Настройка обработчиков команд и сообщений"""
        
        # Основные команды
        self.application.add_handler(CommandHandler('start', self.message_handler.start))
        self.application.add_handler(CommandHandler('help', self.message_handler.help_command))
        self.application.add_handler(CommandHandler('cancel', self.message_handler.cancel))
        self.application.add_handler(CommandHandler('reset', self.message_handler.reset_bot))
        
        # Только тест с кнопками (самый удобный!)
        self.application.add_handler(CommandHandler('test', self.analysis_handler.start_button_test))
        self.application.add_handler(CommandHandler('test_buttons', self.analysis_handler.start_button_test))  # Алиас
        
        # Консультация
        self.application.add_handler(CommandHandler('consultation', self.message_handler.start_consultation))
        
        # Административные команды
        self.application.add_handler(CommandHandler('clear', self.message_handler.clear_memory))
        self.application.add_handler(CommandHandler('stats', self.message_handler.get_stats))
        self.application.add_handler(CommandHandler('optimize', self.message_handler.optimize_user))
        
        # Обработчик нажатий на кнопки (InlineKeyboard)
        self.application.add_handler(CallbackQueryHandler(self.message_handler.handle_button_click))
        
        # ВАЖНО: Обработчики состояний ПЕРЕД обычным message handler!
        # Иначе обычный handler перехватывает все сообщения
        self._setup_conversation_handlers()
        
        # Обработчик обычных сообщений в группе 1 (низкий приоритет, ПОСЛЕДНИМ!)
        self.application.add_handler(
            TGMessageHandler(filters.TEXT & ~filters.COMMAND, self.conversation_handler.handle_message),
            group=1
        )
    
    def _setup_conversation_handlers(self):
        """Настройка обработчиков состояний диалога"""
        # ConversationHandler удалены - используем только кнопки и свободный диалог
        pass
    
    async def start(self):
        """Запуск бота"""
        try:
            # Инициализируем базу данных
            await self.db.init_database()
            
            # Запускаем бота
            logger.info("Запуск HR-Психоаналитик бота...")
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            logger.info("Бот успешно запущен")
            
        except Exception as e:
            logger.error(f"Ошибка при запуске бота: {e}")
            raise
    
    async def stop(self):
        """Остановка бота"""
        try:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            logger.info("Бот остановлен")
        except Exception as e:
            logger.error(f"Ошибка при остановке бота: {e}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Получение статуса здоровья бота"""
        return {
            'bot_status': 'running',
            'ai_client': self.ai_client.get_system_health(),
            'database': self.db.get_health_status(),
            'config': {
                'max_tokens': self.config.max_tokens,
                'cache_enabled': True,
                'monitoring_enabled': self.config.monitoring_enabled
            }
        }
    
    def get_analytics(self) -> Dict[str, Any]:
        """Получение аналитики бота"""
        return self.ai_client.export_analytics()
    
    def optimize_system(self) -> Dict[str, Any]:
        """Оптимизация системы"""
        # Оптимизируем кэш
        cache_optimization = self.ai_client.response_cache.optimize_cache()
        
        # Получаем системную статистику
        system_health = self.get_health_status()
        
        return {
            'cache_optimization': cache_optimization,
            'system_health': system_health,
            'recommendations': self._get_system_recommendations()
        }
    
    def _get_system_recommendations(self) -> list:
        """Получение рекомендаций по оптимизации системы"""
        recommendations = []
        
        # Проверяем статистику кэша
        cache_stats = self.ai_client.response_cache.get_cache_stats()
        if cache_stats['hit_rate'] < 0.3:
            recommendations.append("Низкий процент попаданий в кэш. Рассмотрите увеличение TTL")
        
        # Проверяем статистику токенов
        token_stats = self.ai_client.token_monitor.get_system_health()
        if token_stats['truncation_rate'] > 0.15:
            recommendations.append("Высокий процент обрезанных ответов. Рекомендуется оптимизация промптов")
        
        return recommendations