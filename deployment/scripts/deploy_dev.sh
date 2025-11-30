#!/bin/bash

###############################################################################
# Deploy Development Script для Quick Score Tournaments
# Автоматический деплой в Development окружение
# 
# Использование:
#   ./deploy_dev.sh
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
BRANCH="dev"

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

log_info "=== Деплой Development окружения ==="
log_info "Директория: $APP_DIR"

# Шаг 1: Резервное копирование БД (опционально)
log_info "Шаг 1/5: Резервное копирование базы данных..."
if [ -f "instance/tournament_dev.db" ]; then
    BACKUP_DIR="$HOME/backups"
    mkdir -p "$BACKUP_DIR"
    BACKUP_FILE="$BACKUP_DIR/tournament_dev_$(date +%Y%m%d_%H%M%S).db"
    cp "instance/tournament_dev.db" "$BACKUP_FILE"
    log_info "✓ Резервная копия создана: $BACKUP_FILE"
else
    log_warn "База данных не найдена, пропускаем резервное копирование"
fi

# Шаг 2: Обновление кода
log_info "Шаг 2/5: Обновление кода из репозитория..."
git fetch origin
CURRENT_COMMIT=$(git rev-parse HEAD)
git pull origin "$BRANCH"
NEW_COMMIT=$(git rev-parse HEAD)

if [ "$CURRENT_COMMIT" != "$NEW_COMMIT" ]; then
    log_info "✓ Код обновлён: $CURRENT_COMMIT → $NEW_COMMIT"
else
    log_info "✓ Код уже актуален"
fi

# Шаг 3: Активация виртуального окружения
log_info "Шаг 3/5: Активация виртуального окружения..."
if [ ! -d "venv" ]; then
    log_error "Виртуальное окружение не найдено!"
    exit 1
fi
source venv/bin/activate

# Шаг 4: Обновление зависимостей
log_info "Шаг 4/5: Обновление зависимостей..."
pip install --upgrade pip
pip install -r requirements.txt
log_info "✓ Зависимости обновлены"

# Шаг 5: Перезапуск сервиса
log_info "Шаг 5/5: Перезапуск сервиса..."
sudo systemctl restart tournaments-dev
sleep 3

# Проверка статуса
if sudo systemctl is-active --quiet tournaments-dev; then
    log_info "✓ Сервис успешно перезапущен"
else
    log_error "✗ Сервис не запустился!"
    log_error "Проверьте логи: sudo journalctl -u tournaments-dev -n 50"
    exit 1
fi

# Финальная проверка
log_info "=== Проверка работы Development ==="
sleep 2

# Проверка статуса
if sudo systemctl is-active --quiet tournaments-dev; then
    log_info "✓ Сервис работает"
else
    log_error "✗ Сервис не работает!"
    exit 1
fi

# Проверка порта
if ss -tuln | grep -q ":5001"; then
    log_info "✓ Порт 5001 слушается"
else
    log_warn "⚠ Порт 5001 не слушается"
fi

# Финальная информация
log_info "=== Деплой Development завершён! ==="
echo ""
log_info "Development доступен по адресу:"
echo "  https://quickscore.sytes.net/new_dev"
echo ""
log_info "Полезные команды:"
echo "  Статус:      sudo systemctl status tournaments-dev"
echo "  Логи:        sudo journalctl -u tournaments-dev -f"
echo "  Перезапуск:  sudo systemctl restart tournaments-dev"
echo ""

