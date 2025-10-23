# 🤖 Деплой Telegram ботов на VDS

Руководство по развертыванию Telegram ботов на том же сервере вместе с Flask приложением.

---

## 📋 Структура проектов

```
/home/deploy/
├── app/                      # Flask приложение Quick Score
├── bot1/                     # Первый Telegram бот
├── bot2/                     # Второй Telegram бот
└── bots/                     # Общая папка для ботов (опционально)
```

---

## 🚀 Деплой Telegram бота

### Шаг 1: Клонирование репозитория бота

```bash
cd /home/deploy
git clone https://github.com/YOUR_USERNAME/YOUR_BOT_REPO.git bot1
cd bot1
```

### Шаг 2: Создание виртуального окружения

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Шаг 3: Настройка конфигурации

Создайте файл `.env`:

```bash
nano .env
```

Пример содержимого:

```env
# Telegram Bot Token
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Database (если бот использует БД)
DATABASE_URL=sqlite:///bot.db

# Другие настройки
ADMIN_ID=123456789
LOG_LEVEL=INFO
```

### Шаг 4: Создание systemd сервиса

```bash
sudo nano /etc/systemd/system/telegram-bot1.service
```

Содержимое файла:

```ini
[Unit]
Description=Telegram Bot 1
After=network.target

[Service]
Type=simple
User=deploy
Group=deploy
WorkingDirectory=/home/deploy/bot1
Environment="PATH=/home/deploy/bot1/venv/bin"
EnvironmentFile=/home/deploy/bot1/.env

# Запуск бота
ExecStart=/home/deploy/bot1/venv/bin/python main.py

# Перезапуск при сбое
Restart=always
RestartSec=10

# Логирование
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Шаг 5: Запуск бота

```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot1
sudo systemctl start telegram-bot1
```

### Шаг 6: Проверка работы

```bash
# Статус
sudo systemctl status telegram-bot1

# Логи в реальном времени
sudo journalctl -u telegram-bot1 -f

# Последние 100 строк логов
sudo journalctl -u telegram-bot1 -n 100 --no-pager
```

---

## 🔄 Автоматическое обновление бота

### Создание скрипта обновления

```bash
nano /home/deploy/bot1/update.sh
```

Содержимое:

```bash
#!/bin/bash

BOT_DIR="/home/deploy/bot1"
SERVICE_NAME="telegram-bot1"

cd "$BOT_DIR"

echo "Обновление бота..."

# Pull из репозитория
git pull origin main

# Активация venv
source venv/bin/activate

# Обновление зависимостей
pip install -r requirements.txt

# Перезапуск сервиса
sudo systemctl restart "$SERVICE_NAME"

echo "Бот обновлен и перезапущен!"
```

Дайте права на выполнение:

```bash
chmod +x /home/deploy/bot1/update.sh
```

### Использование:

```bash
cd /home/deploy/bot1
./update.sh
```

---

## 📦 Деплой нескольких ботов

### Автоматизация через скрипт

Создайте универсальный скрипт `deployment/scripts/deploy_bot.sh`:

```bash
#!/bin/bash

###############################################################################
# Deploy Telegram Bot Script
# 
# Использование:
#   ./deploy_bot.sh BOT_NAME REPO_URL
#   Пример: ./deploy_bot.sh mybot https://github.com/user/bot.git
###############################################################################

set -e

BOT_NAME=$1
REPO_URL=$2

if [ -z "$BOT_NAME" ] || [ -z "$REPO_URL" ]; then
    echo "Использование: ./deploy_bot.sh BOT_NAME REPO_URL"
    exit 1
fi

BOT_DIR="/home/deploy/$BOT_NAME"

echo "=== Деплой бота: $BOT_NAME ==="

# Клонирование
if [ -d "$BOT_DIR" ]; then
    echo "Директория $BOT_DIR уже существует!"
    exit 1
fi

git clone "$REPO_URL" "$BOT_DIR"
cd "$BOT_DIR"

# Виртуальное окружение
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# .env файл
if [ ! -f ".env" ]; then
    echo "Создайте .env файл с токеном бота!"
    echo "nano $BOT_DIR/.env"
fi

# Systemd сервис
SERVICE_FILE="/etc/systemd/system/telegram-$BOT_NAME.service"

sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Telegram Bot - $BOT_NAME
After=network.target

[Service]
Type=simple
User=deploy
Group=deploy
WorkingDirectory=$BOT_DIR
Environment="PATH=$BOT_DIR/venv/bin"
EnvironmentFile=$BOT_DIR/.env
ExecStart=$BOT_DIR/venv/bin/python main.py

Restart=always
RestartSec=10

StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "telegram-$BOT_NAME"

echo "✓ Бот $BOT_NAME настроен!"
echo ""
echo "Следующие шаги:"
echo "1. Настроить .env: nano $BOT_DIR/.env"
echo "2. Запустить бота: sudo systemctl start telegram-$BOT_NAME"
echo "3. Проверить статус: sudo systemctl status telegram-$BOT_NAME"
```

---

## 🛠️ Управление ботами

### Создание скрипта управления всеми ботами

```bash
nano /home/deploy/manage_bots.sh
```

Содержимое:

```bash
#!/bin/bash

# Список всех ботов
BOTS=("bot1" "bot2" "bot3")

