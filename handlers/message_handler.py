"""
Обработчик основных команд и сообщений бота
"""

import logging
from typing import Dict, Any, Optional
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

logger = logging.getLogger(__name__)

class MessageHandler:
    """Обработчик основных команд и сообщений"""
    
    def __init__(self, ai_client, database):
        self.ai_client = ai_client
        self.database = database
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработчик команды /start с главным меню"""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        user = update.effective_user
        
        # Очищаем предыдущие данные пользователя
        self.ai_client.clear_user_data(user.id)
        
        welcome_text = f"""
💫 **ПСИХОЛОГИЧЕСКАЯ ПОМОЩЬ И САМОПОЗНАНИЕ**

Шалом, {user.first_name or 'друг'}! 

Я помогу вам в духовном росте и самопознании.

**Мой подход основан на:**
• Психоанализе по авторской методике
• Работе с бессознательным и архетипами
• Принципах самоуважения и духовности

**Выберите формат работы:**
"""
        
        # Создаем клавиатуру с кнопками
        keyboard = [
            [InlineKeyboardButton("📊 Тест самооценки", callback_data='test_samoocenka')],
            [InlineKeyboardButton("💼 Личная консультация 🔒", callback_data='personal')],
            [InlineKeyboardButton("❓ Справка", callback_data='help')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text, 
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        return 'WAITING_MESSAGE'
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /help"""
        help_text = (
            "❓ *СПРАВКА*\n\n"
            "*Бесплатно:*\n"
            "• Тест самооценки (10 вопросов)\n"
            "• 10 follow\\-up вопросов после теста\n\n"
            "*Платно \\(в разработке\\):*\n"
            "• Личная консультация от 500₽\n\n"
            "*Команды:*\n"
            "/start \\- главное меню\n"
            "/test \\- тест самооценки\n"
            "/cancel \\- отменить\n"
            "/help \\- справка\n\n"
            "*Мой подход:*\n"
            "• Психоанализ по авторской методике\n"
            "• Работа с бессознательным\n"
            "• Духовные принципы\n\n"
            "Просто напишите свой вопрос!"
        )
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработчик команды /cancel - работает везде"""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        user = update.effective_user
        
        # Очищаем ВСЕ данные
        self.ai_client.clear_user_data(user.id)
        context.user_data.clear()
        
        # Очищаем тест с кнопками если активен
        if hasattr(self, 'analysis_handler'):
            self.analysis_handler.button_test_data.pop(user.id, None)
        
        # Очищаем трекер бесплатной консультации
        if hasattr(self, 'conversation_handler'):
            self.conversation_handler.free_consultation_tracker.pop(user.id, None)
        
        keyboard = [
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')],
            [InlineKeyboardButton("📊 Тест самооценки", callback_data='test_samoocenka')],
            [InlineKeyboardButton("💬 Консультация", callback_data='consultation')]
        ]
        
        await update.message.reply_text(
            "❌ **ОТМЕНЕНО**\n\n"
            "Все данные очищены.\n\n"
            "Что делать дальше?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    async def reset_bot(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /reset"""
        user = update.effective_user
        
        # Очищаем данные пользователя
        self.ai_client.clear_user_data(user.id)
        
        await update.message.reply_text(
            "🔄 Бот сброшен!\n\n"
            "Все ваши данные очищены. Начните заново с /start"
        )
    
    async def clear_memory(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Очистка памяти бота (только для админов)"""
        user = update.effective_user
        
        # Проверка на админа (можно настроить)
        if user.id != 123456789:  # Замените на ваш Telegram ID
            await update.message.reply_text("❌ У вас нет прав для этой команды")
            return
        
        # Очистка всех данных
        self.ai_client.response_cache.clear()
        
        # Очистка базы данных
        try:
            await self.database.clear_all_data()
            
            await update.message.reply_text(
                "✅ Память бота полностью очищена:\n"
                "• Очищена RAM память\n"
                "• Очищена база данных\n"
                "• Все диалоги удалены\n\n"
                "💡 Для очистки кэша Telegram перезапустите бота командой /start"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при очистке: {e}")
    
    # PREMIUM FEATURE: Свободная консультация перенесена в handlers/premium_consultation.py
    # async def start_consultation(...) - см. premium_consultation.py
    
    async def consultation_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Информация о личной консультации"""
        consultation_text = """
💫 **ЛИЧНАЯ КОНСУЛЬТАЦИЯ**

Я помогу вам пройти путь трансформации и раскрыть ваш истинный потенциал.

**Что я предлагаю:**

✨ **Повышение самооценки**
• Избавление от самокритики и сомнений
• Обретение уверенности в себе
• Принятие и любовь к себе

🎯 **Поиск предназначения**
• Обнаружение вашего уникального дара
• Определение жизненной миссии
• Построение карьеры по призванию

😌 **Освобождение от негатива**
• Проработка страхов и тревог
• Трансформация гнева в силу
• Освобождение от обид прошлого

💝 **Гармонизация отношений**
• Улучшение отношений с близкими
• Установление здоровых границ
• Привлечение качественных отношений

━━━━━━━━━━━━━━━━━━━━━━

**Формат работы:**
• Индивидуальные сессии 1-2 часа
• Онлайн/оффлайн (на ваш выбор)
• Персональная программа развития
• Поддержка между сессиями

**Стоимость:** обсуждается индивидуально

📞 **Записаться:**
Напишите мне: [Ваш Telegram/Email/Телефон]

Или просто напишите "Хочу консультацию" здесь!

━━━━━━━━━━━━━━━━━━━━━━
💙 Ваша трансформация начинается с первого шага!
"""
        
        await update.message.reply_text(consultation_text, parse_mode=ParseMode.MARKDOWN)
    
    async def get_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Получение статистики (только для админов)"""
        user = update.effective_user
        
        # Проверка на админа
        if user.id != 123456789:  # Замените на ваш Telegram ID
            await update.message.reply_text("❌ У вас нет прав для этой команды")
            return
        
        try:
            # Получаем статистику системы
            system_health = self.ai_client.get_system_health()
            
            stats_text = f"""
📊 **СТАТИСТИКА СИСТЕМЫ**

**Токены:**
• Всего запросов: {system_health['token_monitor']['total_requests']}
• Всего токенов: {system_health['token_monitor']['total_tokens']}
• Среднее на запрос: {system_health['token_monitor']['avg_tokens_per_request']:.1f}
• Процент обрезанных: {system_health['token_monitor']['truncation_rate']:.1%}

**Кэш:**
• Записей в кэше: {system_health['response_cache']['total_entries']}
• Процент попаданий: {system_health['response_cache']['hit_rate']:.1%}
• Использование памяти: {system_health['response_cache']['memory_usage_estimate']} байт

**Пользователи:**
• Активных: {system_health['token_monitor']['active_users']}

**Предупреждения:**
{chr(10).join(system_health['token_monitor']['optimization_alerts']) if system_health['token_monitor']['optimization_alerts'] else 'Нет'}
"""
            
            await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка получения статистики: {e}")
    
    async def optimize_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Оптимизация для пользователя"""
        user = update.effective_user
        
        try:
            # Получаем статус оптимизации
            optimization_status = self.ai_client.get_user_optimization_status(user.id)
            
            # Применяем оптимизацию
            optimization_result = self.ai_client.optimize_user_experience(user.id)
            
            result_text = f"""
🔧 **ОПТИМИЗАЦИЯ ЗАВЕРШЕНА**

**Примененные оптимизации:**
{chr(10).join([opt['description'] for opt in optimization_result.get('applied_optimizations', [])]) if optimization_result.get('applied_optimizations') else 'Нет автоматических оптимизаций'}

**Рекомендации:**
{chr(10).join([rec.description for rec in optimization_status['optimization_suggestions']]) if optimization_status['optimization_suggestions'] else 'Нет рекомендаций'}

**Статус кэша:**
• Записей: {optimization_status['cache_stats']['total_entries']}
• Попаданий: {optimization_status['cache_stats']['hit_rate']:.1%}
"""
            
            await update.message.reply_text(result_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка оптимизации: {e}")
    
    async def handle_button_click(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик нажатий на кнопки InlineKeyboard"""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        from handlers.analysis_handler import AnalysisHandler
        
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        # Проверяем, это кнопки теста, отмена или возврат?
        if data.startswith('btn_test_') or data == 'cancel_test' or data.startswith('back_to_q'):
            if hasattr(self, 'analysis_handler'):
                await self.analysis_handler.handle_button_test_answer(update, context)
            return
        
        # Завершение консультации
        if data == 'end_consultation':
            context.user_data.clear()
            await query.edit_message_text(
                "✅ **КОНСУЛЬТАЦИЯ ЗАВЕРШЕНА**\n\n"
                "Спасибо за доверие!\n\n"
                "Что делать дальше?\n"
                "/start - Главное меню\n"
                "/test - Тест самооценки",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Follow-up кнопки после теста
        if data == 'followup_start':
            await query.edit_message_text(
                f"💬 **ДОПОЛНИТЕЛЬНЫЕ ВОПРОСЫ**\n\n"
                f"У вас есть **{context.user_data.get('free_questions', 10)} бесплатных вопросов** по результату теста.\n\n"
                f"Просто напишите свой вопрос, и я отвечу! 📝",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        if data == 'test_restart':
            await query.edit_message_text("🔄 Перезапускаю тест...\n\nИспользуйте: /test")
            return
        
        if data == 'main_menu':
            # Возврат в главное меню
            context.user_data.clear()
            await query.edit_message_text(
                "🏠 Возвращаю вас в главное меню...\n\nИспользуйте: /start",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        if data == 'test_samoocenka':
            # Запускаем тест с кнопками напрямую
            await query.edit_message_text(
                "📊 **ТЕСТ САМООЦЕНКИ**\n\n"
                "Отлично! Запускаю тест с кнопками.\n"
                "Используйте команду: /test",
                parse_mode=ParseMode.MARKDOWN
            )
            
        elif data == 'premium':
            # Премиум доступ (в разработке)
            premium_text = """
⭐ **ПРЕМИУМ ДОСТУП**
*(в разработке)*

**Что будет включено:**
✨ Полный тест самооценки (30 вопросов)
✨ Неограниченные консультации
✨ Персональный план развития
✨ Дневник с аналитикой прогресса
✨ Все упражнения из книги
✨ Экспорт результатов в PDF

**Цена:** 500₽/месяц

🔔 *Уведомим вас о запуске!*

/start - Вернуться в меню
"""
            await query.edit_message_text(premium_text, parse_mode=ParseMode.MARKDOWN)
            
        elif data == 'personal':
            # Личная консультация (в разработке)
            personal_text = """
💼 **ЛИЧНАЯ КОНСУЛЬТАЦИЯ**
🔒 *В разработке*

**Скоро будет доступно:**

💬 **Свободный диалог с психологом**
• На основе книги "Восхождение"
• GPT-4 для сложных случаев
• GPT-3.5 для простых вопросов
• До 15 вопросов в сессии

✨ **Что включено:**
• Глубокий анализ вашей ситуации
• Персональные рекомендации
• Практические упражнения
• Кнопка "Назад" для уточнения

💰 **Ориентировочная стоимость:**
• Простые вопросы: 500₽ (до 7 вопросов)
• Сложные случаи: 2000₽ (до 15 вопросов)
• Личная встреча: от 5000₽

📅 **Когда запустим:**
Ориентировочно через 2-3 недели

🔔 *Хотите узнать о запуске первыми?*
Напишите: "Записать меня на консультацию"

/start - Вернуться в меню
"""
            await query.edit_message_text(personal_text, parse_mode=ParseMode.MARKDOWN)
            
        elif data == 'help':
            # Справка
            help_text = """
❓ **СПРАВКА**

**🎯 С ЧЕГО НАЧАТЬ:**

1️⃣ Пройдите /test
   → Тест самооценки с кнопками (3 минуты)

2️⃣ Задайте свой вопрос
   → Получите персональные рекомендации

**💬 КОМАНДЫ:**
/start - Главное меню
/test - Тест самооценки
/help - Эта справка
/cancel - Отменить

**🧠 МОЙ ПОДХОД:**
• Психоанализ по авторской методике
• Работа с бессознательным
• Духовные принципы самопознания
• Практические упражнения

/start - Вернуться в меню
"""
            await query.edit_message_text(help_text, parse_mode=ParseMode.MARKDOWN)