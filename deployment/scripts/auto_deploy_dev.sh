#!/bin/bash

###############################################################################
# Auto Deploy Development Script для Quick Score Tournaments
# Автоматический деплой при изменениях в ветке dev
# 
# Использование:
#   Этот скрипт запускается через cron каждые 5 минут
#   Проверяет наличие изменений в ветке dev и запускает деплой
#
# Настройка cron:
#   */5 * * * * /home/deploy/quick-score-dev/deployment/scripts/auto_deploy_dev.sh >> /home/deploy/logs/auto_deploy_dev.log 2>&1
###############################################################################

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Функции для логирования
log_info() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] [INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] [WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR]${NC} $1"
}

# Переменные
APP_DIR="/home/deploy/quick-score-dev"
BRANCH="dev"
DEPLOY_SCRIPT="$APP_DIR/deployment/scripts/deploy_dev.sh"
LOCK_FILE="/tmp/auto_deploy_dev.lock"

# Проверка блокировки (предотвращение параллельного запуска)
if [ -f "$LOCK_FILE" ]; then
    PID=$(cat "$LOCK_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        log_warn "Деплой уже выполняется (PID: $PID), пропускаем"
        exit 0
    else
        log_warn "Удаляем устаревший lock файл"
        rm -f "$LOCK_FILE"
    fi
fi

# Создаём lock файл
echo $$ > "$LOCK_FILE"
trap "rm -f $LOCK_FILE" EXIT

# Проверка директории
if [ ! -d "$APP_DIR" ]; then
    log_error "Директория $APP_DIR не найдена!"
    exit 1
fi

cd "$APP_DIR"

log_info "=== Проверка изменений в ветке $BRANCH ==="

# Обновляем информацию о ветках
git fetch origin "$BRANCH" > /dev/null 2>&1 || {
    log_error "Не удалось получить информацию о ветке $BRANCH"
    exit 1
}

# Получаем текущий и удалённый коммит
CURRENT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "")
REMOTE_COMMIT=$(git rev-parse "origin/$BRANCH" 2>/dev/null || echo "")

# Проверяем, на какой ветке мы находимся
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")

# Если мы не на ветке dev, переключаемся
if [ "$CURRENT_BRANCH" != "$BRANCH" ]; then
    log_info "Переключение на ветку $BRANCH..."
    git checkout "$BRANCH" > /dev/null 2>&1 || {
        log_error "Не удалось переключиться на ветку $BRANCH"
        exit 1
    }
    CURRENT_COMMIT=$(git rev-parse HEAD)
fi

# Проверяем наличие изменений
if [ -z "$CURRENT_COMMIT" ] || [ -z "$REMOTE_COMMIT" ]; then
    log_warn "Не удалось определить коммиты, пропускаем проверку"
    exit 0
fi

if [ "$CURRENT_COMMIT" = "$REMOTE_COMMIT" ]; then
    log_info "Изменений нет (коммит: ${CURRENT_COMMIT:0:7})"
    exit 0
fi

log_info "Обнаружены изменения: ${CURRENT_COMMIT:0:7} → ${REMOTE_COMMIT:0:7}"
log_info "Запуск деплоя..."

# Запускаем скрипт деплоя
if [ -f "$DEPLOY_SCRIPT" ]; then
    bash "$DEPLOY_SCRIPT"
    log_info "✓ Деплой завершён"
else
    log_error "Скрипт деплоя не найден: $DEPLOY_SCRIPT"
    exit 1
fi