case "$1" in
    start)
        for bot in "${BOTS[@]}"; do
            echo "Запуск $bot..."
            sudo systemctl start "telegram-$bot"
        done
        ;;
    stop)
        for bot in "${BOTS[@]}"; do
            echo "Остановка $bot..."
            sudo systemctl stop "telegram-$bot"
        done
        ;;
    restart)
        for bot in "${BOTS[@]}"; do
            echo "Перезапуск $bot..."
            sudo systemctl restart "telegram-$bot"
        done
        ;;
    status)
        for bot in "${BOTS[@]}"; do
            echo "=== Статус $bot ==="
            sudo systemctl status "telegram-$bot" --no-pager | head -20
            echo ""
        done
        ;;
    logs)
        if [ -z "$2" ]; then
            echo "Укажите имя бота: $0 logs BOT_NAME"
            exit 1
        fi
        sudo journalctl -u "telegram-$2" -f
        ;;
    *)
        echo "Использование: $0 {start|stop|restart|status|logs BOT_NAME}"
        exit 1
        ;;
esac
```

Дайте права:

```bash
chmod +x /home/deploy/manage_bots.sh
```

### Использование:

```bash
./manage_bots.sh start      # Запустить все боты
./manage_bots.sh stop       # Остановить все боты
./manage_bots.sh restart    # Перезапустить все боты
./manage_bots.sh status     # Статус всех ботов
./manage_bots.sh logs bot1  # Логи конкретного бота
```

---

## 📊 Мониторинг ботов

### Проверка всех запущенных сервисов

```bash
systemctl list-units --type=service --state=running | grep telegram
```

### Логи всех ботов

```bash
sudo journalctl -u "telegram-*" -f
```

### Использование ресурсов

```bash
# Все Python процессы
ps aux | grep python

# Использование памяти ботами
ps aux | grep python | awk '{sum += $4} END {print "Использование памяти: " sum "%"}'
```

---

## 🔐 Безопасность

### Защита токенов

1. **Никогда не коммитьте .env в Git:**

```bash
echo ".env" >> .gitignore
```

2. **Ограничьте права на .env:**

```bash
chmod 600 /home/deploy/bot1/.env
```

3. **Используйте переменные окружения:**

```python
import os
BOT_TOKEN = os.getenv('BOT_TOKEN')
```

### Firewall

Telegram боты не требуют входящих подключений (они сами подключаются к Telegram).

Если используете Webhook:

```bash
# Открыть порт для webhook (например, 8443)
sudo ufw allow 8443/tcp comment 'Telegram Webhook'
```

---

## 🔄 Webhook vs Long Polling

### Long Polling (рекомендуется для VDS)

**Преимущества:**
- Проще в настройке
- Не требует SSL сертификата
- Работает за NAT

**Недостатки:**
- Постоянное подключение к Telegram API
- Немного выше нагрузка на сервер

### Webhook

**Преимущества:**
- Меньше нагрузка на сервер
- Быстрее получение обновлений

**Недостатки:**
- Требует SSL сертификат
- Требует публичный IP и открытый порт

**Настройка webhook (если есть SSL):**

```python
import os
from telegram import Bot

BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_URL = f"https://yourdomain.com:8443/{BOT_TOKEN}"

bot = Bot(BOT_TOKEN)
bot.set_webhook(url=WEBHOOK_URL)
```

---

## 📈 Оптимизация

### Использование одного venv для всех ботов (если зависимости одинаковые)

```bash
# Создать общий venv
python3 -m venv /home/deploy/bots_venv

# Использовать в systemd:
Environment="PATH=/home/deploy/bots_venv/bin"
```

### Логирование в файлы

```bash
# В systemd сервисе:
StandardOutput=file:/home/deploy/logs/bot1.log
StandardError=file:/home/deploy/logs/bot1_error.log
```

### Ротация логов

```bash
sudo nano /etc/logrotate.d/telegram-bots
```

Содержимое:

```
/home/deploy/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

---

## 🆘 Решение проблем

### Бот не запускается

```bash
# Проверить логи
sudo journalctl -u telegram-bot1 -n 100 --no-pager

# Проверить .env файл
cat /home/deploy/bot1/.env

# Запустить вручную для отладки
cd /home/deploy/bot1
source venv/bin/activate
python main.py
```

### Бот постоянно перезапускается

```bash
# Увеличить RestartSec в systemd
sudo nano /etc/systemd/system/telegram-bot1.service
# RestartSec=30

sudo systemctl daemon-reload
sudo systemctl restart telegram-bot1
```

### Конфликт портов (для webhook)

```bash
# Проверить занятые порты
sudo netstat -tulpn | grep :8443

# Изменить порт в настройках бота
```

---

## 📝 Пример структуры бота

### Минимальный бот (main.py):

```python
import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен из переменных окружения
TOKEN = os.getenv('BOT_TOKEN')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Привет! Я бот.')

async def main():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    
    # Long Polling
    await application.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
```

### requirements.txt:

```
python-telegram-bot>=20.0
python-dotenv>=1.0.0
```

---

## ✅ Чек-лист деплоя

- [ ] Клонирован репозиторий бота
- [ ] Создано виртуальное окружение
- [ ] Установлены зависимости
- [ ] Создан .env файл с токеном
- [ ] Создан systemd сервис
- [ ] Сервис включен и запущен
- [ ] Проверены логи
- [ ] Бот отвечает на команды
- [ ] Настроен скрипт обновления

---

**Готово!** Ваш Telegram бот развернут и работает 24/7 🚀

