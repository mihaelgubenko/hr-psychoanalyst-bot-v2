"""
Менеджер токенов для оптимизации использования OpenAI API
Улучшенная версия с типизацией и метриками
"""

# import tiktoken  # Временно отключено из-за проблем с установкой
import logging
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import time

logger = logging.getLogger(__name__)

@dataclass
class TokenUsage:
    """Информация об использовании токенов с метриками"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float
    processing_time: float = 0.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    @property
    def cost_per_token(self) -> float:
        """Стоимость за токен"""
        return self.estimated_cost / max(self.total_tokens, 1)
    
    def to_dict(self) -> Dict[str, Union[int, float, str]]:
        """Преобразование в словарь"""
        return {
            'prompt_tokens': self.prompt_tokens,
            'completion_tokens': self.completion_tokens,
            'total_tokens': self.total_tokens,
            'estimated_cost': self.estimated_cost,
            'processing_time': self.processing_time,
            'timestamp': self.timestamp.isoformat()
        }

class TokenManager:
    """Менеджер токенов с улучшенной оптимизацией и метриками"""
    
    def __init__(self, config):
        self.config = config
        # self.encoding = tiktoken.get_encoding("cl100k_base")  # Временно отключено
        self.encoding = None
        
        # Стоимость токенов для разных моделей (за 1K токенов)
        self.token_costs = {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-3.5-turbo": {"input": 0.001, "output": 0.002},
            "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004}
        }
        
        # Статистика использования
        self.usage_stats = {
            'total_tokens': 0,
            'total_requests': 0,
            'total_cost': 0.0,
            'avg_tokens_per_request': 0.0,
            'avg_cost_per_request': 0.0
        }
    
    def count_tokens(self, text: str) -> int:
        """Точный подсчет токенов в тексте"""
        try:
            if self.encoding:
                return len(self.encoding.encode(text))
            else:
                # Fallback: примерная оценка (1 токен ≈ 4 символа)
                return len(text) // 4
        except Exception as e:
            logger.error(f"Ошибка подсчета токенов: {e}")
            # Fallback: примерная оценка (1 токен ≈ 4 символа)
            return len(text) // 4
    
    def count_tokens_list(self, texts: List[str]) -> int:
        """Подсчет токенов в списке текстов"""
        return sum(self.count_tokens(text) for text in texts)
    
    def estimate_response_tokens(self, prompt_tokens: int, context_length: int, prompt_type: str = "general") -> int:
        """Улучшенная оценка количества токенов в ответе"""
        # Базовые оценки по типам промптов
        base_estimates = {
            "express_analysis": 300,
            "full_analysis": 800,
            "psychology_consultation": 200,
            "career_consultation": 400,
            "self_esteem_analysis": 600,
            "general": 500
        }
        
        base_estimate = base_estimates.get(prompt_type, base_estimates["general"])
        
        # Корректировка на основе длины промпта
        if prompt_tokens > 2000:
            base_estimate = min(base_estimate + 200, 1000)
        elif prompt_tokens < 500:
            base_estimate = max(base_estimate - 100, 100)
        
        # Корректировка на основе контекста
        if context_length > 10:
            base_estimate = min(base_estimate + 150, 1000)
        elif context_length < 3:
            base_estimate = max(base_estimate - 50, 100)
        
        return min(base_estimate, self.config.response_tokens)
    
    def calculate_available_tokens(self, prompt: str, context: str, user_type: str = "free") -> int:
        """Расчет доступных токенов для ответа с учетом пользователя"""
        prompt_tokens = self.count_tokens(prompt)
        context_tokens = self.count_tokens(context)
        
        # Получаем лимиты для пользователя
        user_limits = self.config.get_user_limits(user_type)
        max_tokens = user_limits["max_tokens"]
        
        # Резервируем место для ответа
        available_for_prompt = max_tokens - self.config.response_tokens
        
        # Если промпт + контекст превышают лимит
        if prompt_tokens + context_tokens > available_for_prompt:
            # Сжимаем контекст
            max_context_tokens = available_for_prompt - prompt_tokens
            return max_context_tokens
        
        return context_tokens
    
    def optimize_prompt(
        self, 
        prompt: str, 
        context: str, 
        user_type: str = "free",
        prompt_type: str = "general"
    ) -> Tuple[str, str, TokenUsage]:
        """Оптимизация промпта с улучшенной логикой"""
        start_time = time.time()
        
        prompt_tokens = self.count_tokens(prompt)
        context_tokens = self.count_tokens(context)
        
        # Получаем адаптивные лимиты
        conversation_length = len(context.split('\n')) if context else 0
        adaptive_limits = self.config.get_adaptive_limits(conversation_length, user_type)
        max_tokens = adaptive_limits["max_tokens"]
        
        # Резервируем место для ответа
        available_for_prompt = max_tokens - self.config.response_tokens
        
        # Если все помещается
        if prompt_tokens + context_tokens <= available_for_prompt:
            total_tokens = prompt_tokens + context_tokens
            estimated_response_tokens = self.estimate_response_tokens(
                prompt_tokens, conversation_length, prompt_type
            )
            estimated_cost = self._calculate_cost(total_tokens + estimated_response_tokens, "gpt-4")
            
            processing_time = time.time() - start_time
            
            usage = TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=estimated_response_tokens,
                total_tokens=total_tokens + estimated_response_tokens,
                estimated_cost=estimated_cost,
                processing_time=processing_time
            )
            
            self._update_stats(usage)
            return prompt, context, usage
        
        # Нужно сжимать контекст
        max_context_tokens = available_for_prompt - prompt_tokens
        
        if max_context_tokens <= 0:
            # Если даже промпт не помещается, используем минимальный контекст
            max_context_tokens = self.config.min_tokens
            logger.warning(f"Промпт слишком длинный, используется минимальный контекст")
        
        # Сжимаем контекст
        compressed_context = self._compress_context(context, max_context_tokens)
        
        final_tokens = prompt_tokens + self.count_tokens(compressed_context)
        estimated_response_tokens = self.estimate_response_tokens(
            prompt_tokens, conversation_length, prompt_type
        )
        estimated_cost = self._calculate_cost(final_tokens + estimated_response_tokens, "gpt-4")
        
        processing_time = time.time() - start_time
        
        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=estimated_response_tokens,
            total_tokens=final_tokens + estimated_response_tokens,
            estimated_cost=estimated_cost,
            processing_time=processing_time
        )
        
        self._update_stats(usage)
        return prompt, compressed_context, usage
    
    def _compress_context(self, context: str, max_tokens: int) -> str:
        """Умное сжатие контекста с сохранением важной информации"""
        if self.count_tokens(context) <= max_tokens:
            return context
        
        # Разбиваем на предложения
        sentences = context.split('. ')
        
        # Приоритизируем последние предложения
        important_sentences = sentences[-3:]  # Последние 3 предложения
        
        # Добавляем предложения с ключевыми словами
        key_words = [
            'важно', 'проблема', 'цель', 'мечта', 'страх', 'тревога', 
            'работа', 'карьера', 'отношения', 'семья', 'любовь', 'деньги'
        ]
        
        for sentence in sentences[:-3]:
            if any(word in sentence.lower() for word in key_words):
                important_sentences.insert(-3, sentence)
        
        # Собираем сжатый контекст
        compressed = '. '.join(important_sentences)
        
        # Если все еще не помещается, обрезаем
        while self.count_tokens(compressed) > max_tokens and len(compressed) > 100:
            compressed = compressed[:-100] + "..."
        
        return compressed
    
    def _calculate_cost(self, tokens: int, model: str = "gpt-4") -> float:
        """Расчет примерной стоимости запроса"""
        if model not in self.token_costs:
            model = "gpt-4"
        
        # Разделяем на входные и выходные токены (примерно 70/30)
        input_tokens = int(tokens * 0.7)
        output_tokens = int(tokens * 0.3)
        
        cost_per_1k_input = self.token_costs[model]["input"]
        cost_per_1k_output = self.token_costs[model]["output"]
        
        input_cost = (input_tokens / 1000) * cost_per_1k_input
        output_cost = (output_tokens / 1000) * cost_per_1k_output
        
        return input_cost + output_cost
    
    def _update_stats(self, usage: TokenUsage):
        """Обновление статистики использования"""
        self.usage_stats['total_tokens'] += usage.total_tokens
        self.usage_stats['total_requests'] += 1
        self.usage_stats['total_cost'] += usage.estimated_cost
        self.usage_stats['avg_tokens_per_request'] = (
            self.usage_stats['total_tokens'] / self.usage_stats['total_requests']
        )
        self.usage_stats['avg_cost_per_request'] = (
            self.usage_stats['total_cost'] / self.usage_stats['total_requests']
        )
    
    def split_long_response(self, response: str, max_length: int = None) -> List[str]:
        """Разбиение длинного ответа на части с улучшенной логикой"""
        if max_length is None:
            max_length = self.config.max_message_length
        
        if len(response) <= max_length:
            return [response]
        
        parts = []
        current_part = ""
        
        # Разбиваем по абзацам
        paragraphs = response.split('\n\n')
        
        for paragraph in paragraphs:
            if len(current_part + paragraph) <= max_length:
                current_part += "\n\n" + paragraph if current_part else paragraph
            else:
                if current_part:
                    parts.append(current_part.strip())
                
                # Если один абзац слишком длинный, разбиваем его
                if len(paragraph) > max_length:
                    sub_parts = self._split_long_paragraph(paragraph, max_length)
                    parts.extend(sub_parts[:-1])  # Добавляем все кроме последнего
                    current_part = sub_parts[-1]  # Последний становится текущим
                else:
                    current_part = paragraph
        
        if current_part:
            parts.append(current_part.strip())
        
        return parts
    
    def _split_long_paragraph(self, paragraph: str, max_length: int) -> List[str]:
        """Разбиение длинного абзаца на части"""
        parts = []
        current_part = ""
        
        sentences = paragraph.split('. ')
        
        for sentence in sentences:
            if len(current_part + sentence) <= max_length:
                current_part += ". " + sentence if current_part else sentence
            else:
                if current_part:
                    parts.append(current_part.strip())
                current_part = sentence
        
        if current_part:
            parts.append(current_part.strip())
        
        return parts
    
    def is_response_truncated(self, response: str) -> bool:
        """Улучшенная проверка обрезанного ответа"""
        # Индикаторы обрезанного ответа
        truncation_indicators = [
            response.endswith('...'),
            response.endswith('…'),
            not response.endswith('.'),
            not response.endswith('!'),
            not response.endswith('?'),
            len(response.split()) < 10,  # Слишком короткий ответ
            'продолжение следует' in response.lower(),
            'to be continued' in response.lower()
        ]
        
        return any(truncation_indicators)
    
    def get_continuation_prompt(self, truncated_response: str) -> str:
        """Получение промпта для продолжения обрезанного ответа"""
        # Берем последние 200 символов для контекста
        context = truncated_response[-200:] if len(truncated_response) > 200 else truncated_response
        
        return f"""Продолжи ответ с того места, где остановился. 
Контекст: {context}

Продолжение:"""
    
    def get_usage_stats(self) -> Dict[str, Union[int, float]]:
        """Получение статистики использования"""
        return self.usage_stats.copy()
    
    def reset_stats(self):
        """Сброс статистики"""
        self.usage_stats = {
            'total_tokens': 0,
            'total_requests': 0,
            'total_cost': 0.0,
            'avg_tokens_per_request': 0.0,
            'avg_cost_per_request': 0.0
        }