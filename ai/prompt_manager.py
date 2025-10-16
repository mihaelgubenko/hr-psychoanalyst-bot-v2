"""
Менеджер промптов с адаптивными шаблонами и A/B тестированием
Улучшенная версия с типизацией и оптимизацией
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import random

logger = logging.getLogger(__name__)

class PromptType(Enum):
    """Типы промптов"""
    EXPRESS_ANALYSIS = "express_analysis"
    FULL_ANALYSIS = "full_analysis"
    PSYCHOLOGY_CONSULTATION = "psychology_consultation"
    CAREER_CONSULTATION = "career_consultation"
    EMOTIONAL_SUPPORT = "emotional_support"
    SELF_ESTEEM_ANALYSIS = "self_esteem_analysis"

class PromptLength(Enum):
    """Длины промптов"""
    SHORT = "short"      # ~200 токенов
    MEDIUM = "medium"    # ~400 токенов
    LONG = "long"        # ~600 токенов
    EXTENDED = "extended" # ~800 токенов

@dataclass
class PromptTemplate:
    """Шаблон промпта с метаданными"""
    id: str
    type: PromptType
    length: PromptLength
    template: str
    description: str
    estimated_tokens: int
    active: bool = True
    created_at: Optional[datetime] = None
    usage_count: int = 0
    success_rate: float = 0.0
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class PromptMetrics:
    """Метрики использования промпта"""
    template_id: str
    total_uses: int = 0
    successful_uses: int = 0
    avg_response_length: float = 0.0
    avg_user_satisfaction: float = 0.0
    conversion_rate: float = 0.0
    last_used: Optional[datetime] = None

class PromptManager:
    """Менеджер промптов с адаптивными шаблонами и A/B тестированием"""
    
    def __init__(self, config):
        self.config = config
        self.templates: Dict[str, PromptTemplate] = {}
        self.metrics: Dict[str, PromptMetrics] = {}
        self.user_preferences: Dict[int, Dict[str, Any]] = {}
        
        # Загружаем стандартные шаблоны
        self._load_default_templates()
    
    def _load_default_templates(self):
        """Загрузка стандартных шаблонов промптов"""
        
        # Экспресс-анализ - короткий
        self.templates["express_analysis_short"] = PromptTemplate(
            id="express_analysis_short",
            type=PromptType.EXPRESS_ANALYSIS,
            length=PromptLength.SHORT,
            template="""Ты — HR-психоаналитик. Проведи краткий анализ личности.

ДИАЛОГ: {conversation}

ФОРМАТ:
🧠 Психотип: [кратко]
💼 Подходящие сферы: [2-3 области]
🎯 Рекомендации: [конкретно]

СТИЛЬ: Профессиональный, до 150 слов.""",
            description="Краткий экспресс-анализ",
            estimated_tokens=200
        )
        
        # Экспресс-анализ - средний
        self.templates["express_analysis_medium"] = PromptTemplate(
            id="express_analysis_medium",
            type=PromptType.EXPRESS_ANALYSIS,
            length=PromptLength.MEDIUM,
            template="""Ты — профессиональный HR-психоаналитик и карьерный консультант.

ДИАЛОГ КЛИЕНТА ({message_count} сообщений):
{conversation}

ЗАДАЧА: Проведи экспресс-анализ личности.

МЕТОДОЛОГИЯ:
- Психоанализ (Фрейд): защитные механизмы
- Аналитическая психология (Юнг): архетипы
- MBTI: предпочтения в принятии решений
- Big Five: основные черты личности

ФОРМАТ ОТВЕТА:
🎯 ЭКСПРЕСС-ПРОФИЛЬ

🧠 Психотип: [краткое описание]
📊 Основные черты: [2-3 характеристики]
💼 Подходящие сферы: [3-4 области]
🎓 Рекомендации: [конкретные направления]
⚠️ Зоны развития: [что развивать]

СТИЛЬ: Профессиональный, эмпатичный. До 300 слов.""",
            description="Стандартный экспресс-анализ",
            estimated_tokens=400
        )
        
        # Экспресс-анализ - длинный
        self.templates["express_analysis_long"] = PromptTemplate(
            id="express_analysis_long",
            type=PromptType.EXPRESS_ANALYSIS,
            length=PromptLength.LONG,
            template="""Ты — ведущий HR-психоаналитик с 20-летним опытом.

ДЕТАЛЬНЫЙ ДИАЛОГ КЛИЕНТА ({message_count} сообщений):
{conversation}

КОНТЕКСТ: {conversation}

ЗАДАЧА: Проведи глубокий экспресс-анализ личности.

МЕТОДОЛОГИЯ:
- Психоанализ (Фрейд): защитные механизмы, бессознательные мотивы
- Аналитическая психология (Юнг): архетипы, типы личности
- MBTI: предпочтения в восприятии и принятии решений
- Big Five: основные черты личности
- Анализ речевых паттернов и эмоциональных индикаторов

