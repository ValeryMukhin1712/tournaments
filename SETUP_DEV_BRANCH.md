# Настройка ветки dev для автоматического деплоя

## 📋 Обзор

Настроена система автоматического деплоя:
- **Production** (`/`) → отслеживает ветку `main` на GitHub
- **Development** (`/new_dev`) → отслеживает ветку `dev` на GitHub

## 🔄 Текущая конфигурация

### Production
- **Ветка**: `main`
- **Директория**: `/home/deploy/quick-score`
- **Скрипт деплоя**: `deployment/scripts/deploy_production.sh`
- **Сервис**: `tournaments`
- **Порт**: 5000

### Development
- **Ветка**: `dev`
- **Директория**: `/home/deploy/quick-score-dev`
- **Скрипт деплоя**: `deployment/scripts/deploy_dev.sh`
- **Сервис**: `tournaments-dev`
- **Порт**: 5001

## 🚀 Использование

### Работа с веткой dev

#### 1. Переключение на ветку dev (локально)

```bash
git checkout dev
```

#### 2. Внесение изменений и коммит

```bash
# Внесите изменения в код
git add .
git commit -m "Описание изменений"
```

#### 3. Пуш в ветку dev

```bash
git push origin dev
```

**Автоматически запустится деплой в Development окружение!**

### Работа с веткой main (production)

#### 1. Переключение на ветку main

```bash
git checkout main
```

#### 2. Внесение изменений и коммит

```bash
# Внесите изменения в код
git add .
git commit -m "Описание изменений"
```

#### 3. Пуш в ветку main

```bash
git push origin main
```

**Автоматически запустится деплой в Production окружение!**

## 🔧 Настройка автоматического деплоя на сервере

### Вариант 1: GitHub Webhook (рекомендуется)

#### На сервере:

```bash
cd /home/deploy/quick-score-dev
chmod +x deployment/scripts/setup_dev_webhook.sh
./deployment/scripts/setup_dev_webhook.sh
```

#### В GitHub:

1. Откройте: https://github.com/ValeryMukhin1712/quick-score/settings/hooks
2. Нажмите **Add webhook**
3. Заполните:
   - **Payload URL**: `http://YOUR_SERVER_IP:9001/webhook`
   - **Content type**: `application/json`
   - **Secret**: `change-me-to-random-secret` (или сгенерируйте новый)
   - **Which events**: `Just the push event`
4. Нажмите **Add webhook**

### Вариант 2: GitHub Actions

Создайте файл `.github/workflows/deploy-dev.yml`:

```yaml
name: Deploy Dev to VDS

on:
  push:
    branches:
      - dev
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Dev Server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: deploy
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /home/deploy/quick-score-dev
            ./deployment/scripts/deploy_dev.sh
```

## 📝 Проверка работы

### Проверка статуса сервисов

```bash
# Production
sudo systemctl status tournaments

# Development
sudo systemctl status tournaments-dev

# Webhook для dev
sudo systemctl status webhook-dev
```

### Проверка логов

```bash
# Production
sudo journalctl -u tournaments -f

# Development
sudo journalctl -u tournaments-dev -f

# Webhook для dev
sudo journalctl -u webhook-dev -f
```

### Ручной запуск деплоя

```bash
# Production
cd /home/deploy/quick-score
./deployment/scripts/deploy_production.sh

# Development
cd /home/deploy/quick-score-dev
./deployment/scripts/deploy_dev.sh
```

## 🔄 Синхронизация веток

### Перенос изменений из dev в main

```bash
# Переключиться на main
git checkout main

# Слить изменения из dev
git merge dev

# Запушить в main (запустится деплой в production)
git push origin main
```

### Перенос изменений из main в dev

```bash
# Переключиться на dev
git checkout dev

# Слить изменения из main
git merge main

# Запушить в dev (запустится деплой в development)
git push origin dev
```

## ⚠️ Важные замечания

1. **Всегда тестируйте изменения в dev перед переносом в main**
2. **Production обновляется только из ветки main**
3. **Development обновляется только из ветки dev**
4. **Не коммитьте напрямую в main без тестирования в dev**

## 🐛 Решение проблем

### Webhook не работает

```bash
# Проверить статус
sudo systemctl status webhook-dev

# Перезапустить
sudo systemctl restart webhook-dev

# Проверить логи
sudo journalctl -u webhook-dev -n 50
```

### Деплой не запускается

```bash
# Проверить, что скрипт имеет права на выполнение
chmod +x /home/deploy/quick-score-dev/deployment/scripts/deploy_dev.sh

# Запустить вручную
cd /home/deploy/quick-score-dev
./deployment/scripts/deploy_dev.sh
```

### Проблемы с git

```bash
# Проверить текущую ветку
cd /home/deploy/quick-score-dev
git branch

# Переключиться на ветку dev
git checkout dev

# Обновить из GitHub
git fetch origin
git pull origin dev
```

