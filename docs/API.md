# API Документация HR-Психоаналитик Бота v2.0

## 🎯 Обзор

HR-Психоаналитик Бот v2.0 предоставляет RESTful API для управления ботом, мониторинга и аналитики.

## 🔗 Базовый URL

```
https://your-domain.com/api/v2
```

## 🔐 Аутентификация

Все запросы требуют API ключ в заголовке:

```http
Authorization: Bearer YOUR_API_KEY
```

## 📊 Endpoints

### 1. Статус системы

#### GET /health

Получить статус здоровья системы.

**Ответ:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "uptime": 3600,
  "components": {
    "database": "healthy",
    "openai": "healthy",
    "cache": "healthy"
  },
  "metrics": {
    "total_requests": 1250,
    "active_users": 45,
    "avg_response_time": 1.2
  }
}
```

### 2. Управление пользователями

#### GET /users/{user_id}

Получить информацию о пользователе.

**Параметры:**
- `user_id` (int) - ID пользователя Telegram

**Ответ:**
```json
{
  "user_id": 12345,
  "analyses_count": 3,
  "last_activity": "2024-01-15T10:30:00Z",
  "preferences": {
    "preferred_prompt_length": "medium",
    "preferred_style": "detailed"
  },
  "usage_stats": {
    "total_requests": 25,
    "total_tokens": 15000,
    "cache_hit_rate": 0.75
  }
}
```

#### DELETE /users/{user_id}

Удалить данные пользователя.

**Ответ:**
```json
{
  "success": true,
  "message": "Данные пользователя удалены"
}
```

### 3. Анализы

#### GET /users/{user_id}/analyses

Получить список анализов пользователя.

**Параметры запроса:**
- `limit` (int, optional) - Количество записей (по умолчанию 10)
- `offset` (int, optional) - Смещение (по умолчанию 0)
- `type` (string, optional) - Тип анализа (express, full, self_esteem)

**Ответ:**
```json
{
  "analyses": [
    {
      "id": 1,
      "type": "express_analysis",
      "created_at": "2024-01-15T10:30:00Z",
      "payment_status": "free",
      "summary": "Краткое описание анализа"
    }
  ],
  "total": 3,
  "limit": 10,
  "offset": 0
}
```

#### GET /analyses/{analysis_id}

Получить детальную информацию об анализе.

**Ответ:**
```json
{
  "id": 1,
  "user_id": 12345,
  "type": "express_analysis",
  "analysis_data": {
    "psychotype": "Интроверт-интуит",
    "traits": ["аналитичность", "эмпатия"],
    "recommendations": ["развитие коммуникативных навыков"]
  },
  "created_at": "2024-01-15T10:30:00Z",
  "payment_status": "free"
}
```

### 4. Статистика

#### GET /stats/overview

Получить общую статистику системы.

**Ответ:**
```json
{
  "total_users": 150,
  "total_analyses": 450,
  "total_requests": 5000,
  "total_tokens": 2500000,
  "avg_response_time": 1.2,
  "cache_hit_rate": 0.75,
  "conversion_rate": 0.15,
  "revenue": 22500
}
```

#### GET /stats/usage

Получить статистику использования за период.

**Параметры запроса:**
- `start_date` (string) - Дата начала (YYYY-MM-DD)
- `end_date` (string) - Дата окончания (YYYY-MM-DD)
- `granularity` (string) - Детализация (hour, day, week)

**Ответ:**
```json
{
  "period": {
    "start": "2024-01-01",
    "end": "2024-01-31"
  },
  "data": [
    {
      "date": "2024-01-01",
      "requests": 150,
      "users": 25,
      "tokens": 75000,
      "revenue": 500
    }
  ]
}
```

### 5. Мониторинг

#### GET /monitoring/tokens

Получить статистику использования токенов.

**Ответ:**
```json
{
  "total_tokens": 2500000,
  "avg_tokens_per_request": 500,
  "cost_per_token": 0.00003,
  "total_cost": 75.0,
  "by_model": {
    "gpt-4": {
      "tokens": 2000000,
      "cost": 60.0
    },
    "gpt-3.5-turbo": {
      "tokens": 500000,
      "cost": 15.0
    }
  }
}
```

#### GET /monitoring/performance

Получить метрики производительности.

**Ответ:**
```json
{
  "avg_response_time": 1.2,
  "p95_response_time": 3.5,
  "p99_response_time": 5.0,
  "error_rate": 0.02,
  "throughput": 100,
  "cache_hit_rate": 0.75
}
```

### 6. A/B тестирование

#### GET /ab-tests

Получить список активных A/B тестов.

**Ответ:**
```json
{
  "tests": [
    {
      "id": "express_analysis_v2",
      "name": "Новый промпт экспресс-анализа",
      "status": "active",
      "variants": [
        {
          "id": "control",
          "name": "Контрольная группа",
          "traffic": 0.5
        },
        {
          "id": "variant_a",
          "name": "Вариант A",
          "traffic": 0.5
        }
      ],
      "metrics": {
        "conversion_rate": 0.15,
        "avg_satisfaction": 4.2,
        "sample_size": 1000
      }
    }
  ]
}
```

#### POST /ab-tests/{test_id}/conversion

Записать конверсию для A/B теста.

**Тело запроса:**
```json
{
  "user_id": 12345,
  "variant_id": "variant_a",
  "conversion_type": "purchase",
  "value": 500
}
```

### 7. Управление кэшем

#### GET /cache/stats

Получить статистику кэша.

**Ответ:**
```json
{
  "total_entries": 1000,
  "hit_rate": 0.75,
  "memory_usage": "50MB",
  "evictions": 150,
  "by_type": {
    "express_analysis": {
      "entries": 400,
      "hit_rate": 0.8
    },
    "psychology_consultation": {
      "entries": 300,
      "hit_rate": 0.7
    }
  }
}
```

#### DELETE /cache

Очистить кэш.

**Ответ:**
```json
{
  "success": true,
  "message": "Кэш очищен",
  "entries_removed": 1000
}
```

## 📝 Коды ошибок

| Код | Описание |
|-----|----------|
| 200 | Успешно |
| 400 | Неверный запрос |
| 401 | Не авторизован |
| 403 | Доступ запрещен |
| 404 | Не найдено |
| 429 | Превышен лимит запросов |
| 500 | Внутренняя ошибка сервера |

## 🔄 Webhooks

### Уведомления о событиях

Бот может отправлять webhooks при определенных событиях:

#### POST /webhooks/events

**Тело запроса:**
```json
{
  "event_type": "analysis_completed",
  "user_id": 12345,
  "analysis_id": 1,
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "analysis_type": "express_analysis",
    "completion_time": 2.5
  }
}
```

**Типы событий:**
- `analysis_completed` - Анализ завершен
- `user_registered` - Пользователь зарегистрирован
- `payment_received` - Получена оплата
- `error_occurred` - Произошла ошибка

## 🧪 Тестирование

### Примеры запросов

#### cURL

```bash
# Получить статус системы
curl -H "Authorization: Bearer YOUR_API_KEY" \
     https://your-domain.com/api/v2/health

# Получить анализы пользователя
curl -H "Authorization: Bearer YOUR_API_KEY" \
     https://your-domain.com/api/v2/users/12345/analyses

# Очистить кэш
curl -X DELETE -H "Authorization: Bearer YOUR_API_KEY" \
     https://your-domain.com/api/v2/cache
```

#### Python

```python
import requests

headers = {"Authorization": "Bearer YOUR_API_KEY"}
base_url = "https://your-domain.com/api/v2"

# Получить статус
response = requests.get(f"{base_url}/health", headers=headers)
print(response.json())

# Получить статистику
response = requests.get(f"{base_url}/stats/overview", headers=headers)
print(response.json())
```

## 📊 Лимиты

- **Rate Limiting**: 100 запросов в минуту на API ключ
- **Размер запроса**: Максимум 1MB
- **Timeout**: 30 секунд для всех запросов
- **Retry**: До 3 попыток с экспоненциальной задержкой

## 🔒 Безопасность

- Все запросы должны использовать HTTPS
- API ключи должны храниться в безопасном месте
- IP адреса могут быть заблокированы при подозрительной активности
- Логирование всех запросов для аудита