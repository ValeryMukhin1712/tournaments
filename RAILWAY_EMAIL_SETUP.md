# Настройка Email на Railway

## Проблема
На Railway не настроены переменные окружения для отправки email, поэтому токены генерируются, но письма не отправляются.

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

### 2. Как добавить переменные на Railway

1. Откройте проект на Railway
2. Перейдите в раздел "Variables" (Переменные)
3. Добавьте каждую переменную:
   - Нажмите "New Variable"
   - Введите имя переменной (например, `MAIL_USERNAME`)
   - Введите значение переменной (например, `tournaments.master@gmail.com`)
   - Нажмите "Add"

### 3. Проверка настроек

После добавления переменных можно проверить настройки через API:

```
GET https://your-app.railway.app/api/debug/email-config
```

Этот endpoint покажет:
- Переменные окружения Railway
- Настройки Flask
- Статус конфигурации

### 4. Тестирование отправки email

Для тестирования отправки email используйте:

```
POST https://your-app.railway.app/api/debug/test-email
Content-Type: application/json

{
  "email": "test@example.com"
}
```

### 5. Логи Railway

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
