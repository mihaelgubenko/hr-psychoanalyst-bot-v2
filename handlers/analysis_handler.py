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
        """Анализ самооценки через ИИ"""
        
        # Формируем промпт для анализа
        answers_text = "\n".join([f"{i+1}. {answer}" for i, answer in enumerate(answers)])
        
        prompt = f"""
Ты — психолог-эксперт по самооценке, обученный по книге "Восхождение". 

ОТВЕТЫ НА ТЕСТ (10 ключевых вопросов):
{answers_text}

ПРОВЕДИ АНАЛИЗ НА ОСНОВЕ КНИГИ "ВОСХОЖДЕНИЕ":

📊 **ОБЩИЙ УРОВЕНЬ САМООЦЕНКИ (1-10)**
[Оценка и краткое обоснование]

💎 **СИЛЬНЫЕ СТОРОНЫ**
[Что уже хорошо развито, на что опираться]

⚠️ **ОБЛАСТИ ДЛЯ РОСТА**
[Что требует внимания и развития]

🎯 **ПЕРСОНАЛЬНЫЕ РЕКОМЕНДАЦИИ**
[3-4 конкретных шага на основе принципов книги]

✨ **УПРАЖНЕНИЯ ИЗ КНИГИ "ВОСХОЖДЕНИЕ"**
[2-3 практических упражнения]

ПРИНЦИПЫ КНИГИ:
- "Для меня создан мир" - каждый важен
- Внутренние силы - корень внешних действий
- Самоуважение через осознание своей ценности
- Вера в себя через веру в Творца

СТИЛЬ: Эмпатичный, вдохновляющий, практичный. 400-600 слов.
"""
        
        # Получаем ответ от ИИ
        ai_response = await self.ai_client.get_response(
            prompt=prompt,
            user_id=user_id,
            prompt_type=PromptType.SELF_ESTEEM_ANALYSIS
        )
        
        return ai_response.content
    
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