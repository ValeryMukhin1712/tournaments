#!/bin/bash

###############################################################################
# Setup Development Environment Script
# Настройка dev версии приложения на порту 5001
# 
# Использование:
#   ./setup_dev_environment.sh
#
# Требования:
#   - Production версия уже настроена
#   - Запускать от пользователя deploy
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
PROD_DIR="/home/deploy/quick-score"
DEV_DIR="/home/deploy/quick-score-dev"
REPO_URL="https://github.com/ValeryMukhin1712/quick-score.git"
BRANCH="main"

# Проверка, что запущено не от root
if [[ $EUID -eq 0 ]]; then
   log_error "Не запускайте этот скрипт от root! Используйте пользователя deploy"
   exit 1
fi

log_info "=== Настройка Dev окружения Quick Score Tournaments ==="

# Шаг 1: Клонирование репозитория для dev версии
log_info "Шаг 1/6: Клонирование репозитория для dev версии..."

if [ -d "$DEV_DIR" ]; then
    log_warn "Директория $DEV_DIR уже существует. Обновить? (y/N)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        log_info "Обновление существующего репозитория..."
        cd "$DEV_DIR"
        git fetch origin
        git reset --hard origin/$BRANCH
    else
        log_info "Используем существующую директорию"
    fi
else
    git clone "$REPO_URL" "$DEV_DIR"
    cd "$DEV_DIR"
    git checkout "$BRANCH"
    log_info "✓ Репозиторий склонирован"
fi

cd "$DEV_DIR"

# Шаг 2: Создание виртуального окружения
log_info "Шаг 2/6: Создание виртуального окружения..."

if [ ! -d "venv" ]; then
    python3 -m venv venv
    log_info "✓ Виртуальное окружение создано"
else
    log_warn "Виртуальное окружение уже существует"
fi

# Шаг 3: Установка зависимостей
log_info "Шаг 3/6: Установка зависимостей..."

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

log_info "✓ Зависимости установлены"

# Шаг 4: Создание .env файла для dev
log_info "Шаг 4/6: Создание конфигурации для dev..."

if [ ! -f "$DEV_DIR/.env" ]; then
    cat > "$DEV_DIR/.env" << 'EOF'
# Flask Configuration - Development
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=DEV_SECRET_KEY_CHANGE_THIS

# Server Configuration
HOST=127.0.0.1
PORT=5001

# Database
DATABASE_URL=sqlite:///instance/tournament_dev.db

# Security
SESSION_COOKIE_SECURE=False
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax

# Logging
LOG_LEVEL=DEBUG
LOG_FILE=app_dev.log
EOF
    log_warn "⚠️  ВАЖНО: Отредактируйте $DEV_DIR/.env"
    log_warn "⚠️  Особенно измените SECRET_KEY на случайную строку!"
else
    log_warn ".env файл уже существует, пропускаем"
fi

log_info "✓ Конфигурация создана"

# Шаг 5: Инициализация базы данных для dev
log_info "Шаг 5/6: Инициализация базы данных для dev..."

source venv/bin/activate
if [ -f "init_db.py" ]; then
    python init_db.py
    log_info "✓ База данных инициализирована"
else
    log_warn "init_db.py не найден, пропускаем инициализацию БД"
fi

# Шаг 6: Настройка systemd сервиса для dev
log_info "Шаг 6/6: Настройка systemd сервиса для dev..."

sudo cp deployment/systemd/tournaments-dev.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable tournaments-dev
sudo systemctl start tournaments-dev

log_info "✓ Systemd сервис настроен и запущен"

# Финальная проверка
log_info "=== Проверка работы dev окружения ==="
sleep 3

# Проверка статуса systemd
sudo systemctl status tournaments-dev --no-pager

# Проверка порта
if netstat -tuln | grep -q ":5001"; then
    log_info "✓ Dev приложение слушает порт 5001"
else
    log_warn "⚠️  Dev приложение не отвечает на порту 5001"
fi

# Финальная информация
log_info "=== Настройка Dev окружения завершена! ==="
echo ""
log_info "Dev приложение доступно по адресу:"
echo "  http://quickscore.sytes.net/new_dev"
echo "  https://quickscore.sytes.net/new_dev (если настроен SSL)"
echo ""
log_info "Полезные команды:"
echo "  Статус:      sudo systemctl status tournaments-dev"
echo "  Логи:        sudo journalctl -u tournaments-dev -f"
echo "  Перезапуск:  sudo systemctl restart tournaments-dev"
echo "  Остановка:   sudo systemctl stop tournaments-dev"
echo ""
log_info "=== Готово! ==="

