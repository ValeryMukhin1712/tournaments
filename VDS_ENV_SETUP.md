# Настройка .env файла на VDS для Telegram бота

## Проблема
На VDS сервере отсутствуют переменные окружения для Telegram бота, поэтому используется неправильный бот или возникают ошибки.

## Решение

### 1. Подключитесь к VDS серверу

```bash
ssh deploy@your-server-ip
cd ~/quick-score
```

### 2. Отредактируйте файл .env

```bash
nano .env
```

### 3. Добавьте в конец файла следующие строки:

```bash
# Telegram Bot Configuration (PROD)
# ВАЖНО: Для продакшена используйте PROD переменные
TELEGRAM_BOT_TOKEN_PROD=ваш_токен_бота_QuickScore
TELEGRAM_BOT_USERNAME_PROD=Q_uickScore_bot
```

**Замените:**
- `ваш_токен_бота_QuickScore` - токен вашего бота QuickScore (получите у @BotFather в Telegram)
- `Q_uickScore_bot` - username вашего бота QuickScore (без символа @)

### 4. Сохраните файл

- Нажмите `Ctrl+O` для сохранения
- Нажмите `Enter` для подтверждения
- Нажмите `Ctrl+X` для выхода

### 5. Перезапустите приложение

Если используете systemd:
```bash
sudo systemctl restart your-app-name
```

Или если запускаете вручную:
```bash
# Остановите текущий процесс (Ctrl+C)
# Запустите заново
python app.py
```

### 6. Проверьте логи

```bash
tail -f app.log | grep -i telegram
```

Должны увидеть сообщения:
```
Генерация QR-кода: используется bot_username=Q_uickScore_bot, APP_ENV=не установлен
```

## Пример полного .env файла на VDS

```bash
# Flask Configuration
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=e591c7618e8f4021be4b263d83763d1329ae0a361734b9256fa969df72a8f4d9

# Server Configuration
HOST=0.0.0.0
PORT=5000

# Database
DATABASE_URL=sqlite:///instance/tournament.db

# Security
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax

# Logging
LOG_LEVEL=INFO
LOG_FILE=app.log

# Telegram Bot Configuration (PROD)
# ВАЖНО: Не устанавливайте APP_ENV=dev на продакшене!
TELEGRAM_BOT_TOKEN_PROD=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz-1234567890
TELEGRAM_BOT_USERNAME_PROD=Q_uickScore_bot
```

## Проверка работы

1. Откройте приложение в браузере
2. Подайте заявку на турнир с подключением Telegram
3. Проверьте, что открывается правильный бот (QuickScore, а не devQuickScore)
4. Проверьте логи - должно быть правильное имя бота

## Примечания

- **НЕ** устанавливайте `APP_ENV=dev` на VDS - это переключит на dev бота
- **НЕ** используйте переменные `TELEGRAM_BOT_TOKEN_DEV` и `TELEGRAM_BOT_USERNAME_DEV` на продакшене
- Используйте только `TELEGRAM_BOT_TOKEN_PROD` и `TELEGRAM_BOT_USERNAME_PROD` на VDS

