"""
Обработчик анализов личности и тестов
"""

import logging
from typing import Dict, Any, Optional
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from ai.adaptive_prompt_manager import PromptType

logger = logging.getLogger(__name__)

class AnalysisHandler:
    """Обработчик анализов личности"""
    
    def __init__(self, ai_client, database):
        self.ai_client = ai_client
        self.database = database
        self.user_data = {}  # user_id -> analysis data
        self.button_test_data = {}  # user_id -> {answers, current_q} для теста с кнопками
    
    async def start_self_esteem_test(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Начало теста самооценки"""
        user = update.effective_user
        
        # Инициализация данных пользователя в context (важно для ConversationHandler!)
        context.user_data['test_type'] = 'self_esteem'
        context.user_data['answers'] = []
        context.user_data['current_question'] = 0
        
        intro_text = """
📖 **ТЕСТ САМООЦЕНКИ | "Восхождение"**

Этот тест основан на книге "Восхождение" и поможет вам:

✨ Понять уровень вашей самооценки
🎯 Найти свое предназначение
😌 Освободиться от страхов, гнева и обид
💝 Улучшить отношения с собой и другими

**Принципы из книги "Восхождение":**
• Каждый человек создан для определенной миссии
• "Для меня создан мир" - вы важны как целый мир
• Самоуважение основано на понимании своей ценности
• У каждого есть силы для выполнения своего предназначения

**Формат:** 10 ключевых вопросов
**Время:** ~5-7 минут  
**Результат:** Детальный анализ + персональные рекомендации

💡 *Отвечайте искренне - это ключ к трансформации!*

━━━━━━━━━━━━━━━━━━━━━━

**Вопрос 1 из 10:**
Как вы оцениваете свою ценность как личности? (1-10)
"""
        
        await update.message.reply_text(intro_text, parse_mode=ParseMode.MARKDOWN)
        return 'SELF_ESTEEM_Q'
    
    async def handle_self_esteem_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Обработка ответов на вопросы теста самооценки"""
        user = update.effective_user
        text = update.message.text.strip()
        
        if not text or len(text) < 1:
            await update.message.reply_text(
                "Пожалуйста, дайте ответ."
            )
            return 'SELF_ESTEEM_Q'
        
        # Получаем данные из context (важно для ConversationHandler!)
        answers = context.user_data.get('answers', [])
        current_q = context.user_data.get('current_question', 0)
        
        # Сохраняем ответ
        answers.append(text)
        current_q += 1
        
        # Обновляем context
        context.user_data['answers'] = answers
        context.user_data['current_question'] = current_q
        
        # Проверяем, закончились ли вопросы (10 вопросов для упрощенного теста)
        if current_q >= 10:
            # Все вопросы завершены - проводим анализ
            await update.message.reply_text(
                "✅ Отлично! Все ответы получены.\n\n"
                "🔮 Провожу глубокий анализ вашей самооценки...\n"
                "⏱️ Это займет 30-60 секунд."
            )
            
            try:
                # Анализ через ИИ
                analysis_result = await self._analyze_self_esteem(user.id, answers)
            except Exception as e:
                logger.error(f"Ошибка анализа самооценки: {e}", exc_info=True)
                await update.message.reply_text(
                    "😔 Извините, произошла ошибка при анализе.\n\n"
                    "Попробуйте позже или напишите /start для начала заново."
                )
                context.user_data.clear()
                return ConversationHandler.END
            
            analysis_result = analysis_result if analysis_result else "Анализ временно недоступен."
            
            # Отправляем результат
            await self._send_analysis_result(update, analysis_result)
            
            # Сохраняем результаты
            await self.database.save_analysis(
                user.id, 
                user.first_name or f"User_{user.id}", 
                'self_esteem', 
                {
                    'type': 'self_esteem',
                    'answers': answers,
                    'analysis': analysis_result
                }
            )
            
            # Очищаем данные
            context.user_data.clear()
            return ConversationHandler.END
        
        # Следующий вопрос
        next_question = self._get_next_question(current_q)
        await update.message.reply_text(next_question, parse_mode=ParseMode.MARKDOWN)
        
        return 'SELF_ESTEEM_Q'
    
    async def start_full_analysis(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Начало полного анализа"""
        user = update.effective_user
        
        # Проверяем, есть ли уже полный анализ
        analyses = await self.database.get_user_analyses(user.id)
        has_full_analysis = any(analysis.analysis_type == 'full' for analysis in analyses)
        
        if has_full_analysis:
            await update.message.reply_text(
                "У вас уже есть полный анализ! Для нового анализа используйте /start"
            )
            return 'WAITING_MESSAGE'
        
        # Инициализация данных в context
        context.user_data['test_type'] = 'full_analysis'
        context.user_data['answers'] = []
        context.user_data['current_question'] = 0
        
        professional_questions = [
            "Расскажите о вашем детстве. Какие воспоминания формировали ваш характер?",
            "Что вас больше всего мотивирует в жизни? Откуда черпаете энергию?",
            "Как вы справляетесь со стрессом? Опишите последнюю сложную ситуацию.",
            "В какой среде вы работаете лучше всего? Команда или индивидуально?",
            "Какие ваши главные страхи и как они влияют на решения?",
            "Как вы видите себя через 5 лет? Какие цели важны?",
            "Что бы вы изменили в себе, если бы могли? Почему именно это?"
        ]
        
        await update.message.reply_text(
            "💎 **Полный психоанализ**\n\n"
            "Отлично! Сейчас я проведу детальный анализ вашей личности.\n"
            "Будет 7 профессиональных вопросов.\n\n"
            "**Вопрос 1 из 7:**\n"
            f"{professional_questions[0]}"
        )
        
        return 'Q1'
    
    async def handle_full_analysis_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Обработка ответов на вопросы полного анализа"""
        user = update.effective_user
        text = update.message.text.strip()
        
        if not text or len(text) < 20:
            await update.message.reply_text(
                "Пожалуйста, дайте развернутый ответ (минимум 20 символов). "
                "Это важно для качественного анализа."
            )
            return context.user_data.get('current_question', 'Q1')
        
        # Получаем данные из context
        answers = context.user_data.get('answers', [])
        current_q = context.user_data.get('current_question', 0)
        
        answers.append(text)
        current_q += 1
        
        # Обновляем context
        context.user_data['answers'] = answers
        context.user_data['current_question'] = current_q
        
        professional_questions = [
            "Расскажите о вашем детстве. Какие воспоминания формировали ваш характер?",
            "Что вас больше всего мотивирует в жизни? Откуда черпаете энергию?",
            "Как вы справляетесь со стрессом? Опишите последнюю сложную ситуацию.",
            "В какой среде вы работаете лучше всего? Команда или индивидуально?",
            "Какие ваши главные страхи и как они влияют на решения?",
            "Как вы видите себя через 5 лет? Какие цели важны?",
            "Что бы вы изменили в себе, если бы могли? Почему именно это?"
        ]
        
        if current_q < 7:
            await update.message.reply_text(
                f"**Вопрос {current_q + 1} из 7:**\n"
                f"{professional_questions[current_q]}"
            )
            return f'Q{current_q + 1}'
        else:
            # Все вопросы ответены, проводим анализ
            await update.message.reply_text(
                "🎯 Отлично! Все ответы получены. "
                "Провожу детальный психоанализ... Это займет несколько минут."
            )
            
            # Анализ через ИИ
            analysis_result = await self._analyze_full_personality(user.id, answers)
            
            # Отправляем результат
            await self._send_analysis_result(update, analysis_result)
            
            # Сохраняем результаты
            await self.database.save_analysis(
                user.id, 
                user.first_name or f"User_{user.id}", 
                'full', 
                {
                    'type': 'full',
                    'answers': answers,
                    'analysis': analysis_result
                },
                'paid'
            )
            
            await update.message.reply_text(
                "✅ **Анализ завершен!**\n\n"
                "Спасибо за доверие. Ваши данные сохранены анонимно.\n"
                "Для нового анализа используйте /start"
            )
            
            # Очищаем данные
            context.user_data.clear()
            return ConversationHandler.END
    
    async def _analyze_self_esteem(self, user_id: int, answers: list) -> str:
        """Анализ самооценки через ИИ с промптом из книги 'Восхождение'"""
        
        # Формируем список ответов
        answers_text = "\n".join([f"Вопрос {i+1}: {answer}" for i, answer in enumerate(answers)])
        
        # Создаем специальный промпт для анализа теста на основе книги "Восхождение"
        prompt = f"""Ты — психолог-эксперт по самооценке, обученный по книге "Восхождение". 

ОТВЕТЫ НА ТЕСТ САМООЦЕНКИ (10 вопросов):
{answers_text}

ВОПРОСЫ БЫЛИ:
1. Как вы оцениваете свою ценность как личности? (1-10)
2. Насколько вы довольны собой и своими достижениями?
3. Верите ли вы в свои способности справляться с трудностями?
4. Какие страхи чаще всего мешают вам действовать?
5. Как часто вы испытываете гнев или раздражение?
6. Есть ли у вас обиды на людей из прошлого?
7. Знаете ли вы свое предназначение в жизни?
8. Что придает смысл вашей жизни?
9. Как вы проявляете любовь к себе?
10. Чувствуете ли вы себя свободным быть собой?

ПРОВЕДИ АНАЛИЗ НА ОСНОВЕ КНИГИ "ВОСХОЖДЕНИЕ":

📊 **ОБЩИЙ УРОВЕНЬ САМООЦЕНКИ** (1-10)
[Дай оценку и краткое обоснование]

💎 **СИЛЬНЫЕ СТОРОНЫ**
[Что уже хорошо развито, на что можно опираться]

⚠️ **ОБЛАСТИ ДЛЯ РОСТА**
[Что требует внимания и развития]

🎯 **ПЕРСОНАЛЬНЫЕ РЕКОМЕНДАЦИИ**
[3-4 конкретных шага на основе принципов книги "Восхождение"]

✨ **УПРАЖНЕНИЯ ИЗ КНИГИ**
[2-3 практических упражнения для повышения самооценки]

ПРИНЦИПЫ КНИГИ "ВОСХОЖДЕНИЕ":
• "Для меня создан мир" - каждый человек важен как целый мир
• Внутренние силы - истинный корень всех внешних действий
• Самоуважение основано на осознании своей ценности перед Творцом
• Вера в себя связана с верой в Б-га
• У каждого есть силы для выполнения своего предназначения

СТИЛЬ: Эмпатичный, вдохновляющий, практичный. 500-700 слов."""

        # Получаем ответ напрямую от OpenAI (без adaptive промптов)
        analysis = await self.ai_client.get_direct_response(prompt, user_id)
        
        return analysis
    
    async def _analyze_full_personality(self, user_id: int, answers: list) -> str:
        """Анализ полной личности через ИИ"""
        
        # Формируем промпт для анализа
        answers_text = "\n".join([f"{i+1}. {answer}" for i, answer in enumerate(answers)])
        
        prompt = f"""
Ты — ведущий психоаналитик и HR-эксперт с 20-летним опытом.

ДЕТАЛЬНЫЕ ОТВЕТЫ КЛИЕНТА:
{answers_text}

ПРОВЕДИ ГЛУБОКИЙ ПСИХОАНАЛИЗ:

🧠 **ПСИХОАНАЛИТИЧЕСКИЙ ПРОФИЛЬ:**
- Структура личности (Ид/Эго/Суперэго)
- Защитные механизмы
- Бессознательные конфликты
- Травмы и их влияние

🎭 **АРХЕТИПЫ И ТИПОЛОГИЯ:**
- Доминирующий архетип по Юнгу
- MBTI тип с обоснованием
- Темперамент и особенности

📊 **BIG FIVE (OCEAN):**
- Открытость: [1-10] + обоснование
- Добросовестность: [1-10] + обоснование  
- Экстраверсия: [1-10] + обоснование
- Доброжелательность: [1-10] + обоснование
- Нейротизм: [1-10] + обоснование

💼 **HR-РЕКОМЕНДАЦИИ:**
- Подходящие роли и позиции
- Стиль управления/работы
- Мотивационные факторы
- Потенциальные риски

🎓 **ОБРАЗОВАТЕЛЬНЫЕ РЕКОМЕНДАЦИИ:**
- Конкретные направления обучения
- Форматы обучения (очное/заочное)
- Дополнительные навыки
- Карьерная траектория

🔮 **ПРОГНОЗ РАЗВИТИЯ:**
- Как будет развиваться личность
- Ключевые точки роста
- Рекомендации по саморазвитию

СТИЛЬ: Профессиональный, детальный, практичный. 1200-1500 слов.
"""
        
        # Получаем ответ от ИИ
        ai_response = await self.ai_client.get_response(
            prompt=prompt,
            user_id=user_id,
            prompt_type=PromptType.FULL_ANALYSIS
        )
        
        return ai_response.content
    
    async def _send_analysis_result(self, update: Update, result: str):
        """Отправка результата анализа"""
        
        # Разбиваем длинный результат на части
        max_length = 4000
        if len(result) <= max_length:
            await update.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)
        else:
            parts = [result[i:i+max_length] for i in range(0, len(result), max_length)]
            for i, part in enumerate(parts):
                prefix = f"**Анализ (часть {i+1}/{len(parts)}):**\n\n" if i > 0 else ""
                await update.message.reply_text(prefix + part, parse_mode=ParseMode.MARKDOWN)
    
    def _get_next_question(self, question_num: int) -> str:
        """Получение следующего вопроса теста самооценки (10 вопросов)"""
        
        # Упрощенный тест - 10 ключевых вопросов из книги "Восхождение"
        questions = [
            "Как вы оцениваете свою ценность как личности? (1-10)",
            "Насколько вы довольны собой и своими достижениями?",
            "Верите ли вы в свои способности справляться с трудностями?",
            "Какие страхи чаще всего мешают вам действовать?",
            "Как часто вы испытываете гнев или раздражение?",
            "Есть ли у вас обиды на людей из прошлого?",
            "Знаете ли вы свое предназначение в жизни?",
            "Что придает смысл вашей жизни?",
            "Как вы проявляете любовь к себе?",
            "Чувствуете ли вы себя свободным быть собой?"
        ]
        
        if question_num < len(questions):
            progress = f"━" * question_num + "○" + "━" * (10 - question_num - 1)
            return f"**Вопрос {question_num + 1} из 10:**\n{questions[question_num]}\n\n{progress}"
        
        return "Все вопросы завершены!"
    
    # ==================== ТЕСТ С КНОПКАМИ ====================
    
    async def start_button_test(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Тест самооценки с кнопками"""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        # Инициализируем данные
        self.button_test_data[update.effective_user.id] = {
            'answers': [],
            'current_question': 0
        }
        
        intro_text = """
📊 **ТЕСТ САМООЦЕНКИ**

Отвечайте на вопросы, нажимая кнопки.

⏱️ **Время:** ~3 минуты
📊 **Результат:** Детальный психоанализ с рекомендациями

**Подход:**
🧠 Психоанализ (Фрейд, Юнг)
🌟 Духовные принципы самопознания
💡 Практические упражнения

Начинаем! ⬇️
"""
        await update.message.reply_text(intro_text, parse_mode=ParseMode.MARKDOWN)
        
        # Показываем первый вопрос
        await self._show_button_question(update, 0)
    
    async def _show_button_question(self, update: Update, question_num: int) -> None:
        """Показать вопрос с кнопками"""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        questions_with_buttons = [
            {
                'text': "**Вопрос 1/10:**\nКак вы оцениваете свою ценность как личности?",
                'buttons': [[InlineKeyboardButton(str(i), callback_data=f'btn_test_q0_a{i}') for i in range(1, 6)],
                           [InlineKeyboardButton(str(i), callback_data=f'btn_test_q0_a{i}') for i in range(6, 11)]]
            },
            {
                'text': "**Вопрос 2/10:**\nНасколько вы довольны собой?",
                'buttons': [
                    [InlineKeyboardButton("Очень доволен", callback_data='btn_test_q1_a1')],
                    [InlineKeyboardButton("Скорее доволен", callback_data='btn_test_q1_a2')],
                    [InlineKeyboardButton("Не очень", callback_data='btn_test_q1_a3')],
                    [InlineKeyboardButton("Недоволен", callback_data='btn_test_q1_a4')]
                ]
            },
            {
                'text': "**Вопрос 3/10:**\nВерите ли в свои способности?",
                'buttons': [
                    [InlineKeyboardButton("Полностью верю", callback_data='btn_test_q2_a1')],
                    [InlineKeyboardButton("Скорее да", callback_data='btn_test_q2_a2')],
                    [InlineKeyboardButton("Сомневаюсь", callback_data='btn_test_q2_a3')],
                    [InlineKeyboardButton("Не верю", callback_data='btn_test_q2_a4')]
                ]
            },
            # Остальные вопросы упростим для демо
            {
                'text': f"**Вопрос 4/10:**\nКакие страхи мешают вам?",
                'buttons': [
                    [InlineKeyboardButton("Страх неудачи", callback_data='btn_test_q3_a1')],
                    [InlineKeyboardButton("Страх осуждения", callback_data='btn_test_q3_a2')],
                    [InlineKeyboardButton("Нет сильных страхов", callback_data='btn_test_q3_a3')]
                ]
            },
            {
                'text': "**Вопрос 5/10:**\nКак часто гнев?",
                'buttons': [[InlineKeyboardButton(str(i), callback_data=f'btn_test_q4_a{i}') for i in range(1, 6)],
                           [InlineKeyboardButton(str(i), callback_data=f'btn_test_q4_a{i}') for i in range(6, 11)]]
            },
            {
                'text': "**Вопрос 6/10:**\nЕсть ли обиды?",
                'buttons': [
                    [InlineKeyboardButton("Да, много", callback_data='btn_test_q5_a1')],
                    [InlineKeyboardButton("Есть немного", callback_data='btn_test_q5_a2')],
                    [InlineKeyboardButton("Почти нет", callback_data='btn_test_q5_a3')],
                    [InlineKeyboardButton("Нет обид", callback_data='btn_test_q5_a4')]
                ]
            },
            {
                'text': "**Вопрос 7/10:**\nЗнаете предназначение?",
                'buttons': [
                    [InlineKeyboardButton("Да, знаю", callback_data='btn_test_q6_a1')],
                    [InlineKeyboardButton("Есть идеи", callback_data='btn_test_q6_a2')],
                    [InlineKeyboardButton("Ищу", callback_data='btn_test_q6_a3')],
                    [InlineKeyboardButton("Не знаю", callback_data='btn_test_q6_a4')]
                ]
            },
            {
                'text': "**Вопрос 8/10:**\nЧто придает смысл?",
                'buttons': [
                    [InlineKeyboardButton("Семья", callback_data='btn_test_q7_a1')],
                    [InlineKeyboardButton("Работа", callback_data='btn_test_q7_a2')],
                    [InlineKeyboardButton("Духовность", callback_data='btn_test_q7_a3')],
                    [InlineKeyboardButton("Пока не знаю", callback_data='btn_test_q7_a4')]
                ]
            },
            {
                'text': "**Вопрос 9/10:**\nЛюбовь к себе?",
                'buttons': [[InlineKeyboardButton(str(i), callback_data=f'btn_test_q8_a{i}') for i in range(1, 6)],
                           [InlineKeyboardButton(str(i), callback_data=f'btn_test_q8_a{i}') for i in range(6, 11)]]
            },
            {
                'text': "**Вопрос 10/10:**\nСвободны быть собой?",
                'buttons': [
                    [InlineKeyboardButton("Да, полностью", callback_data='btn_test_q9_a1')],
                    [InlineKeyboardButton("В основном да", callback_data='btn_test_q9_a2')],
                    [InlineKeyboardButton("Не всегда", callback_data='btn_test_q9_a3')],
                    [InlineKeyboardButton("Нет", callback_data='btn_test_q9_a4')]
                ]
            }
        ]
        
        if question_num < len(questions_with_buttons):
            q = questions_with_buttons[question_num]
            
            # Добавляем прогресс бар
            progress_filled = int((question_num / 10) * 10)
            progress_bar = "━" * progress_filled + "○" + "━" * (10 - progress_filled - 1)
            progress_text = f"\n\n{progress_bar}  {question_num}/10 ({progress_filled * 10}%)"
            
            # Добавляем кнопки навигации
            nav_buttons = []
            if question_num > 0:  # Кнопка "Назад" только если не первый вопрос
                nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f'back_to_q{question_num-1}'))
            nav_buttons.append(InlineKeyboardButton("❌ Отменить", callback_data='cancel_test'))
            
            buttons_with_nav = q['buttons'] + [nav_buttons]
            reply_markup = InlineKeyboardMarkup(buttons_with_nav)
            
            full_text = q['text'] + progress_text
            
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    full_text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text(
                    full_text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
    
    async def handle_button_test_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка ответов из кнопок"""
        query = update.callback_query
        await query.answer()
        
        user = update.effective_user
        data = query.data
        
        # Проверка на отмену
        if data == 'cancel_test':
            await query.edit_message_text(
                "❌ **ТЕСТ ОТМЕНЕН**\n\n"
                "Ваши ответы не сохранены.\n\n"
                "Что делать дальше?\n"
                "/start - Главное меню\n"
                "/test - Начать тест заново\n"
                "/consultation - Консультация"
            )
            self.button_test_data.pop(user.id, None)
            return
        
        # Проверка на возврат назад
        if data.startswith('back_to_q'):
            prev_question = int(data.split('back_to_q')[1])
            
            # Удаляем последний ответ
            if user.id in self.button_test_data:
                answers = self.button_test_data[user.id]['answers']
                if len(answers) > prev_question:
                    self.button_test_data[user.id]['answers'] = answers[:prev_question]
                    self.button_test_data[user.id]['current_question'] = prev_question
            
            # Показываем предыдущий вопрос
            await self._show_button_question(update, prev_question)
            return
        
        # Парсим callback_data: btn_test_q{N}_a{answer}
        if not data.startswith('btn_test_'):
            return
        
        parts = data.split('_')
        question_num = int(parts[2][1:])  # q0 -> 0
        answer = parts[3]  # a1, a2, etc
        
        # Сохраняем ответ
        if user.id not in self.button_test_data:
            self.button_test_data[user.id] = {'answers': [], 'current_question': 0}
        
        self.button_test_data[user.id]['answers'].append(answer)
        self.button_test_data[user.id]['current_question'] = question_num + 1
        
        # Проверяем, все ли вопросы отвечены
        if question_num >= 9:  # 10-й вопрос (индекс 9)
            await query.edit_message_text(
                "✅ Отлично! Все ответы получены.\n\n"
                "🔮 Провожу глубокий психоанализ...\n"
                "⏱️ 30-60 секунд"
            )
            
            # Показываем typing action
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            # Анализируем
            answers = self.button_test_data[user.id]['answers']
            
            try:
                analysis = await self._analyze_self_esteem_simple(user.id, answers)
                await update.effective_chat.send_message(analysis, parse_mode=ParseMode.MARKDOWN)
                
                # Сохраняем в БД
                await self.database.save_analysis(
                    user.id,
                    user.first_name or f"User_{user.id}",
                    'self_esteem_buttons',
                    {'answers': answers, 'analysis': analysis}
                )
                
                # FOLLOW-UP: Предлагаем дополнительные вопросы
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                
                followup_keyboard = [
                    [InlineKeyboardButton("💬 Задать вопрос по результату", callback_data='followup_start')],
                    [InlineKeyboardButton("🔄 Пройти тест заново", callback_data='test_restart')],
                    [InlineKeyboardButton("👤 Личная консультация", callback_data='personal')],
                    [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
                ]
                
                await update.effective_chat.send_message(
                    "✨ **ЧТО ДАЛЬШЕ?**\n\n"
                    "У вас есть **10 бесплатных вопросов** по результату теста.\n\n"
                    "Выберите действие:",
                    reply_markup=InlineKeyboardMarkup(followup_keyboard),
                    parse_mode=ParseMode.MARKDOWN
                )
                
                # Устанавливаем счетчик вопросов
                context.user_data['followup_mode'] = True
                context.user_data['free_questions'] = 10
                context.user_data['test_result'] = analysis
                
            except Exception as e:
                logger.error(f"Ошибка анализа кнопочного теста: {e}", exc_info=True)
                await update.effective_chat.send_message(
                    "😔 Ошибка при анализе. Попробуйте /start"
                )
            
            # Очищаем данные теста
            self.button_test_data.pop(user.id, None)
        else:
            # Показываем следующий вопрос
            await self._show_button_question(update, question_num + 1)
    
    async def _analyze_self_esteem_simple(self, user_id: int, answers: list) -> str:
        """Психоаналитический анализ самооценки"""
        answers_text = "\n".join([f"{i+1}. {ans}" for i, ans in enumerate(answers)])
        
        prompt = f"""Проведи психоаналитический анализ самооценки.

ОТВЕТЫ НА ТЕСТ:
{answers_text}

ИСПОЛЬЗУЙ ИНТЕГРАТИВНЫЙ ПОДХОД:

🧠 **ПСИХОАНАЛИЗ (ФРЕЙД):**
- Какие защитные механизмы использует человек?
- Есть ли вытеснение, проекция, рационализация?
- Как бессознательное влияет на самооценку?

💎 **ЮНГИАНСКИЙ АНАЛИЗ:**
- Какие архетипы проявляются?
- Работает ли человек с Тенью (отвергаемыми частями)?
- На каком этапе индивидуации?
- Интроверт или экстраверт?

🌟 **ДУХОВНЫЕ АСПЕКТЫ:**
- Осознает ли свою ценность?
- Есть ли связь с высшим предназначением?
- "Для меня создан мир" - принимает ли этот принцип?

ДАЙ АНАЛИЗ (400-500 слов):

📊 **УРОВЕНЬ САМООЦЕНКИ** (1-10 + обоснование)

🧠 **ПСИХОДИНАМИКА**
[Защитные механизмы, бессознательные паттерны]

💎 **АРХЕТИПИЧЕСКИЙ АНАЛИЗ**
[Какие архетипы активны, работа с Тенью]

✨ **СИЛЬНЫЕ СТОРОНЫ**
[На что опираться]

⚠️ **ЗОНЫ РОСТА**
[Что требует внимания]

🎯 **ПЕРСОНАЛЬНЫЕ РЕКОМЕНДАЦИИ**
[3-4 конкретных метода: работа с Тенью, диалог с бессознательным, самоанализ]

💡 **ПРАКТИЧЕСКИЕ УПРАЖНЕНИЯ**
[2-3 упражнения для повышения самооценки]

СТИЛЬ: Глубокий, профессиональный, эмпатичный, мудрый."""

        return await self.ai_client.get_direct_response(prompt, user_id)