ФОРМАТ ОТВЕТА:
🎯 ДЕТАЛЬНЫЙ ЭКСПРЕСС-ПРОФИЛЬ

🧠 Психотип: [подробное описание на основе Юнга/Фрейда]
📊 Основные черты: [3-4 ключевые характеристики с примерами]
💼 Подходящие сферы: [4-5 областей с обоснованием]
🎓 Рекомендации по обучению: [конкретные направления и форматы]
⚠️ Зоны развития: [что стоит развивать и как]
💡 Карьерные перспективы: [потенциал роста]

СТИЛЬ: Профессиональный, эмпатичный, конкретный. До 500 слов.""",
            description="Детальный экспресс-анализ",
            estimated_tokens=600
        )
        
        # Психологическая консультация - короткая
        self.templates["psychology_consultation_short"] = PromptTemplate(
            id="psychology_consultation_short",
            type=PromptType.PSYCHOLOGY_CONSULTATION,
            length=PromptLength.SHORT,
            template="""Ты — психолог-консультант. Поддержи и пойми клиента.

СООБЩЕНИЕ: {conversation}

ОТВЕТ:
💙 Понимание чувств
🤗 Поддержка
💡 Мягкий совет

СТИЛЬ: Теплый, до 100 слов.""",
            description="Краткая психологическая поддержка",
            estimated_tokens=150
        )
        
        # Психологическая консультация - средняя
        self.templates["psychology_consultation_medium"] = PromptTemplate(
            id="psychology_consultation_medium",
            type=PromptType.PSYCHOLOGY_CONSULTATION,
            length=PromptLength.MEDIUM,
            template="""Ты — опытный психолог с большим сердцем.

ИСТОРИЯ РАЗГОВОРА:
{conversation}

ТЕКУЩЕЕ СООБЩЕНИЕ:
{conversation}

ТВОЯ РОЛЬ: Друг-психолог, который помнит весь разговор.

ПРИНЦИПЫ:
- СНАЧАЛА прояви эмпатию и понимание
- УЧИТЫВАЙ всю историю разговора
- НЕ давай советы, если не просят
- Поддерживай эмоционально

ФОРМАТ ОТВЕТА:
💙 Эмпатичный ответ (с учетом контекста)
🤗 Поддержка и принятие
💡 Мягкие рекомендации (если уместно)

СТИЛЬ: Теплый, понимающий. До 250 слов.""",
            description="Стандартная психологическая поддержка",
            estimated_tokens=300
        )
        
        # Карьерная консультация - средняя
        self.templates["career_consultation_medium"] = PromptTemplate(
            id="career_consultation_medium",
            type=PromptType.CAREER_CONSULTATION,
            length=PromptLength.MEDIUM,
            template="""Ты — HR-консультант с 15-летним опытом.

СООБЩЕНИЕ КЛИЕНТА:
{conversation}

КОНТЕКСТ: {conversation}

ТВОЯ РОЛЬ: Эксперт по карьере и развитию.

ВАЖНО: Отвечай ПОЛНОСТЬЮ на вопрос пользователя. Не обрывай ответ.

ФОКУС:
- Конкретные техники и методики
- Практические советы
- Карьерные стратегии
- Образовательные направления

ФОРМАТ ОТВЕТА:
💼 Практические рекомендации
🎯 Конкретные техники
📈 Карьерные стратегии
🎓 Образовательные направления

СТИЛЬ: Профессиональный, конкретный, ПОЛНЫЙ ответ. До 400 слов.""",
            description="Карьерная консультация",
            estimated_tokens=400
        )
        
        # Полный анализ
        self.templates["full_analysis"] = PromptTemplate(
            id="full_analysis",
            type=PromptType.FULL_ANALYSIS,
            length=PromptLength.EXTENDED,
            template="""Ты — ведущий психоаналитик и HR-эксперт с 20-летним опытом.

ДЕТАЛЬНЫЕ ОТВЕТЫ КЛИЕНТА:
{conversation}

ПРОВЕДИ ГЛУБОКИЙ ПСИХОАНАЛИЗ:

🧠 ПСИХОАНАЛИТИЧЕСКИЙ ПРОФИЛЬ:
- Структура личности (Ид/Эго/Суперэго)
- Защитные механизмы
- Бессознательные конфликты
- Травмы и их влияние

🎭 АРХЕТИПЫ И ТИПОЛОГИЯ:
- Доминирующий архетип по Юнгу
- MBTI тип с обоснованием
- Темперамент и особенности

📊 BIG FIVE (OCEAN):
- Открытость: [1-10] + обоснование
- Добросовестность: [1-10] + обоснование  
- Экстраверсия: [1-10] + обоснование
- Доброжелательность: [1-10] + обоснование
- Нейротизм: [1-10] + обоснование

