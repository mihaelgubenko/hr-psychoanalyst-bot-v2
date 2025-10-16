# 🚀 Руководство по развертыванию HR-Психоаналитик Бота v2.0

## 📋 Предварительные требования

- **Python 3.11+** - основная среда выполнения
- **Git** - для клонирования репозитория
- **Telegram Bot Token** - от @BotFather
- **OpenAI API Key** - от platform.openai.com
- **Минимум 1GB RAM** - для стабильной работы
- **Минимум 1GB дискового пространства** - для базы данных и логов

## 🔧 Быстрое развертывание

### 1. Клонирование репозитория

```bash
git clone https://github.com/your-username/hr-psychoanalyst-bot-v2.git
cd hr-psychoanalyst-bot-v2
```

### 2. Автоматическая установка

```bash
# Запуск скрипта развертывания
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

### 3. Настройка конфигурации

```bash
# Копирование примера конфигурации
cp config/.env.example .env

# Редактирование конфигурации
nano .env
```

**Заполните следующие переменные в .env:**

```env
BOT_TOKEN=your_telegram_bot_token_here
OPENAI_API_KEY=your_openai_api_key_here
PAYMENT_TOKEN=your_payment_token_here
```

### 4. Запуск бота

```bash
# Активация виртуального окружения
source venv/bin/activate

# Запуск бота
python bot/main.py
```

## 🐳 Развертывание с Docker

### 1. Создание Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода
COPY . .

# Создание пользователя
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

# Запуск
CMD ["python", "bot/main.py"]
```

### 2. Docker Compose

```yaml
version: '3.8'

services:
  bot:
    build: .
    environment:
      - BOT_TOKEN=${BOT_TOKEN}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - PAYMENT_TOKEN=${PAYMENT_TOKEN}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  redis_data:
```

### 3. Запуск с Docker

```bash
# Создание .env файла
cp config/.env.example .env
# Отредактируйте .env

# Запуск
docker-compose up -d

# Просмотр логов
docker-compose logs -f bot
```

## ☁️ Развертывание в облаке

### Railway.app

1. **Подключение репозитория:**
   - Войдите в Railway.app
   - Нажмите "New Project"
   - Выберите "Deploy from GitHub repo"
   - Выберите ваш репозиторий

2. **Настройка переменных окружения:**
   ```env
   BOT_TOKEN=your_telegram_bot_token
   OPENAI_API_KEY=your_openai_api_key
   PAYMENT_TOKEN=your_payment_token
   ```

3. **Настройка команды запуска:**
   ```
   python bot/main.py
   ```

4. **Деплой:**
   - Railway автоматически развернет бота
   - Проверьте логи в панели управления

### Heroku

1. **Создание Procfile:**
   ```
   web: python bot/main.py
   ```

2. **Создание runtime.txt:**
   ```
   python-3.11.0
   ```

3. **Деплой:**
   ```bash
   # Установка Heroku CLI
   # Создание приложения
   heroku create your-bot-name
   
   # Настройка переменных
   heroku config:set BOT_TOKEN=your_token
   heroku config:set OPENAI_API_KEY=your_key
   
   # Деплой
   git push heroku main
   ```

### DigitalOcean App Platform

1. **Создание app.yaml:**
   ```yaml
   name: hr-psychoanalyst-bot
   services:
   - name: bot
     source_dir: /
     github:
       repo: your-username/hr-psychoanalyst-bot-v2
       branch: main
     run_command: python bot/main.py
     environment_slug: python
     instance_count: 1
     instance_size_slug: basic-xxs
     envs:
     - key: BOT_TOKEN
       value: your_telegram_bot_token
     - key: OPENAI_API_KEY
       value: your_openai_api_key
   ```

2. **Деплой через веб-интерфейс DigitalOcean**

## 🔧 Настройка для продакшена

### 1. Systemd сервис

