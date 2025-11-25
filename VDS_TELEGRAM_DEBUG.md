# Диагностика проблем с Telegram на VDS сервере

## Проблема
При отправке формы "Связаться с автором" на VDS сервере возникает ошибка:
```
Ошибка при отправке сообщения. Пожалуйста, попробуйте позже.
```

## Возможные причины и решения

### 1. Проверка логов приложения

Подключитесь к VDS серверу и проверьте логи приложения:

```bash
# Если используете systemd
sudo journalctl -u your-app-name -n 100 --no-pager

# Или если логи в файле
tail -f /path/to/your/app/app.log
tail -f /path/to/your/app/tournament.log
```

Ищите строки с ошибками:
- `Ошибка при отправке в Telegram:`
- `Timeout при отправке сообщения в Telegram`
- `Telegram настройки не заданы`

### 2. Проверка переменных окружения

Проверьте, установлены ли переменные окружения на сервере:

```bash
# Если используете systemd service
sudo systemctl show your-app-name | grep TELEGRAM

# Или проверьте файл окружения
cat /etc/systemd/system/your-app-name.service.d/override.conf
# или
cat /etc/environment
```

**Решение**: Если переменные не установлены, добавьте их:

#### Вариант А: Через systemd (рекомендуется)

Создайте файл с переменными окружения:
```bash
sudo mkdir -p /etc/systemd/system/your-app-name.service.d/
sudo nano /etc/systemd/system/your-app-name.service.d/override.conf
```

Добавьте:
```ini
[Service]
Environment="TELEGRAM_BOT_TOKEN=8395818732:AAHwQKYFV3Fr3LOopRS3nOwvH28lhCBXEfc"
Environment="TELEGRAM_CHAT_ID=7052840972"
```

Перезапустите сервис:
```bash
sudo systemctl daemon-reload
sudo systemctl restart your-app-name
```

#### Вариант Б: Через .env файл

Создайте файл `.env` в директории приложения:
```bash
cd /path/to/your/app
nano .env
```

Добавьте:
```
TELEGRAM_BOT_TOKEN=8395818732:AAHwQKYFV3Fr3LOopRS3nOwvH28lhCBXEfc
TELEGRAM_CHAT_ID=7052840972
```

### 3. Проверка доступа к Telegram API

Проверьте, может ли сервер подключиться к Telegram:

```bash
curl -X POST "https://api.telegram.org/bot8395818732:AAHwQKYFV3Fr3LOopRS3nOwvH28lhCBXEfc/getMe"
```

**Ожидаемый результат**: JSON с информацией о боте
```json
{"ok":true,"result":{"id":...,"is_bot":true,...}}
```

**Если не работает**:
- Проверьте файрвол: `sudo ufw status`
- Проверьте, разрешен ли исходящий HTTPS трафик
- Проверьте DNS: `nslookup api.telegram.org`

### 4. Проверка установки библиотеки requests

Убедитесь, что библиотека `requests` установлена:

```bash
# Активируйте виртуальное окружение
source venv/bin/activate  # или путь к вашему venv

# Проверьте установку
pip show requests

# Если не установлена
pip install requests
```

### 5. Тест отправки сообщения вручную

Создайте тестовый скрипт для проверки:

```bash
cd /path/to/your/app
nano test_telegram.py
```

Содержимое:
```python
import requests

BOT_TOKEN = "8395818732:AAHwQKYFV3Fr3LOopRS3nOwvH28lhCBXEfc"
CHAT_ID = "7052840972"

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
payload = {
    'chat_id': CHAT_ID,
    'text': 'Тестовое сообщение с VDS сервера'
}

response = requests.post(url, data=payload, timeout=10)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
```

Запустите:
```bash
python test_telegram.py
```

### 6. Проверка настроек Nginx (если используется)

Если используете Nginx как reverse proxy, убедитесь, что он не блокирует исходящие запросы.
Nginx не должен блокировать исходящие запросы от Flask приложения.

### 7. Проверка конфигурации config.py

Убедитесь, что в `config.py` есть значения по умолчанию:

```python
# Настройки Telegram Bot для обратной связи
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN') or '8395818732:AAHwQKYFV3Fr3LOopRS3nOwvH28lhCBXEfc'
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID') or '7052840972'
```

## Общая последовательность диагностики

1. ✅ Проверьте логи приложения
2. ✅ Проверьте доступ к Telegram API с сервера (curl)
3. ✅ Запустите тестовый скрипт
4. ✅ Проверьте переменные окружения
5. ✅ Перезапустите приложение
6. ✅ Проверьте работу формы

## Частые ошибки

### Ошибка: "chat not found"
**Причина**: Бот не может отправить сообщение, потому что пользователь не начал диалог с ботом.
**Решение**: Откройте Telegram, найдите вашего бота и отправьте ему `/start`

### Ошибка: "Timeout"
**Причина**: Сервер не может подключиться к Telegram API (файрвол, сеть)
**Решение**: Проверьте файрвол и сетевые настройки

### Ошибка: "Telegram настройки не заданы"
**Причина**: Переменные окружения пустые или None
**Решение**: Установите переменные окружения или проверьте значения по умолчанию в config.py

## После исправления

После внесения изменений:

```bash
# Перезапустите приложение
sudo systemctl restart your-app-name

# Проверьте статус
sudo systemctl status your-app-name

# Проверьте логи
sudo journalctl -u your-app-name -f
```

## Обновление кода на сервере

Если внесли изменения в код:

```bash
cd /path/to/your/app
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart your-app-name
```
