💼 HR-РЕКОМЕНДАЦИИ:
- Подходящие роли и позиции
- Стиль управления/работы
- Мотивационные факторы
- Потенциальные риски

🎓 ОБРАЗОВАТЕЛЬНЫЕ РЕКОМЕНДАЦИИ:
- Конкретные направления обучения
- Форматы обучения (очное/заочное)
- Дополнительные навыки
- Карьерная траектория

🔮 ПРОГНОЗ РАЗВИТИЯ:
- Как будет развиваться личность
- Ключевые точки роста
- Рекомендации по саморазвитию

СТИЛЬ: Профессиональный, детальный, практичный. 1200-1500 слов.""",
            description="Полный психоанализ",
            estimated_tokens=800
        )
        

        # Эмоциональная поддержка\n        self.templates["emotional_support_short"] = PromptTemplate(\n            id="emotional_support_short",\n            type=PromptType.EMOTIONAL_SUPPORT,\n            length=PromptLength.SHORT,\n            template="""Ты — психолог-консультант. Поддержи и успокой клиента.\n\nСООБЩЕНИЕ: {conversation}\n\nОТВЕТ:\n💙 Понимание чувств\n🤗 Поддержка\n💡 Мягкий совет\n\nСТИЛЬ: Теплый, до 100 слов.""",\n            description="Краткая эмоциональная поддержка",\n            estimated_tokens=150\n        )\n\n        # Анализ самооценки\n        self.templates["self_esteem_analysis"] = PromptTemplate(\n            id="self_esteem_analysis",\n            type=PromptType.SELF_ESTEEM_ANALYSIS,\n            length=PromptLength.LONG,\n            template="""Ты — психолог-эксперт по самооценке. Проанализируй ответы на тест самооценки.\n\nОТВЕТЫ НА ТЕСТ:\n{conversation}\n\nПРОВЕДИ АНАЛИЗ САМООЦЕНКИ:\n\n🎯 УРОВЕНЬ САМООЦЕНКИ:\n- Общая оценка (низкая/средняя/высокая)\n- Конкретные показатели\n- Сильные и слабые стороны\n\n📊 ДЕТАЛЬНЫЙ АНАЛИЗ:\n- Уверенность в себе\n- Самопринятие\n- Самоуважение\n- Социальная уверенность\n\n💡 РЕКОМЕНДАЦИИ:\n- Конкретные шаги для повышения самооценки\n- Упражнения и практики\n- Работа с внутренним критиком\n\nСТИЛЬ: Профессиональный, эмпатичный, мотивирующий. 800-1200 слов.""",\n            description="Анализ самооценки",\n            estimated_tokens=600\n        )\n
        # Инициализируем метрики для всех шаблонов
        for template_id in self.templates:
            self.metrics[template_id] = PromptMetrics(template_id=template_id)
    
    def get_optimal_prompt(
        self, 
        prompt_type: PromptType, 
        available_tokens: int,
        user_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str]:
        """Получение оптимального промпта на основе доступных токенов и метрик"""
        
        # Получаем предпочтения пользователя
        user_prefs = self.user_preferences.get(user_id, {})
        
        # Фильтруем шаблоны по типу
        type_templates = {
            k: v for k, v in self.templates.items() 
            if v.type == prompt_type and v.active
        }
        
        if not type_templates:
            logger.error(f"Нет доступных шаблонов для типа {prompt_type}")
            return "", "default"
        
        # Выбираем оптимальную длину
        optimal_length = self._select_optimal_length(available_tokens, user_prefs)
        
        # Ищем шаблон подходящей длины
        suitable_templates = [
            t for t in type_templates.values() 
            if t.length == optimal_length and t.estimated_tokens <= available_tokens
        ]
        
        if not suitable_templates:
            # Если нет подходящих, берем самый короткий
            suitable_templates = [
                t for t in type_templates.values() 
                if t.estimated_tokens <= available_tokens
            ]
            suitable_templates.sort(key=lambda x: x.estimated_tokens)
        
        if not suitable_templates:
            # Если ничего не подходит, берем самый короткий
            suitable_templates = [min(type_templates.values(), key=lambda x: x.estimated_tokens)]
        
        # Выбираем лучший шаблон на основе метрик
        selected_template = self._select_best_template(suitable_templates)
        
        # Форматируем промпт
        formatted_prompt = self._format_prompt(selected_template, context or {})
        
        # Обновляем метрики
        self._update_template_metrics(selected_template.id)
        
        return formatted_prompt, selected_template.id
    
    def _select_optimal_length(self, available_tokens: int, user_prefs: Dict[str, Any]) -> PromptLength:
        """Выбор оптимальной длины промпта"""
        
        # Учитываем предпочтения пользователя
        preferred_length = user_prefs.get('preferred_length')
        if preferred_length:
            try:
                return PromptLength(preferred_length)
            except ValueError:
                pass
        
        # Выбираем на основе доступных токенов
        if available_tokens >= 600:
            return PromptLength.LONG
        elif available_tokens >= 400:
            return PromptLength.MEDIUM
        else:
            return PromptLength.SHORT
    
    def _select_best_template(self, templates: List[PromptTemplate]) -> PromptTemplate:
        """Выбор лучшего шаблона на основе метрик"""
        if len(templates) == 1:
            return templates[0]
        
        # Сортируем по успешности и частоте использования
        def score_template(template: PromptTemplate) -> float:
            metrics = self.metrics.get(template.id, PromptMetrics(template_id=template.id))
            
            # Составной скор: успешность (60%) + частота использования (40%)
            success_score = metrics.successful_uses / max(metrics.total_uses, 1)
            usage_score = min(metrics.total_uses / 100, 1.0)  # Нормализуем до 1.0
            
            return success_score * 0.6 + usage_score * 0.4
        
        return max(templates, key=score_template)
    
    def _format_prompt(self, template: PromptTemplate, context: Dict[str, Any]) -> str:
        """Форматирование промпта с контекстом"""
        try:
            return template.template.format(**context)
        except KeyError as e:
            logger.error(f"Ошибка форматирования промпта {template.id}: {e}")
            # Возвращаем базовый шаблон без форматирования
            return template.template
    
    def _update_template_metrics(self, template_id: str):
        """Обновление метрик использования шаблона"""
        if template_id in self.metrics:
            self.metrics[template_id].total_uses += 1
            self.metrics[template_id].last_used = datetime.now()
    
    def record_success(self, template_id: str, response_length: int, user_satisfaction: float = None):
        """Запись успешного использования шаблона"""
        if template_id in self.metrics:
            metrics = self.metrics[template_id]
            metrics.successful_uses += 1
            
            # Обновляем среднюю длину ответа
            if metrics.avg_response_length == 0:
                metrics.avg_response_length = response_length
            else:
                metrics.avg_response_length = (
                    (metrics.avg_response_length * (metrics.successful_uses - 1) + response_length) 
                    / metrics.successful_uses
                )
            
            # Обновляем среднюю удовлетворенность
            if user_satisfaction is not None:
                if metrics.avg_user_satisfaction == 0:
                    metrics.avg_user_satisfaction = user_satisfaction
                else:
                    metrics.avg_user_satisfaction = (
                        (metrics.avg_user_satisfaction * (metrics.successful_uses - 1) + user_satisfaction) 
                        / metrics.successful_uses
                    )
    
    def update_user_preferences(self, user_id: int, preferences: Dict[str, Any]):
        """Обновление предпочтений пользователя"""
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {}
        
        self.user_preferences[user_id].update(preferences)
        logger.info(f"Обновлены предпочтения пользователя {user_id}: {preferences}")
    
    def get_user_preferences(self, user_id: int) -> Dict[str, Any]:
        """Получение предпочтений пользователя"""
        return self.user_preferences.get(user_id, {})
    
    def get_template_stats(self) -> Dict[str, Dict[str, Any]]:
        """Получение статистики по шаблонам"""
        stats = {}
        
        for template_id, template in self.templates.items():
            metrics = self.metrics.get(template_id, PromptMetrics(template_id=template_id))
            
            stats[template_id] = {
                'type': template.type.value,
                'length': template.length.value,
                'estimated_tokens': template.estimated_tokens,
                'active': template.active,
                'description': template.description,
                'total_uses': metrics.total_uses,
                'successful_uses': metrics.successful_uses,
                'success_rate': metrics.successful_uses / max(metrics.total_uses, 1),
                'avg_response_length': metrics.avg_response_length,
                'avg_user_satisfaction': metrics.avg_user_satisfaction,
                'last_used': metrics.last_used.isoformat() if metrics.last_used else None
            }
        
        return stats
    
    def get_best_templates(self, prompt_type: PromptType, limit: int = 5) -> List[PromptTemplate]:
        """Получение лучших шаблонов по типу"""
        type_templates = [
            t for t in self.templates.values() 
            if t.type == prompt_type and t.active
        ]
        
        # Сортируем по метрикам
        def template_score(template: PromptTemplate) -> float:
            metrics = self.metrics.get(template.id, PromptMetrics(template_id=template.id))
            success_rate = metrics.successful_uses / max(metrics.total_uses, 1)
            return success_rate * 0.7 + (metrics.avg_user_satisfaction / 5.0) * 0.3
        
        sorted_templates = sorted(type_templates, key=template_score, reverse=True)
        return sorted_templates[:limit]