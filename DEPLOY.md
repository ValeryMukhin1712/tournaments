# 🚀 Деплой на Railway

## Подготовка к деплою

### 1. Создание аккаунта Railway
1. Перейдите на [railway.app](https://railway.app)
2. Войдите через GitHub
3. Подключите ваш репозиторий

### 2. Настройка проекта
1. Создайте новый проект в Railway
2. Добавьте PostgreSQL базу данных
3. Подключите GitHub репозиторий

### 3. Переменные окружения
Railway автоматически установит:
- `DATABASE_URL` - для PostgreSQL
- `PORT` - порт приложения

Дополнительно установите:
- `FLASK_ENV=production`
- `SECRET_KEY` - сгенерируйте новый ключ

### 4. Деплой
1. Railway автоматически обнаружит `Procfile`
2. Установит зависимости из `requirements.txt`
3. Запустит приложение с `gunicorn`

## Локальная разработка

### Установка зависимостей
```bash
pip install -r requirements.txt
```

### Запуск в режиме разработки
```bash
python app.py
```

### Запуск с PostgreSQL (для тестирования)
```bash
export FLASK_ENV=production
export DATABASE_URL=postgresql://user:password@localhost:5432/tournament
python app.py
```

## Структура проекта

```
├── app.py                 # Главный файл приложения
├── config.py              # Конфигурация для разных окружений
├── requirements.txt       # Python зависимости
├── Procfile              # Команда запуска для Railway
├── railway.json          # Настройки Railway
├── migrate_to_postgresql.py # Скрипт миграции данных
├── models/               # Модели базы данных
├── routes/               # Маршруты приложения
└── templates/            # HTML шаблоны
```

## Мониторинг

- Логи доступны в панели Railway
- Метрики производительности встроены
- Автоматический перезапуск при сбоях

## Резервное копирование

Railway автоматически создает бэкапы PostgreSQL базы данных.
