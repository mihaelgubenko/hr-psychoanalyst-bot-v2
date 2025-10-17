"""
═══════════════════════════════════════════════════════════════════
PREMIUM FEATURE: СВОБОДНАЯ КОНСУЛЬТАЦИЯ
═══════════════════════════════════════════════════════════════════

Этот файл содержит код для ПЛАТНОЙ свободной консультации.

📍 ГДЕ ИСПОЛЬЗУЕТСЯ:
   - Платная версия бота (GPT-4 для сложных, GPT-3.5-turbo для простых)
   - Трекер: 7 вопросов (простые) / 15 вопросов (сложные)
   - После теста: 10 бесплатных follow-up вопросов

🎯 ФУНКЦИОНАЛ:
   - Свободный диалог на основе книги "Восхождение"
   - Автоопределение сложности вопроса
   - Переключение между GPT-3.5 и GPT-4
   - Трекер бесплатных/платных вопросов
   - Кнопка "Назад" для возврата к предыдущему ответу
   - Предложение личной консультации при исчерпании лимита

📅 ДАТА СОЗДАНИЯ: 2025-10-17
📝 ПРИЧИНА ДЕАКТИВАЦИИ: Оптимизация расходов на токены, переход на бесплатный тест

🔄 КАК ВКЛЮЧИТЬ:
   1. Раскомментировать импорт в handlers/message_handler.py
   2. Добавить кнопку "Консультация" в главное меню
   3. Подключить обработчики в core/bot.py
   4. Настроить лимиты в config/settings.yaml

═══════════════════════════════════════════════════════════════════
"""

import logging
from typing import Dict, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

logger = logging.getLogger(__name__)

class PremiumConsultationHandler:
    """
    Обработчик платной свободной консультации
    
    Основан на книге "Восхождение" с интеграцией психоанализа.
    Использует адаптивный выбор модели OpenAI в зависимости от сложности вопроса.
    """
    
    def __init__(self, ai_client, database):
        self.ai_client = ai_client
        self.database = database
        self.consultation_history = {}  # user_id -> list of messages
        self.question_tracker = {}  # user_id -> {'count': int, 'max': int, 'type': 'simple'|'complex'}
    
    async def start_consultation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начало свободной консультации"""
        consultation_intro = """
💬 **ПСИХОЛОГИЧЕСКАЯ КОНСУЛЬТАЦИЯ**

Шалом! Я готов вам помочь 🙏

**Я консультирую по темам:**
✨ Самооценка и уверенность в себе
😰 Работа со страхами и тревогами
😤 Освобождение от гнева и обид
🎯 Поиск предназначения и смысла жизни
💝 Отношения с собой и другими
🌱 Духовное и личностное развитие

**Мой подход основан на:**
📖 Принципах самопознания и духовного роста (книга "Восхождение")
🧠 Психоанализе (Фрейд, Юнг)
🎯 Современных методиках работы с эмоциями
💡 Эмпатии и глубоком понимании

**Как это работает:**
1️⃣ Опишите, что вас беспокоит
2️⃣ Я задам уточняющие вопросы (если нужно)
3️⃣ Дам анализ и персональные рекомендации
4️⃣ Предложу практические упражнения

💬 *Просто напишите, что на душе, и я помогу!*

**Примеры вопросов:**
• "Боюсь что меня осудят"
• "Не знаю свое предназначение"  
• "Есть обида на родителей"
• "Хочу повысить самооценку"
• "Чувствую гнев внутри"