```bash
# Создание сервиса
sudo nano /etc/systemd/system/hr-psychoanalyst-bot.service
```

**Содержимое файла:**
```ini
[Unit]
Description=HR-Psychoanalyst Bot v2.0
After=network.target

[Service]
Type=simple
User=bot
WorkingDirectory=/opt/hr-psychoanalyst-bot-v2
Environment=PATH=/opt/hr-psychoanalyst-bot-v2/venv/bin
ExecStart=/opt/hr-psychoanalyst-bot-v2/venv/bin/python bot/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Активация сервиса:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable hr-psychoanalyst-bot
sudo systemctl start hr-psychoanalyst-bot
```

### 2. Nginx (опционально)

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. Мониторинг

**Prometheus + Grafana:**
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'hr-psychoanalyst-bot'
    static_configs:
      - targets: ['localhost:8000']
```

**Логирование:**
```bash
# Настройка logrotate
sudo nano /etc/logrotate.d/hr-psychoanalyst-bot
```

## 🔍 Проверка развертывания

### 1. Проверка статуса

```bash
# Проверка логов
tail -f logs/bot.log

# Проверка статуса (systemd)
sudo systemctl status hr-psychoanalyst-bot

# Проверка процессов
ps aux | grep python
```

### 2. Тестирование

```bash
# Запуск тестов
python -m pytest tests/ -v

# Проверка конфигурации
python -c "from bot.config import BotConfig; print('Config OK')"
```

### 3. Мониторинг метрик

```bash
# Проверка API (если включен)
curl http://localhost:8000/health

# Проверка базы данных
sqlite3 psychoanalyst.db ".tables"
```

## 🚨 Устранение неполадок

### Частые проблемы

1. **Ошибка "Module not found":**
   ```bash
   # Активируйте виртуальное окружение
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Ошибка "API key not found":**
   ```bash
   # Проверьте .env файл
   cat .env
   # Убедитесь, что переменные установлены
   ```

3. **Ошибка "Database locked":**
   ```bash
   # Перезапустите бота
   sudo systemctl restart hr-psychoanalyst-bot
   ```

4. **Высокое потребление памяти:**
   ```bash
   # Проверьте кэш
   python -c "from core.response_cache import ResponseCache; cache = ResponseCache(); cache.clear()"
   ```

### Логи и отладка

```bash
# Включение debug режима
export DEBUG=true
python bot/main.py

# Подробные логи
export LOG_LEVEL=DEBUG
python bot/main.py
```

## 📊 Мониторинг и метрики

### 1. Основные метрики

- **Запросы в минуту** - нагрузка на бота
- **Время ответа** - производительность
- **Использование токенов** - затраты на API
- **Ошибки** - стабильность системы

### 2. Алерты

Настройте уведомления для:
- Высокого потребления токенов (>1000 в минуту)
- Медленных ответов (>5 секунд)
- Ошибок API (>5% от запросов)
- Недоступности бота

### 3. Резервное копирование

```bash
# Бэкап базы данных
cp psychoanalyst.db backup/psychoanalyst_$(date +%Y%m%d).db

# Бэкап конфигурации
tar -czf backup/config_$(date +%Y%m%d).tar.gz config/
```

## 🔄 Обновления

### 1. Обновление кода

```bash
# Получение обновлений
git pull origin main

# Установка новых зависимостей
pip install -r requirements.txt

# Перезапуск
sudo systemctl restart hr-psychoanalyst-bot
```

### 2. Миграция данных

```bash
# Создание бэкапа
cp psychoanalyst.db psychoanalyst_backup.db

# Применение миграций (если есть)
python scripts/migrate.py
```

## 📞 Поддержка

- **Документация:** [docs/](docs/)
- **Issues:** GitHub Issues
- **Логи:** `logs/bot.log`
- **Метрики:** Prometheus/Grafana

---

**Версия:** 2.0  
**Последнее обновление:** 2024-01-15  
**Статус:** Готов к продакшену