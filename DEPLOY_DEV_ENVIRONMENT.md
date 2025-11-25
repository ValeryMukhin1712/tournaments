# 🚀 Настройка Dev окружения на сервере

Этот документ описывает, как настроить dev версию приложения на том же сервере, что и production версия.

## Архитектура

- **Production**: `https://quickscore.sytes.net/` → порт 5000
- **Development**: `https://quickscore.sytes.net/new_dev` → порт 5001

## Предварительные требования

1. Production версия уже настроена и работает
2. У вас есть доступ к серверу по SSH
3. Установлены: Nginx, Python 3, Git

## Шаг 1: Настройка Dev окружения

### На сервере выполните:

```bash
# Подключитесь к серверу
ssh deploy@ваш_сервер

# Перейдите в директорию проекта
cd ~

# Скопируйте скрипт настройки на сервер (с локальной машины)
# Или создайте его вручную на сервере
nano ~/setup_dev_environment.sh
# Вставьте содержимое из deployment/scripts/setup_dev_environment.sh

# Сделайте скрипт исполняемым
chmod +x ~/setup_dev_environment.sh

# Запустите скрипт
./setup_dev_environment.sh
```

Скрипт автоматически:
- Создаст директорию `/home/deploy/quick-score-dev`
- Склонирует репозиторий
- Создаст виртуальное окружение
- Установит зависимости
- Создаст отдельную базу данных для dev
- Настроит systemd сервис на порту 5001

## Шаг 2: Настройка Nginx

### Обновите конфигурацию Nginx:

```bash
# На сервере
sudo nano /etc/nginx/sites-available/tournaments.conf
```

Или скопируйте новую конфигурацию:

```bash
# С локальной машины
scp deployment/nginx/tournaments_with_dev.conf deploy@ваш_сервер:~/tournaments_with_dev.conf

# На сервере
sudo cp ~/tournaments_with_dev.conf /etc/nginx/sites-available/tournaments.conf
```

### Проверьте конфигурацию:

```bash
sudo nginx -t
```

### Перезапустите Nginx:

```bash
sudo systemctl restart nginx
```

## Шаг 3: Проверка работы

### Проверьте статус сервисов:

```bash
# Production
sudo systemctl status tournaments

# Development
sudo systemctl status tournaments-dev
```

### Проверьте порты:

```bash
netstat -tuln | grep -E "5000|5001"
```

Должны быть:
- `127.0.0.1:5000` - Production
- `127.0.0.1:5001` - Development

### Проверьте в браузере:

- Production: `https://quickscore.sytes.net/`
- Development: `https://quickscore.sytes.net/new_dev`

## Обновление Dev версии

### Способ 1: Автоматический скрипт (рекомендуется)

Скопируйте скрипт на сервер и используйте его:

```bash
# С локальной машины
scp deployment/scripts/deploy_dev.sh deploy@89.19.44.212:~/deploy_dev.sh

# На сервере
chmod +x ~/deploy_dev.sh
cd ~/quick-score-dev
~/deploy_dev.sh
```

Или выполните вручную:

```bash
cd ~/quick-score-dev
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart tournaments-dev
```

### Способ 2: Ручное обновление

```bash
cd ~/quick-score-dev
git fetch origin
git reset --hard origin/main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart tournaments-dev
```

## Обновление Production версии

### Способ 1: Автоматический скрипт (рекомендуется)

Скопируйте скрипт на сервер и используйте его:

```bash
# С локальной машины
scp deployment/scripts/deploy_production.sh deploy@89.19.44.212:~/deploy_production.sh

# На сервере
chmod +x ~/deploy_production.sh
cd ~/quick-score
~/deploy_production.sh
```

Или выполните вручную:

```bash
cd ~/quick-score
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart tournaments
```

### Способ 2: Ручное обновление

```bash
cd ~/quick-score
git fetch origin
git reset --hard origin/main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart tournaments
```

## 📖 Подробная документация по деплою

Для подробной информации о процедурах деплоя см. файл `DEPLOYMENT_PROCEDURE.md`

## Важные замечания

### Базы данных

- **Production**: `/home/deploy/quick-score/instance/tournament.db`
- **Development**: `/home/deploy/quick-score-dev/instance/tournament_dev.db`

Базы данных полностью независимы.

### Конфигурация

- **Production**: `/home/deploy/quick-score/.env`
- **Development**: `/home/deploy/quick-score-dev/.env`

Убедитесь, что в dev версии:
- `FLASK_ENV=development`
- `FLASK_DEBUG=True`
- `PORT=5001`
- Используется отдельная база данных

### Логи

```bash
# Production логи
sudo journalctl -u tournaments -f

# Development логи
sudo journalctl -u tournaments-dev -f
```

## Решение проблем

### Dev версия не запускается

```bash
# Проверьте логи
sudo journalctl -u tournaments-dev -n 50 --no-pager

# Проверьте порт
netstat -tuln | grep 5001

# Запустите вручную для диагностики
cd ~/quick-score-dev
source venv/bin/activate
gunicorn --bind 127.0.0.1:5001 app:app
```

### Nginx возвращает 502 Bad Gateway

1. Проверьте, что dev сервис запущен:
   ```bash
   sudo systemctl status tournaments-dev
   ```

2. Проверьте, что порт 5001 слушается:
   ```bash
   netstat -tuln | grep 5001
   ```

3. Проверьте логи Nginx:
   ```bash
   sudo tail -f /var/log/nginx/tournaments_error.log
   ```

### Статические файлы не загружаются в /new_dev

Проверьте, что путь к статическим файлам правильный в Nginx конфигурации:
```nginx
location /new_dev/static {
    alias /home/deploy/quick-score-dev/static;
    ...
}
```

## Полезные команды

```bash
# Перезапуск dev версии
sudo systemctl restart tournaments-dev

# Остановка dev версии
sudo systemctl stop tournaments-dev

# Просмотр логов в реальном времени
sudo journalctl -u tournaments-dev -f

# Проверка конфигурации Nginx
sudo nginx -t

# Перезагрузка Nginx
sudo systemctl reload nginx
```

## Откат изменений

Если нужно удалить dev окружение:

```bash
# Остановить сервис
sudo systemctl stop tournaments-dev
sudo systemctl disable tournaments-dev

# Удалить сервис
sudo rm /etc/systemd/system/tournaments-dev.service
sudo systemctl daemon-reload

# Удалить директорию (опционально)
rm -rf ~/quick-score-dev

# Восстановить старую конфигурацию Nginx
sudo cp /etc/nginx/sites-available/tournaments.conf.backup /etc/nginx/sites-available/tournaments.conf
sudo nginx -t
sudo systemctl restart nginx
```

---

**Важно**: 
- Dev версия использует отдельную базу данных, поэтому изменения в dev не влияют на production
- Всегда тестируйте изменения в dev перед деплоем в production
- Не используйте dev версию для реальных данных

