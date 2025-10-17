"""
Обработчик диалогов с интегрированным управлением токенами
"""

import logging
from typing import Dict, Any, Optional
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ai.adaptive_prompt_manager import PromptType
from ai.security_manager import SecurityManager

logger = logging.getLogger(__name__)

class BotConversationHandler:
    """Обработчик диалогов с умным управлением контекстом"""
    
    def __init__(self, ai_client, database):
        self.ai_client = ai_client
        self.database = database
        self.conversation_history = {}  # user_id -> list of messages
        self.free_consultation_tracker = {}  # user_id -> {'count': int, 'max': 7}
        self.security_manager = SecurityManager()  # Менеджер безопасности
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Обработка входящих сообщений"""
        user = update.effective_user
        text = update.message.text.strip()
        
        if not text:
            await update.message.reply_text("Пожалуйста, напишите что-то конкретное.")
            return 'WAITING_MESSAGE'
        
        # 🔒 ПРОВЕРКИ БЕЗОПАСНОСТИ
        
        # 1. Проверка поведения пользователя
        is_allowed, reason = self.security_manager.check_user_behavior(user.id)
        if not is_allowed:
            await update.message.reply_text(f"⚠️ {reason}")
            return 'WAITING_MESSAGE'
        
        # 2. Проверка rate limiting
        is_allowed, reason = self.security_manager.check_rate_limit(user.id)
        if not is_allowed:
            await update.message.reply_text(f"⏰ {reason}")
            return 'WAITING_MESSAGE'
        
        # 3. Проверка на спам
        is_spam, reason = self.security_manager.check_spam_patterns(user.id, text)
        if is_spam:
            await update.message.reply_text(f"🚫 {reason}")
            return 'WAITING_MESSAGE'
        
        # Обработка запроса на консультацию
        if 'записать' in text.lower() and 'консультац' in text.lower():
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            
            keyboard = [
                [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')],
                [InlineKeyboardButton("📊 Тест самооценки", callback_data='test_samoocenka')]
            ]
            
            await update.message.reply_text(
                "📝 **ЗАПИСЬ НА КОНСУЛЬТАЦИЮ**\n\n"
                "Спасибо за интерес!\n\n"
                "💼 **Для записи свяжитесь:**\n"
                "📧 Email: [укажите ваш email]\n"
                "📱 Telegram: @[ваш username]\n"
                "☎️ Телефон: [укажите номер]\n\n"
                "🔔 Мы свяжемся с вами в ближайшее время!",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            return 'WAITING_MESSAGE'
        
        # Обработка команд "1" и "2" (из справки)
        if text.strip() == "1":
            await update.message.reply_text(
                "📊 **ТЕСТ САМООЦЕНКИ**\n\n"
                "Отлично! Запускаю тест с кнопками.\n"
                "Используйте команду: /test",
                parse_mode=ParseMode.MARKDOWN
            )
            return 'WAITING_MESSAGE'
            
        elif text.strip() == "2":
            # Запуск структурированной консультации
            await self._start_structured_consultation(update, context)
            return 'STRUCTURED_CONSULTATION'
        
        # Проверяем, находимся ли в режиме структурированной консультации
        if context.user_data.get('consultation_type') == 'structured':
            # Обработка команд отмены и возврата
            text_lower = text.lower().strip()
            if text_lower in ['отмена', 'отменить', 'cancel', 'стоп', 'хватит']:
                context.user_data.clear()
                await update.message.reply_text(
                    "❌ **КОНСУЛЬТАЦИЯ ОТМЕНЕНА**\n\n"
                    "Ваши ответы не сохранены.\n\n"
                    "Что делать дальше?\n"
                    "/start - Главное меню\n"
                    "/test - Тест самооценки\n"
                    "/consultation - Начать консультацию заново",
                    parse_mode=ParseMode.MARKDOWN
                )
                return 'WAITING_MESSAGE'
            
            if text_lower in ['назад', 'back', 'предыдущий']:
                current_q = context.user_data.get('current_question', 0)
                if current_q > 0:
                    # Возвращаемся к предыдущему вопросу
                    prev_question = current_q - 1
                    context.user_data['current_question'] = prev_question
                    
                    # Удаляем последний ответ
                    answers = context.user_data.get('consultation_answers', [])
                    if len(answers) > prev_question:
                        context.user_data['consultation_answers'] = answers[:prev_question]
                    
                    await self._ask_consultation_question(update, context)
                    return 'STRUCTURED_CONSULTATION'
                else:
                    await update.message.reply_text("Вы на первом вопросе. Отменить консультацию: напишите 'отмена'")
                    return 'STRUCTURED_CONSULTATION'
            
            return await self._handle_consultation_answer(update, context)
        
        # Инициализируем историю пользователя
        if user.id not in self.conversation_history:
            self.conversation_history[user.id] = []
        
        # Инициализируем трекер бесплатной консультации
        if user.id not in self.free_consultation_tracker:
            self.free_consultation_tracker[user.id] = {'count': 0, 'max': 7}
        
        # Проверяем лимит бесплатной консультации (если не follow-up режим)
        if not context.user_data.get('followup_mode'):
            tracker = self.free_consultation_tracker[user.id]
            if tracker['count'] >= tracker['max']:
                # Лимит исчерпан
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                
                keyboard = [
                    [InlineKeyboardButton("💼 Личная консультация", callback_data='personal')],
                    [InlineKeyboardButton("📊 Пройти тест", callback_data='test_samoocenka')],
                    [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
                ]
                
                await update.message.reply_text(
                    f"⚠️ **Бесплатная консультация исчерпана ({tracker['count']}/{tracker['max']})**\n\n"
                    f"Хотите продолжить?\n\n"
                    f"💼 **Личная консультация (в разработке):**\n"
                    f"• До 15 вопросов в сессии\n"
                    f"• GPT-4 для сложных случаев\n"
                    f"• Кнопка 'Назад' для уточнения\n\n"
                    f"Ориентировочно: от 500₽",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=ParseMode.MARKDOWN
                )
                return 'WAITING_MESSAGE'
        
        # Добавляем сообщение в историю
        self.conversation_history[user.id].append(text)
        
        # Ограничиваем длину истории
        if len(self.conversation_history[user.id]) > 20:
            self.conversation_history[user.id] = self.conversation_history[user.id][-20:]
        
        # Анализируем паттерны речи
        patterns = self._analyze_speech_patterns(text)
        
        # Обрабатываем специальные случаи
        if patterns['cancellation']:
            return await self._handle_cancellation(update, context)
        
        if patterns['topic_change']:
            return await self._handle_topic_change(update, context)
        
        if patterns['self_introduction_request']:
            return await self._handle_self_introduction(update, context)
        
        # ПРИОРИТЕТ: Если пользователь задает прямой вопрос - отвечаем сразу
        if self._is_direct_question(text):
            response_type = self._determine_response_type(patterns, text)
            try:
                response = await self._get_ai_response(user.id, text, response_type)
                await self._send_response(update, response)
                return 'WAITING_MESSAGE'
            except Exception as e:
                logger.error(f"Ошибка получения ответа ИИ: {e}")
                await update.message.reply_text(
                    "Извините, произошла ошибка при обработке запроса. Попробуйте позже."
                )
                return 'WAITING_MESSAGE'
        
        # Определяем тип ответа
        response_type = self._determine_response_type(patterns, text)
        
        # Получаем ответ от ИИ
        try:
            # Показываем, что бот думает
            thinking_msg = await update.message.reply_text("🤔 Думаю...")
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            # Получаем ответ от ИИ (используем GPT-3.5 для бесплатной консультации)
            response = await self._get_ai_response(user.id, text, response_type)
            
            # 4. Проверка лимита токенов (приблизительная оценка)
            estimated_tokens = len(text.split()) * 1.3 + len(response.split()) * 1.3  # Примерная оценка
            is_allowed, reason = self.security_manager.check_token_limit(user.id, int(estimated_tokens))
            if not is_allowed:
                await thinking_msg.delete()
                await update.message.reply_text(f"💰 {reason}")
                return 'WAITING_MESSAGE'
            
            # Удаляем индикатор
            await thinking_msg.delete()
            
            # Отправляем ответ
            await self._send_response(update, response)
            
            # Увеличиваем счетчик бесплатной консультации (если не follow-up режим)
            if not context.user_data.get('followup_mode'):
                self.free_consultation_tracker[user.id]['count'] += 1
                remaining = self.free_consultation_tracker[user.id]['max'] - self.free_consultation_tracker[user.id]['count']
                
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                
                # Кнопки управления
                keyboard = [
                    [InlineKeyboardButton("❌ Завершить", callback_data='end_consultation')],
                    [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
                ]
                
                await update.message.reply_text(
                    f"💡 **Бесплатная консультация:** {self.free_consultation_tracker[user.id]['count']}/{self.free_consultation_tracker[user.id]['max']}\n"
                    f"Осталось: **{remaining} вопросов**\n"
                    f"─────────────────",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=ParseMode.MARKDOWN
                )
            
            # PREMIUM FEATURE: Кнопки консультации отключены (функция перенесена в premium_consultation.py)
            
            # FOLLOW-UP РЕЖИМ: Уменьшаем счетчик бесплатных вопросов (после теста)
            if context.user_data.get('followup_mode'):
                free_q = context.user_data.get('free_questions', 0)
                if free_q > 0:
                    free_q -= 1
                    context.user_data['free_questions'] = free_q
                    
                    if free_q > 0:
                        await update.message.reply_text(
                            f"💡 Осталось бесплатных вопросов: **{free_q}/10**",
                            parse_mode=ParseMode.MARKDOWN
                        )
                    else:
                        # Закончились вопросы - предлагаем платную консультацию
                        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                        
                        keyboard = [
                            [InlineKeyboardButton("💼 Личная консультация", callback_data='personal')],
                            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
                        ]
                        
                        await update.message.reply_text(
                            "⚠️ **Бесплатные вопросы закончились (10/10)**\n\n"
                            "Хотите продолжить работу?\n\n"
                            "💼 **Личная консультация (в разработке):**\n"
                            "• До 15 вопросов в сессии\n"
                            "• GPT-4 для сложных случаев\n"
                            "• Кнопка 'Назад' для уточнения\n\n"
                            "Ориентировочно: от 500₽",
                            reply_markup=InlineKeyboardMarkup(keyboard),
                            parse_mode=ParseMode.MARKDOWN
                        )
                        context.user_data.pop('followup_mode', None)
            
        except Exception as e:
            logger.error(f"Ошибка получения ответа ИИ: {e}")
            await update.message.reply_text(
                "Извините, произошла ошибка при обработке запроса. Попробуйте позже."
            )
        
        return 'WAITING_MESSAGE'
    
    async def _start_structured_consultation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запуск структурированной консультации"""
        user = update.effective_user
        
        # Инициализируем данные консультации
        context.user_data['consultation_type'] = 'structured'
        context.user_data['consultation_answers'] = []
        context.user_data['current_question'] = 0
        context.user_data['consultation_questions'] = [
            "Что вас больше всего беспокоит в себе? (1-2 предложения)",
            "Какие качества вы хотели бы развить? (1-2 предложения)", 
            "Что мешает вам чувствовать уверенность? (1-2 предложения)",
            "Как вы обычно справляетесь со стрессом? (1-2 предложения)",
            "Что помогает вам чувствовать себя лучше? (1-2 предложения)",
            "Какие у вас есть мечты или цели? (1-2 предложения)",
            "Что бы вы хотели изменить в своей жизни? (1-2 предложения)"
        ]
        
        intro_text = """
💬 **БЕСПЛАТНАЯ КОНСУЛЬТАЦИЯ** (7 вопросов)

Отвечайте кратко на каждый вопрос (1-2 предложения).

**Принципы:** Книга "Восхождение"
**Модель:** GPT-3.5 (экономичная)
**Результат:** Персональные рекомендации

Начинаем! ⬇️
"""
        
        # Проверяем, это callback query или обычное сообщение
        if update.callback_query:
            # Кнопка была нажата - используем edit_message_text
            await update.callback_query.edit_message_text(intro_text, parse_mode=ParseMode.MARKDOWN)
        else:
            # Обычное сообщение - используем reply_text
            await update.message.reply_text(intro_text, parse_mode=ParseMode.MARKDOWN)
        
        await self._ask_consultation_question(update, context)
    
    async def _ask_consultation_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Задать вопрос консультации"""
        current_q = context.user_data.get('current_question', 0)
        questions = context.user_data.get('consultation_questions', [])
        
        if current_q >= len(questions):
            # Все вопросы заданы - делаем анализ
            await self._analyze_consultation_answers(update, context)
            return
        
        question_text = f"**Вопрос {current_q + 1}/7:**\n{questions[current_q]}"
        progress = "🟩" * (current_q + 1) + "⬜" * (len(questions) - current_q - 1)
        
        # Создаем кнопки для навигации
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = []
        
        # Кнопка "Назад" только если не первый вопрос
        if current_q > 0:
            keyboard.append([InlineKeyboardButton("⬅️ Назад к предыдущему вопросу", callback_data=f'consultation_back_{current_q - 1}')])
        
        # Кнопка отмены
        keyboard.append([InlineKeyboardButton("❌ Отменить консультацию", callback_data='cancel_consultation')])
        
        # Проверяем, это callback query или обычное сообщение
        if update.callback_query:
            # Кнопка была нажата - отправляем новое сообщение
            await update.callback_query.message.reply_text(
                f"{question_text}\n\n{progress}",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            # Обычное сообщение - используем reply_text
            await update.message.reply_text(
                f"{question_text}\n\n{progress}",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def _analyze_consultation_answers(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Анализ ответов консультации"""
        user = update.effective_user
        answers = context.user_data.get('consultation_answers', [])
        
        # Формируем краткий анализ
        analysis_prompt = f"""Ты психолог по книге "Восхождение". 

ОТВЕТЫ ПОЛЬЗОВАТЕЛЯ:
{chr(10).join([f"Вопрос {i+1}: {answers[i]}" for i in range(len(answers))])}

ЗАДАЧА: Дай краткий анализ (100-150 слов) с 2-3 практическими рекомендациями.

ФОРМАТ:
💙 Понимание ситуации
💡 2-3 конкретных совета из книги "Восхождение"
🎯 Следующий шаг

СТИЛЬ: Поддерживающий, практичный, краткий."""
        
        try:
            # Показываем, что бот думает
            thinking_msg = await update.message.reply_text("🤔 Анализирую ваши ответы...")
            
            # Получаем краткий анализ
            analysis = await self.ai_client.get_direct_response(analysis_prompt, user.id)
            
            # Удаляем индикатор
            await thinking_msg.delete()
            
            # Отправляем результат
            if update.callback_query:
                # Кнопка была нажата - отправляем новое сообщение
                await update.callback_query.message.reply_text(
                    f"📋 **РЕЗУЛЬТАТ КОНСУЛЬТАЦИИ**\n\n{analysis}",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                # Обычное сообщение - используем reply_text
                await update.message.reply_text(
                    f"📋 **РЕЗУЛЬТАТ КОНСУЛЬТАЦИИ**\n\n{analysis}",
                    parse_mode=ParseMode.MARKDOWN
                )
            
            # Кнопки завершения
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            
            keyboard = [
                [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')],
                [InlineKeyboardButton("📊 Тест самооценки", callback_data='test_samoocenka')]
            ]
            
            if update.callback_query:
                # Кнопка была нажата - отправляем новое сообщение
                await update.callback_query.message.reply_text(
                    "✅ **Консультация завершена!**\n\nЧто делать дальше?",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                # Обычное сообщение - используем reply_text
                await update.message.reply_text(
                    "✅ **Консультация завершена!**\n\nЧто делать дальше?",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=ParseMode.MARKDOWN
                )
            
        except Exception as e:
            logger.error(f"Ошибка анализа консультации: {e}")
            if update.callback_query:
                await update.callback_query.message.reply_text(
                    "Извините, произошла ошибка при анализе. Попробуйте позже."
                )
            else:
                await update.message.reply_text(
                    "Извините, произошла ошибка при анализе. Попробуйте позже."
                )
        
        # Очищаем данные
        context.user_data.clear()
    
    async def _handle_consultation_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ответа в структурированной консультации"""
        user = update.effective_user
        text = update.message.text.strip()
        
        if not text:
            await update.message.reply_text("Пожалуйста, напишите ответ на вопрос.")
            return 'STRUCTURED_CONSULTATION'
        
        # Проверяем длину ответа (не более 200 символов)
        if len(text) > 200:
            await update.message.reply_text(
                "Ответ слишком длинный. Пожалуйста, опишите кратко в 1-2 предложения."
            )
            return 'STRUCTURED_CONSULTATION'
        
        # Сохраняем ответ
        answers = context.user_data.get('consultation_answers', [])
        answers.append(text)
        context.user_data['consultation_answers'] = answers
        
        # Переходим к следующему вопросу
        current_q = context.user_data.get('current_question', 0)
        context.user_data['current_question'] = current_q + 1
        
        await self._ask_consultation_question(update, context)
        return 'STRUCTURED_CONSULTATION'
    
    def _is_direct_question(self, text: str) -> bool:
        """Определение прямых вопросов, требующих немедленного ответа"""
        text_lower = text.lower()
        
        # Ключевые слова для прямых вопросов
        direct_question_indicators = [
            'что из себя представляет',
            'что входит в',
            'какие курсы',
            'расскажи о',
            'объясни',
            'что такое',
            'как работает',
            'в чем разница',
            'как выбрать',
            'где найти',
            'сколько стоит',
            'как начать',
            'с чего начать',
            'что нужно знать',
            'какие навыки',
            'какие требования'
        ]
        
        # Проверяем наличие прямых вопросов
        for indicator in direct_question_indicators:
            if indicator in text_lower:
                return True
        
        # Проверяем вопросительные знаки в конце
        if text.strip().endswith('?'):
            return True
        
        return False
    
    def _analyze_speech_patterns(self, text: str) -> Dict[str, bool]:
        """Анализ паттернов речи"""
        text_lower = text.lower()
        
        patterns = {
            'psychology_need': False,
            'career_need': False,
            'emotional_support': False,
            'cancellation': False,
            'topic_change': False,
            'self_introduction_request': False,
            'dream_expression': False,
            'provocative': False
        }
        
        # Психологическая помощь
        psychology_keywords = [
            'сон', 'сны', 'депрессия', 'тревога', 'стресс', 'паника', 'страх', 
            'грусть', 'одиночество', 'отношения', 'семья', 'родители', 'дети', 
            'любовь', 'развод', 'смерть', 'потеря', 'плохо', 'больно', 'страшно'
        ]
        patterns['psychology_need'] = any(keyword in text_lower for keyword in psychology_keywords)
        
        # Карьерные вопросы
        career_keywords = [
            'работа', 'карьера', 'профессия', 'зарплата', 'деньги', 'учеба', 
            'образование', 'навыки', 'опыт', 'компания', 'начальник', 'коллеги',
            'высокооплачиваемая работа', 'карьерный рост', 'профессиональное развитие'
        ]
        patterns['career_need'] = any(keyword in text_lower for keyword in career_keywords)
        
        # Эмоциональная поддержка
        emotional_keywords = [
            'одинок', 'грустно', 'плохо', 'устал', 'устала', 'сложно', 'трудно', 
            'помоги', 'поддержка', 'понимаю', 'понимаешь'
        ]
        patterns['emotional_support'] = any(keyword in text_lower for keyword in emotional_keywords)
        
        # Отмена/прекращение
        cancellation_keywords = [
            'не хочу', 'хватит', 'достаточно', 'стоп', 'прекрати', 'остановись', 
            'не буду', 'не буду говорить', 'не хочу говорить', 'хватит говорить'
        ]
        patterns['cancellation'] = any(keyword in text_lower for keyword in cancellation_keywords)
        
        # Смена темы
        topic_change_keywords = [
            'другое', 'другая тема', 'давай о', 'поговорим о', 'хочу поговорить о', 
            'смени тему', 'не об этом'
        ]
        patterns['topic_change'] = any(keyword in text_lower for keyword in topic_change_keywords)
        
        # Запрос рассказать о себе
        self_intro_keywords = [
            'расскажи о себе', 'расскажи о тебе', 'кто ты', 'что ты', 
            'как ты работаешь', 'твоя история', 'твоя работа', 'что ты умеешь'
        ]
        patterns['self_introduction_request'] = any(keyword in text_lower for keyword in self_intro_keywords)
        
        # Мечты и цели
        dream_keywords = [
            'хочу стать', 'мечтаю', 'мечта', 'цель', 'планирую', 'буду', 'стану'
        ]
        patterns['dream_expression'] = any(keyword in text_lower for keyword in dream_keywords)
        
        # Провокационные вопросы
        provocative_keywords = [
            'глупый', 'тупой', 'бесполезный', 'не понимаешь', 'не слушаешь', 
            'плохой', 'ужасный', 'ненавижу', 'ненавидишь', 'не понял', 'не поняла'
        ]
        patterns['provocative'] = any(keyword in text_lower for keyword in provocative_keywords)
        
        return patterns
    
    def _determine_response_type(self, patterns: Dict[str, bool], text: str) -> PromptType:
        """Определение типа ответа"""
        
        if patterns['psychology_need'] or patterns['emotional_support']:
            return PromptType.PSYCHOLOGY_CONSULTATION
        elif patterns['career_need']:
            return PromptType.CAREER_CONSULTATION
        elif 'тест самооценки' in text.lower() or 'восхождение' in text.lower():
            return PromptType.SELF_ESTEEM_ANALYSIS
        elif 'полный анализ' in text.lower() or 'детальный анализ' in text.lower():
            return PromptType.FULL_ANALYSIS
        else:
            return PromptType.EXPRESS_ANALYSIS
    
    async def _get_ai_response(self, user_id: int, message: str, response_type: PromptType) -> str:
        """Получение ответа от ИИ"""
        
        # Формируем контекст
        conversation_context = self.conversation_history.get(user_id, [])
        context = {
            'conversation': '\n'.join(conversation_context[-5:]),  # Последние 5 сообщений для экономии
            'user_message': message,
            'message_count': len(conversation_context)
        }
        
        # Получаем ответ от ИИ (используем GPT-3.5 для бесплатной консультации через прямое обращение)
        ai_response = await self.ai_client.get_direct_response(
            prompt=f"""Ты — психолог, работающий по принципам книги "Восхождение".

ТВОЙ ПОДХОД:

🌟 **ДУХОВНЫЕ ПРИНЦИПЫ:**
- "Для меня создан мир" — каждый человек уникально ценен
- Внутренние силы — корень всех внешних действий
- Самоуважение через осознание своей истинной ценности
- У каждого есть предназначение и силы для его выполнения
- Вера в себя связана с верой в высшее

🔄 **МЕТОДЫ:**
1. Диалог с душой — разговор с внутренним голосом
2. Повторение — укоренение позитивных убеждений
3. Самоанализ — наблюдение за реакциями
4. Работа с эмоциями — выражение и трансформация чувств

ЗАДАЧА: Помоги человеку понять себя, повысить самооценку, найти предназначение.

КОНТЕКСТ: {context.get('conversation', '')}
ВОПРОС: {message}

ОТВЕТ (400-500 слов):
💙 Эмпатия и понимание
🧠 Анализ ситуации
💡 Рекомендации из книги
🎯 Следующие шаги

СТИЛЬ: Эмпатичный, поддерживающий, мудрый.""",
            user_id=user_id
        )
        
        return ai_response
    
    async def _send_response(self, update: Update, response: str):
        """Отправка ответа пользователю с обработкой ошибок"""
        
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
                await update.message.reply_text("😔 Извините, произошла ошибка при отправке ответа. Попробуйте еще раз.")
    
    async def _suggest_next_steps(self, update: Update, patterns: Dict[str, bool], message_count: int):
        """Предложение следующих шагов"""
        
        if message_count >= 10 and not patterns['cancellation']:
            # Предлагаем экспресс-анализ
            await update.message.reply_text(
                "💎 **Хотите детальный анализ?**\n\n"
                "Полный психоанализ включает:\n"
                "• 7 профессиональных вопросов\n"
                "• Детальный профиль личности\n"
                "• HR-оценки и рекомендации\n"
                "• Образовательную траекторию\n\n"
                "Стоимость: 500₽\n"
                "Для заказа напишите: 'хочу полный анализ'"
            )
    
    async def _handle_cancellation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Обработка отмены"""
        await update.message.reply_text(
            "Понял. Если захотите поговорить снова - просто напишите. "
            "Я всегда готов выслушать и поддержать. 💙"
        )
        
        # Очищаем данные пользователя
        user = update.effective_user
        self.ai_client.clear_user_data(user.id)
        self.conversation_history.pop(user.id, None)
        self.free_consultation_tracker.pop(user.id, None)
        
        return 'END'
    
    async def _handle_topic_change(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Обработка смены темы"""
        await update.message.reply_text(
            "Конечно! О чем бы вы хотели поговорить? "
            "Я готов обсудить любую тему, которая вас интересует. 😊"
        )
        return 'WAITING_MESSAGE'
    
    async def _handle_self_introduction(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Обработка запроса рассказать о себе"""
        await update.message.reply_text(
            "Конечно! Я помощник по книге \"Восхождение\". "
            "Помогаю людям понять себя, повысить самооценку, найти предназначение. "
            "Использую принципы из книги \"Восхождение\" и методы психоанализа. "
            "Расскажите, что вас беспокоит! 📖"
        )
        return 'WAITING_MESSAGE'
    