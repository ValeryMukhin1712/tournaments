#!/bin/bash

###############################################################################
# Обновление Development окружения для отслеживания ветки dev
# 
# Использование:
#   ./update_dev_to_track_dev_branch.sh
#
# Требования:
#   - Запускать от пользователя deploy на сервере
#   - Находиться в директории /home/deploy/quick-score-dev
###############################################################################

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Функции для логирования
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Переменные
APP_DIR="/home/deploy/quick-score-dev"

# Проверка, что запущено не от root
if [[ $EUID -eq 0 ]]; then
   log_error "Не запускайте этот скрипт от root! Используйте пользователя deploy"
   exit 1
fi

# Проверка директории
if [ ! -d "$APP_DIR" ]; then
    log_error "Директория $APP_DIR не найдена!"
    exit 1
fi

cd "$APP_DIR"

log_info "=== Настройка Development окружения для отслеживания ветки dev ==="

# Проверка текущей ветки
CURRENT_BRANCH=$(git branch --show-current)
log_info "Текущая ветка: $CURRENT_BRANCH"

# Получение всех веток из GitHub
log_info "Получение веток из GitHub..."
git fetch origin

# Проверка существования ветки dev на GitHub
if git ls-remote --heads origin dev | grep -q dev; then
    log_info "✓ Ветка dev найдена на GitHub"
else
    log_error "✗ Ветка dev не найдена на GitHub!"
    log_error "Создайте ветку dev на GitHub или локально и запушьте её"
    exit 1
fi

# Переключение на ветку dev
log_info "Переключение на ветку dev..."
if git checkout dev 2>/dev/null; then
    log_info "✓ Переключено на ветку dev"
else
    log_info "Создание локальной ветки dev..."
    git checkout -b dev origin/dev
    log_info "✓ Локальная ветка dev создана"
fi

# Настройка отслеживания удалённой ветки
log_info "Настройка отслеживания удалённой ветки dev..."
git branch --set-upstream-to=origin/dev dev
log_info "✓ Ветка dev настроена для отслеживания origin/dev"

# Обновление кода
log_info "Обновление кода из ветки dev..."
git pull origin dev
log_info "✓ Код обновлён из ветки dev"

# Проверка скрипта деплоя
if [ -f "deployment/scripts/deploy_dev.sh" ]; then
    # Проверка, что скрипт использует ветку dev
    if grep -q 'BRANCH="dev"' deployment/scripts/deploy_dev.sh; then
        log_info "✓ Скрипт deploy_dev.sh настроен на ветку dev"
    else
        log_warn "⚠ Скрипт deploy_dev.sh не использует ветку dev"
        log_warn "Обновите BRANCH в deployment/scripts/deploy_dev.sh"
    fi
else
    log_warn "⚠ Скрипт deploy_dev.sh не найден"
fi

log_info "=== Настройка завершена! ==="
echo ""
log_info "Текущая конфигурация:"
echo "  Директория: $APP_DIR"
echo "  Ветка: $(git branch --show-current)"
echo "  Отслеживает: $(git rev-parse --abbrev-ref --symbolic-full-name @{u})"
echo ""
log_info "Для автоматического деплоя настройте webhook:"
echo "  1. Запустите: ./deployment/scripts/setup_dev_webhook.sh"
echo "  2. Настройте webhook в GitHub Settings → Webhooks"
echo ""

