#!/bin/bash

###############################################################################
# Deploy Application Script для Quick Score Tournaments
# Автоматический деплой Flask приложения
# 
# Использование:
#   ./deploy_app.sh                # Первый деплой
#   ./deploy_app.sh --update       # Обновление существующего
#
# Требования:
#   - setup_server.sh уже выполнен
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
APP_DIR="/home/deploy/app"
REPO_URL="https://github.com/ValeryMukhin1712/quick-score.git"
BRANCH="main"
UPDATE_MODE=false

# Проверка аргументов
if [[ "$1" == "--update" ]]; then
    UPDATE_MODE=true
fi

# Проверка, что запущено не от root
if [[ $EUID -eq 0 ]]; then
   log_error "Не запускайте этот скрипт от root! Используйте пользователя deploy"
   exit 1
fi

log_info "=== Начало деплоя Quick Score Tournaments ==="

if [ "$UPDATE_MODE" = true ]; then
    log_info "Режим: ОБНОВЛЕНИЕ существующего приложения"
else
    log_info "Режим: ПЕРВОНАЧАЛЬНЫЙ ДЕПЛОЙ"
fi

# Функция для создания .env файла
create_env_file() {
    log_info "Создание .env файла..."
    
    cat > "$APP_DIR/.env" << 'EOF'
# Flask Configuration
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=CHANGE_THIS_TO_RANDOM_SECRET_KEY

# Server Configuration
HOST=0.0.0.0
PORT=5000

# Database
DATABASE_URL=sqlite:///instance/tournament.db

# Security
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax

# Logging
LOG_LEVEL=INFO
LOG_FILE=app.log
EOF

    log_warn "⚠️  ВАЖНО: Отредактируйте /home/deploy/app/.env"
    log_warn "⚠️  Особенно измените SECRET_KEY на случайную строку!"
}

# Функция для установки зависимостей
install_dependencies() {
    log_info "Установка Python зависимостей..."
    
    cd "$APP_DIR"
    
    # Активация виртуального окружения
    source venv/bin/activate
    
    # Обновление pip
    pip install --upgrade pip
    
    # Установка зависимостей
    pip install -r requirements.txt
    
    # Установка Gunicorn
    pip install gunicorn
    
    log_info "✓ Зависимости установлены"
}

# Обновление приложения
if [ "$UPDATE_MODE" = true ]; then
    log_info "Шаг 1/3: Обновление кода из репозитория..."
    
    cd "$APP_DIR"
    
    # Создание бэкапа базы данных
    if [ -f "instance/tournament.db" ]; then
        log_info "Создание бэкапа базы данных..."
        BACKUP_DIR="/home/deploy/backups"
        mkdir -p "$BACKUP_DIR"
        BACKUP_FILE="$BACKUP_DIR/tournament_$(date +%Y%m%d_%H%M%S).db"
        cp instance/tournament.db "$BACKUP_FILE"
        log_info "✓ Бэкап создан: $BACKUP_FILE"
    fi
    
    # Обновление кода
    git fetch origin
    git reset --hard origin/$BRANCH
    
    log_info "✓ Код обновлен"
    
    # Установка/обновление зависимостей
    install_dependencies
    
    # Перезапуск сервиса
    log_info "Шаг 2/3: Перезапуск приложения..."
    sudo systemctl restart tournaments
    
    log_info "Шаг 3/3: Проверка статуса..."
    sleep 3
    sudo systemctl status tournaments --no-pager
    
    log_info "=== Обновление завершено ==="
    exit 0
fi

# Первоначальный деплой
log_info "Шаг 1/8: Клонирование репозитория..."

if [ -d "$APP_DIR" ]; then
    log_warn "Директория $APP_DIR уже существует. Удалить? (y/N)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        rm -rf "$APP_DIR"
        log_info "Директория удалена"
    else
        log_error "Деплой отменен"
        exit 1
    fi
fi

git clone "$REPO_URL" "$APP_DIR"
cd "$APP_DIR"
git checkout "$BRANCH"

log_info "✓ Репозиторий склонирован"

# Шаг 2: Создание виртуального окружения
log_info "Шаг 2/8: Создание виртуального окружения..."

python3 -m venv venv

log_info "✓ Виртуальное окружение создано"

# Шаг 3: Установка зависимостей
log_info "Шаг 3/8: Установка зависимостей..."

install_dependencies

# Шаг 4: Создание .env файла
log_info "Шаг 4/8: Создание конфигурации..."

if [ ! -f "$APP_DIR/.env" ]; then
    create_env_file
else
    log_warn ".env файл уже существует, пропускаем"
fi

log_info "✓ Конфигурация создана"

# Шаг 5: Инициализация базы данных
log_info "Шаг 5/8: Инициализация базы данных..."

source venv/bin/activate
python init_db.py

log_info "✓ База данных инициализирована"

# Шаг 6: Настройка Nginx
log_info "Шаг 6/8: Настройка Nginx..."

sudo cp deployment/nginx/tournaments.conf /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/tournaments.conf /etc/nginx/sites-enabled/

# Тест конфигурации Nginx
sudo nginx -t

sudo systemctl restart nginx

log_info "✓ Nginx настроен"

# Шаг 7: Настройка systemd сервиса
log_info "Шаг 7/8: Настройка systemd сервиса..."

sudo cp deployment/systemd/tournaments.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable tournaments
sudo systemctl start tournaments

log_info "✓ Systemd сервис настроен и запущен"

# Шаг 8: Проверка статуса
log_info "Шаг 8/8: Проверка работы приложения..."

sleep 3

# Проверка статуса systemd
sudo systemctl status tournaments --no-pager

# Проверка порта
if netstat -tuln | grep -q ":5000"; then
    log_info "✓ Приложение слушает порт 5000"
else
    log_warn "⚠️  Приложение не отвечает на порту 5000"
fi

# Проверка Nginx
if curl -s -o /dev/null -w "%{http_code}" http://localhost | grep -q "200\|302"; then
    log_info "✓ Nginx работает корректно"
else
    log_warn "⚠️  Nginx вернул ошибку"
fi

# Финальная информация
log_info "=== Деплой завершен успешно! ==="
echo ""
log_info "Приложение доступно по адресу:"
echo "  http://$(hostname -I | awk '{print $1}')"
echo ""
log_info "Полезные команды:"
echo "  Статус:      sudo systemctl status tournaments"
echo "  Логи:        sudo journalctl -u tournaments -f"
echo "  Перезапуск:  sudo systemctl restart tournaments"
echo "  Остановка:   sudo systemctl stop tournaments"
echo ""
log_warn "⚠️  СЛЕДУЮЩИЕ ШАГИ:"
echo ""
echo "1. Отредактируйте .env файл:"
echo "   nano /home/deploy/app/.env"
echo "   Измените SECRET_KEY на случайную строку!"
echo ""
echo "2. Перезапустите приложение:"
echo "   sudo systemctl restart tournaments"
echo ""
echo "3. Для SSL сертификата (если есть домен):"
echo "   sudo certbot --nginx -d yourdomain.com"
echo ""
log_info "=== Готово! ==="

