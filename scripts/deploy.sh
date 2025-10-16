#!/bin/bash
# Скрипт развертывания HR-Психоаналитик Бота v2.0

set -e

echo "🚀 Развертывание HR-Психоаналитик Бота v2.0"

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден. Установите Python 3.11+"
    exit 1
fi

# Проверка версии Python
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.11"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Требуется Python $REQUIRED_VERSION или выше. Текущая версия: $PYTHON_VERSION"
    exit 1
fi

echo "✅ Python $PYTHON_VERSION найден"

# Создание виртуального окружения
if [ ! -d "venv" ]; then
    echo "📦 Создание виртуального окружения..."
    python3 -m venv venv
fi

# Активация виртуального окружения
echo "🔧 Активация виртуального окружения..."
source venv/bin/activate

# Установка зависимостей
echo "📚 Установка зависимостей..."
pip install --upgrade pip
pip install -r requirements.txt

# Создание директорий
echo "📁 Создание необходимых директорий..."
mkdir -p logs
mkdir -p data

# Копирование конфигурации
if [ ! -f ".env" ]; then
    echo "⚙️ Создание файла конфигурации..."
    cp config/.env.example .env
    echo "📝 Отредактируйте файл .env с вашими API ключами"
fi

# Проверка конфигурации
echo "🔍 Проверка конфигурации..."
python3 -c "
from bot.config import BotConfig
try:
    config = BotConfig.from_yaml('config/settings.yaml')
    print('✅ Конфигурация загружена успешно')
except Exception as e:
    print(f'❌ Ошибка конфигурации: {e}')
    exit(1)
"

# Запуск тестов
echo "🧪 Запуск тестов..."
python3 -m pytest tests/ -v

# Создание systemd сервиса (опционально)
if [ "$1" = "--systemd" ]; then
    echo "🔧 Создание systemd сервиса..."
    sudo tee /etc/systemd/system/hr-psychoanalyst-bot.service > /dev/null <<EOF
[Unit]
Description=HR-Psychoanalyst Bot v2.0
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/python bot/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable hr-psychoanalyst-bot
    echo "✅ Systemd сервис создан. Запуск: sudo systemctl start hr-psychoanalyst-bot"
fi

echo "🎉 Развертывание завершено!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Отредактируйте .env файл с вашими API ключами"
echo "2. Запустите бота: python bot/main.py"
echo "3. Или используйте systemd: sudo systemctl start hr-psychoanalyst-bot"
echo ""
echo "📊 Мониторинг:"
echo "- Логи: tail -f logs/bot.log"
echo "- Статус: systemctl status hr-psychoanalyst-bot"
echo "- Перезапуск: systemctl restart hr-psychoanalyst-bot"