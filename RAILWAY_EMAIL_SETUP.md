# Настройка Email на Railway

## Проблема
Railway блокирует исходящие SMTP соединения по соображениям безопасности. Ошибка `[Errno 101] Network is unreachable` означает, что приложение не может подключиться к SMTP серверу Gmail.

## Решение

### 1. Настройка переменных окружения на Railway

В панели управления Railway нужно добавить следующие переменные окружения:

```
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=tournaments.master@gmail.com
MAIL_PASSWORD=jqjahujrmrnyzfbo
MAIL_DEFAULT_SENDER=tournaments.master@gmail.com
MAIL_USE_TLS=true
```

### 2. Альтернативное решение для Railway

Поскольку Railway блокирует SMTP, приложение автоматически переключается на fallback режим:

- Токены сохраняются в файл `tokens.txt`
- Данные логируются для ручной отправки
- Можно настроить webhook для автоматической отправки

### 3. Как добавить переменные на Railway

1. Откройте проект на Railway
2. Перейдите в раздел "Variables" (Переменные)
3. Добавьте каждую переменную:
   - Нажмите "New Variable"
   - Введите имя переменной (например, `MAIL_USERNAME`)
   - Введите значение переменной (например, `tournaments.master@gmail.com`)
   - Нажмите "Add"

### 4. Настройка webhook для автоматической отправки (опционально)

Для автоматической отправки email через внешний сервис добавьте переменную:

```
EMAIL_WEBHOOK_URL=https://your-webhook-service.com/send-email
```

Webhook должен принимать POST запрос с JSON:
```json
{
  "to": "user@example.com",
  "subject": "Ваш токен для создания турниров",
  "body": "Текст письма...",
  "from": "tournaments.master@gmail.com"
}
```

### 5. Проверка настроек

После добавления переменных можно проверить настройки через API:

```
GET https://your-app.railway.app/api/debug/email-config
```

Этот endpoint покажет:
- Переменные окружения Railway
- Настройки Flask
- Статус конфигурации

### 6. Тестирование отправки email

Для тестирования отправки email используйте:

```
POST https://your-app.railway.app/api/debug/test-email
Content-Type: application/json

{
  "email": "test@example.com"
}
```

### 7. Логи Railway

Проверьте логи Railway после настройки переменных. В логах должно появиться:

```
Email настройки: server=smtp.gmail.com, port=587, username=tournaments.master@gmail.com
Все переменные окружения MAIL_*: [('MAIL_SERVER', 'smtp.gmail.com'), ('MAIL_USERNAME', 'tournaments.master@gmail.com'), ...]
RAILWAY_ENVIRONMENT: production
```

## Важные моменты

1. **Безопасность**: Пароль email (`MAIL_PASSWORD`) должен быть паролем приложения Gmail, а не обычным паролем аккаунта.

2. **Перезапуск**: После добавления переменных Railway автоматически перезапустит приложение.

3. **Проверка**: Убедитесь, что все переменные добавлены правильно и без лишних пробелов.

## Диагностика

Если email все еще не работает:

1. Проверьте логи Railway на наличие ошибок SMTP
2. Убедитесь, что пароль приложения Gmail действителен
3. Проверьте, что аккаунт Gmail имеет включенную двухфакторную аутентификацию
4. Убедитесь, что пароль приложения создан правильно

## Fallback режим на Railway

Если SMTP заблокирован (ошибка `Network is unreachable`), приложение автоматически переключается в fallback режим:

1. **Токены сохраняются в файл** `tokens.txt` с пометкой `RAILWAY FALLBACK`
2. **Данные логируются** для ручной отправки
3. **Пользователь видит сообщение** "Токен отправлен на ваш email!" (но письмо не приходит)
4. **Администратор может** вручную отправить токены из файла `tokens.txt`

### Ручная отправка токенов

1. Проверьте файл `tokens.txt` на Railway
2. Найдите записи с пометкой `RAILWAY FALLBACK`
3. Отправьте токены вручную через Gmail или другой email сервис

### Альтернативные решения

1. **Используйте внешний email сервис** (SendGrid, Mailgun, etc.)
2. **Настройте webhook** для автоматической отправки
3. **Разверните на другой платформе** (Heroku, DigitalOcean, etc.)
