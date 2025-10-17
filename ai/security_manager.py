"""
═══════════════════════════════════════════════════════════════════
SECURITY MANAGER - БАЗОВАЯ ЗАЩИТА БОТА
═══════════════════════════════════════════════════════════════════

Базовая защита от атак:
- Rate limiting (ограничение запросов)
- Мониторинг расходов токенов
- Логирование подозрительной активности
- Защита от спама

📅 СОЗДАНО: 2025-10-17
🎯 ЦЕЛЬ: Защита от основных угроз без нарушения логики
"""

import logging
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

@dataclass
class SecurityAlert:
    """Алерт безопасности"""
    user_id: int
    alert_type: str
    description: str
    timestamp: float
    severity: str  # 'low', 'medium', 'high'

@dataclass
class RateLimit:
    """Настройки rate limiting"""
    max_requests: int = 10  # Максимум запросов
    time_window: int = 60   # В секундах (1 минута)
    max_tokens_per_hour: int = 5000  # Максимум токенов в час на пользователя

class SecurityManager:
    """Менеджер безопасности бота"""
    
    def __init__(self):
        self.user_requests = defaultdict(lambda: deque())  # user_id -> deque of timestamps
        self.user_tokens = defaultdict(int)  # user_id -> total tokens today
        self.blocked_users = set()  # Заблокированные пользователи
        self.security_alerts = []  # История алертов
        
        # Настройки защиты
        self.rate_limit = RateLimit()
        
        # Статистика
        self.total_requests = 0
        self.blocked_requests = 0
        self.security_incidents = 0
    
    def check_rate_limit(self, user_id: int) -> Tuple[bool, str]:
        """
        Проверка rate limiting для пользователя
        
        Returns:
            (is_allowed, reason)
        """
        current_time = time.time()
        
        # Очищаем старые запросы
        user_queue = self.user_requests[user_id]
        while user_queue and user_queue[0] < current_time - self.rate_limit.time_window:
            user_queue.popleft()
        
        # Проверяем лимит
        if len(user_queue) >= self.rate_limit.max_requests:
            self._log_security_alert(
                user_id, 
                'rate_limit_exceeded', 
                f'Превышен лимит запросов: {len(user_queue)}/{self.rate_limit.max_requests}',
                'medium'
            )
            self.blocked_requests += 1
            return False, f"Слишком много запросов. Подождите {self.rate_limit.time_window} секунд."
        
        # Добавляем текущий запрос
        user_queue.append(current_time)
        self.total_requests += 1
        
        return True, "OK"
    
    def check_token_limit(self, user_id: int, tokens_used: int) -> Tuple[bool, str]:
        """
        Проверка лимита токенов на пользователя
        
        Returns:
            (is_allowed, reason)
        """
        current_hour = int(time.time() // 3600)
        hour_key = f"{user_id}_{current_hour}"
        
        # Получаем токены за текущий час
        user_tokens_this_hour = self.user_tokens.get(hour_key, 0)
        
        if user_tokens_this_hour + tokens_used > self.rate_limit.max_tokens_per_hour:
            self._log_security_alert(
                user_id,
                'token_limit_exceeded',
                f'Превышен лимит токенов: {user_tokens_this_hour + tokens_used}/{self.rate_limit.max_tokens_per_hour}',
                'high'
            )
            return False, f"Превышен лимит токенов в час. Попробуйте позже."
        
        # Обновляем счетчик токенов
        self.user_tokens[hour_key] = user_tokens_this_hour + tokens_used
        
        return True, "OK"
    
    def check_spam_patterns(self, user_id: int, message: str) -> Tuple[bool, str]:
        """
        Проверка на спам-паттерны
        
        Returns:
            (is_spam, reason)
        """
        message_lower = message.lower().strip()
        
        # Список подозрительных паттернов
        spam_patterns = [
            'купить', 'продать', 'заработок', 'деньги', 'криптовалюта',
            'bitcoin', 'ethereum', 'инвестиции', 'брокер', 'казино',
            'xxx', 'порно', 'секс', 'знакомства', 'интим'
        ]
        
        for pattern in spam_patterns:
            if pattern in message_lower:
                self._log_security_alert(
                    user_id,
                    'spam_detected',
                    f'Обнаружен спам: "{pattern}" в сообщении',
                    'medium'
                )
                return True, "Сообщение содержит недопустимый контент."
        
        # Проверка на повторяющиеся сообщения
        if len(message_lower) < 3:
            return True, "Сообщение слишком короткое."
        
        return False, "OK"
    
    def check_user_behavior(self, user_id: int) -> Tuple[bool, str]:
        """
        Проверка подозрительного поведения пользователя
        
        Returns:
            (is_suspicious, reason)
        """
        # Проверяем, не заблокирован ли пользователь
        if user_id in self.blocked_users:
            return False, "Пользователь заблокирован."
        
        # Проверяем количество алертов от пользователя
        user_alerts = [alert for alert in self.security_alerts if alert.user_id == user_id]
        recent_alerts = [alert for alert in user_alerts if alert.timestamp > time.time() - 3600]  # За последний час
        
        if len(recent_alerts) >= 3:
            self._log_security_alert(
                user_id,
                'suspicious_behavior',
                f'Множественные нарушения: {len(recent_alerts)} алертов за час',
                'high'
            )
            return False, "Обнаружено подозрительное поведение. Доступ временно ограничен."
        
        return True, "OK"
    
    def _log_security_alert(self, user_id: int, alert_type: str, description: str, severity: str):
        """Логирование алерта безопасности"""
        alert = SecurityAlert(
            user_id=user_id,
            alert_type=alert_type,
            description=description,
            timestamp=time.time(),
            severity=severity
        )
        
        self.security_alerts.append(alert)
        self.security_incidents += 1
        
        # Ограничиваем размер истории алертов
        if len(self.security_alerts) > 1000:
            self.security_alerts = self.security_alerts[-500:]
        
        logger.warning(f"SECURITY ALERT [{severity.upper()}]: User {user_id} - {alert_type}: {description}")
    
    def block_user(self, user_id: int, reason: str):
        """Блокировка пользователя"""
        self.blocked_users.add(user_id)
        self._log_security_alert(user_id, 'user_blocked', reason, 'high')
        logger.warning(f"USER BLOCKED: {user_id} - {reason}")
    
    def unblock_user(self, user_id: int):
        """Разблокировка пользователя"""
        self.blocked_users.discard(user_id)
        logger.info(f"USER UNBLOCKED: {user_id}")
    
    def get_security_stats(self) -> Dict:
        """Получение статистики безопасности"""
        return {
            'total_requests': self.total_requests,
            'blocked_requests': self.blocked_requests,
            'security_incidents': self.security_incidents,
            'blocked_users_count': len(self.blocked_users),
            'recent_alerts': len([a for a in self.security_alerts if a.timestamp > time.time() - 3600])
        }
    
    def get_user_stats(self, user_id: int) -> Dict:
        """Получение статистики пользователя"""
        user_requests_count = len(self.user_requests[user_id])
        user_alerts = [alert for alert in self.security_alerts if alert.user_id == user_id]
        
        return {
            'requests_last_minute': user_requests_count,
            'total_alerts': len(user_alerts),
            'is_blocked': user_id in self.blocked_users,
            'tokens_today': sum(v for k, v in self.user_tokens.items() if k.startswith(f"{user_id}_"))
        }