---
💎 *Для глубокой работы доступна личная консультация* → /personal
"""
        await update.message.reply_text(consultation_intro, parse_mode=ParseMode.MARKDOWN)
        
        # Инициализируем трекер для пользователя
        user_id = update.effective_user.id
        if user_id not in self.question_tracker:
            self.question_tracker[user_id] = {
                'count': 0,
                'max': 7,  # По умолчанию 7 для простых вопросов
                'type': 'simple'
            }
    
    async def handle_consultation_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Обработка сообщений в консультации"""
        user = update.effective_user
        text = update.message.text.strip()
        
        if not text:
            await update.message.reply_text("Пожалуйста, напишите что-то конкретное.")
            return 'WAITING_MESSAGE'
        
        # Проверяем лимит вопросов
        tracker = self.question_tracker.get(user.id)
        if tracker and tracker['count'] >= tracker['max']:
            # Лимит исчерпан
            keyboard = [
                [InlineKeyboardButton("👤 Личная консультация", callback_data='personal')],
                [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
            ]
            
            await update.message.reply_text(
                f"⚠️ **Лимит вопросов исчерпан ({tracker['count']}/{tracker['max']})**\n\n"
                f"Хотите продолжить глубокую работу?\n\n"
                f"💎 **Личная консультация:**\n"
                f"• Неограниченные вопросы\n"
                f"• Персональный план\n"
                f"• Глубокий разбор\n\n"
                f"От 2000₽",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            return 'WAITING_MESSAGE'
        
        # Определяем сложность вопроса
        is_complex = self._is_complex_question(text)
        
        # Обновляем трекер
        if is_complex and tracker['type'] == 'simple':
            # Переключаемся на сложный режим
            tracker['type'] = 'complex'
            tracker['max'] = 15
        
        tracker['count'] += 1
        
        # Получаем ответ от ИИ
        try:
            # Показываем, что бот думает
            thinking_msg = await update.message.reply_text("🤔 Думаю...")
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            # Выбираем модель
            model = "gpt-4" if is_complex else "gpt-3.5-turbo"
            
            # Получаем ответ
            response = await self._get_consultation_response(user.id, text, model)
            
            # Удаляем индикатор
            await thinking_msg.delete()
            
            # Отправляем ответ
            await self._send_response(update, response)
            
            # Добавляем кнопки управления
            keyboard = [
                [InlineKeyboardButton("⬅️ Назад", callback_data='consultation_back')],
                [InlineKeyboardButton("❌ Завершить", callback_data='end_consultation')],
                [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
            ]
            
            remaining = tracker['max'] - tracker['count']
            await update.message.reply_text(
                f"💡 Осталось вопросов: **{remaining}/{tracker['max']}** ({tracker['type']})\n"
                f"─────────────────",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Ошибка получения ответа ИИ: {e}")
            await update.message.reply_text(
                "Извините, произошла ошибка при обработке запроса. Попробуйте позже."
            )
        
        return 'WAITING_MESSAGE'
    
    def _is_complex_question(self, text: str) -> bool:
        """
        Определение сложности вопроса
        
        СЛОЖНЫЙ вопрос:
        - Длина > 50 слов
        - Эмоциональные маркеры (боюсь, тревога, депрессия)
        - Личная история
        - Глубокий анализ
        
        ПРОСТОЙ вопрос:
        - "Что такое...?"
        - "Как начать...?"
        - FAQ
        """
        text_lower = text.lower()
        
        # Проверка длины
        word_count = len(text.split())
        if word_count > 50:
            return True
        
        # Эмоциональные маркеры
        emotional_keywords = [
            'боюсь', 'страх', 'тревога', 'депрессия', 'паника',
            'грусть', 'одиночество', 'больно', 'страшно', 'плохо',
            'развод', 'смерть', 'потеря', 'травма', 'насилие'
        ]
        
        if any(keyword in text_lower for keyword in emotional_keywords):
            return True
        
        # Личная история (использование "я", "мой", "мне")
        personal_markers = ['я ', 'мне ', 'мой', 'моя', 'мои', 'со мной']
        if any(marker in text_lower for marker in personal_markers):
            return True
        
        # Простые вопросы
        simple_questions = [
            'что такое', 'как начать', 'объясни', 'расскажи о',
            'в чем разница', 'как работает'
        ]
        
        if any(q in text_lower for q in simple_questions):
            return False
        
        # По умолчанию считаем сложным
        return True
    
    async def _get_consultation_response(self, user_id: int, message: str, model: str) -> str:
        """Получение ответа от ИИ с выбором модели"""
        
        # Формируем контекст
        conversation_context = self.consultation_history.get(user_id, [])
        context = {
            'conversation': '\n'.join(conversation_context[-5:]),  # Последние 5 сообщений
            'user_message': message,
            'message_count': len(conversation_context)
        }
        
        # Получаем ответ от ИИ
        ai_response = await self.ai_client.get_response(
            prompt=message,
            user_id=user_id,
            prompt_type='consultation',
            context=context,
            model=model  # Передаем выбранную модель
        )
        
        # Сохраняем в историю
        if user_id not in self.consultation_history:
            self.consultation_history[user_id] = []
        
        self.consultation_history[user_id].append(f"USER: {message}")
        self.consultation_history[user_id].append(f"AI: {ai_response.content}")
        
        return ai_response.content
    
    async def _send_response(self, update: Update, response: str):
        """Отправка ответа пользователю"""
        
        try:
            # Разбиваем длинный ответ на части
            max_length = 4000
            if len(response) <= max_length:
                await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            else:
                parts = [response[i:i+max_length] for i in range(0, len(response), max_length)]
                for i, part in enumerate(parts):
                    prefix = f"**Ответ (часть {i+1}/{len(parts)}):**\n\n" if i > 0 else ""
                    await update.message.reply_text(prefix + part, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            # Если Markdown не работает, отправляем как обычный текст
            logger.error(f"Ошибка отправки с Markdown: {e}")
            try:
                await update.message.reply_text(response)
            except Exception as e2:
                logger.error(f"Критическая ошибка отправки сообщения: {e2}")
                await update.message.reply_text("😔 Извините, произошла ошибка при отправке ответа.")
    
    async def handle_back_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка кнопки 'Назад'"""
        user_id = update.effective_user.id
        
        # Получаем историю
        history = self.consultation_history.get(user_id, [])
        
        if len(history) < 2:
            await update.callback_query.answer("Нет предыдущих сообщений")
            return
        
        # Возвращаемся к предыдущему ответу
        prev_response = history[-2] if history[-2].startswith("AI:") else history[-3]
        prev_response = prev_response.replace("AI: ", "")
        
        # Уменьшаем счетчик
        if user_id in self.question_tracker:
            self.question_tracker[user_id]['count'] = max(0, self.question_tracker[user_id]['count'] - 1)
        
        await update.callback_query.edit_message_text(
            f"⬅️ **ПРЕДЫДУЩИЙ ОТВЕТ:**\n\n{prev_response}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    def clear_user_data(self, user_id: int):
        """Очистка данных пользователя"""
        self.consultation_history.pop(user_id, None)
        self.question_tracker.pop(user_id, None)

