#!/bin/bash
# Скрипт для проверки и запуска приложения на VDS

echo "=== Проверка и запуск приложения ==="
echo ""

# Цвета
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

APP_DIR="/home/deploy/quick-score"
SERVICE_NAME="tournaments"

# Функция для вывода информации
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# 1. Проверка статуса сервиса
echo "1️⃣  Проверка статуса сервиса '$SERVICE_NAME':"
echo ""

if systemctl is-active --quiet $SERVICE_NAME 2>/dev/null || sudo systemctl is-active --quiet $SERVICE_NAME 2>/dev/null; then
    success "Сервис запущен"
    if [ "$EUID" -eq 0 ]; then
        systemctl status $SERVICE_NAME --no-pager -l | head -15
    else
        sudo systemctl status $SERVICE_NAME --no-pager -l | head -15
    fi
else
    error "Сервис НЕ запущен"
    if [ "$EUID" -eq 0 ]; then
        systemctl status $SERVICE_NAME --no-pager -l | head -15
    else
        sudo systemctl status $SERVICE_NAME --no-pager -l | head -15
    fi
    echo ""
    info "Попытка запуска сервиса..."
    if [ "$EUID" -eq 0 ]; then
        systemctl start $SERVICE_NAME
    else
        sudo systemctl start $SERVICE_NAME
    fi
    sleep 2
    if systemctl is-active --quiet $SERVICE_NAME 2>/dev/null || sudo systemctl is-active --quiet $SERVICE_NAME 2>/dev/null; then
        success "Сервис успешно запущен"
    else
        error "Не удалось запустить сервис. Проверьте логи ниже."
    fi
fi
echo ""

# 2. Проверка порта 5000
echo "2️⃣  Проверка порта 5000:"
if command -v netstat &> /dev/null; then
    if netstat -tuln 2>/dev/null | grep -q ":5000"; then
        success "Порт 5000 занят (приложение слушает)"
        netstat -tuln 2>/dev/null | grep ":5000"
    else
        warning "Порт 5000 свободен (приложение не слушает)"
    fi
elif command -v ss &> /dev/null; then
    if ss -tuln 2>/dev/null | grep -q ":5000"; then
        success "Порт 5000 занят (приложение слушает)"
        ss -tuln 2>/dev/null | grep ":5000"
    else
        warning "Порт 5000 свободен (приложение не слушает)"
    fi
else
    warning "Не удалось проверить порт (netstat/ss не найдены)"
fi
echo ""

# 3. Проверка HTTP доступности
echo "3️⃣  Проверка HTTP доступности:"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 http://localhost:5000 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "301" ]; then
    success "Приложение отвечает (HTTP $HTTP_CODE)"
else
    error "Приложение НЕ отвечает (HTTP $HTTP_CODE)"
    if [ "$HTTP_CODE" = "000" ]; then
        warning "Не удалось подключиться. Возможно, приложение не запущено."
    fi
fi
echo ""

# 4. Проверка директории приложения
echo "4️⃣  Проверка директории приложения:"
if [ -d "$APP_DIR" ]; then
    success "Директория найдена: $APP_DIR"
    cd "$APP_DIR" 2>/dev/null || {
        error "Не удалось перейти в директорию"
        exit 1
    }
else
    error "Директория не найдена: $APP_DIR"
    warning "Проверьте путь к приложению"
    exit 1
fi
echo ""

# 5. Проверка процесса Python/Gunicorn
echo "5️⃣  Проверка процессов приложения:"
PYTHON_PROCS=$(ps aux | grep -E "(gunicorn|python.*app.py)" | grep -v grep | wc -l)
if [ "$PYTHON_PROCS" -gt 0 ]; then
    success "Найдено процессов приложения: $PYTHON_PROCS"
    ps aux | grep -E "(gunicorn|python.*app.py)" | grep -v grep | head -5
else
    warning "Процессы приложения не найдены"
fi
echo ""

# 6. Проверка последних логов
echo "6️⃣  Последние 20 строк логов сервиса:"
if [ "$EUID" -eq 0 ]; then
    journalctl -u $SERVICE_NAME -n 20 --no-pager 2>/dev/null || echo "Не удалось получить логи"
else
    sudo journalctl -u $SERVICE_NAME -n 20 --no-pager 2>/dev/null || echo "Не удалось получить логи"
fi
echo ""

# 7. Попытка запуска вручную (если сервис не работает)
if ! systemctl is-active --quiet $SERVICE_NAME 2>/dev/null && ! sudo systemctl is-active --quiet $SERVICE_NAME 2>/dev/null; then
    echo "7️⃣  Попытка запуска приложения вручную:"
    echo ""
    
    # Проверка виртуального окружения
    if [ -f "$APP_DIR/venv/bin/activate" ]; then
        info "Активация виртуального окружения..."
        source "$APP_DIR/venv/bin/activate"
        
        # Проверка зависимостей
        info "Проверка Python и зависимостей..."
        if command -v python3 &> /dev/null; then
            python3 --version
        else
            error "Python3 не найден"
        fi
        
        # Попытка запуска через systemd
        info "Попытка запуска через systemd..."
        if [ "$EUID" -eq 0 ]; then
            systemctl restart $SERVICE_NAME
            systemctl enable $SERVICE_NAME
        else
            sudo systemctl restart $SERVICE_NAME
            sudo systemctl enable $SERVICE_NAME
        fi
        
        sleep 3
        
        if systemctl is-active --quiet $SERVICE_NAME 2>/dev/null || sudo systemctl is-active --quiet $SERVICE_NAME 2>/dev/null; then
            success "Сервис запущен через systemd"
        else
            warning "Не удалось запустить через systemd. Проверьте конфигурацию."
            echo ""
            info "Проверка конфигурации systemd:"
            if [ "$EUID" -eq 0 ]; then
                systemctl cat $SERVICE_NAME 2>/dev/null | head -20
            else
                sudo systemctl cat $SERVICE_NAME 2>/dev/null | head -20
            fi
        fi
    else
        error "Виртуальное окружение не найдено: $APP_DIR/venv/bin/activate"
    fi
    echo ""
fi

# 8. Финальная проверка
echo "=== Финальная проверка ==="
echo ""

if systemctl is-active --quiet $SERVICE_NAME 2>/dev/null || sudo systemctl is-active --quiet $SERVICE_NAME 2>/dev/null; then
    success "✅ Приложение запущено"
    
    # Проверка HTTP еще раз
    sleep 2
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 http://localhost:5000 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "301" ]; then
        success "✅ Приложение отвечает на HTTP запросы"
    else
        warning "⚠️  Приложение запущено, но не отвечает на HTTP (код: $HTTP_CODE)"
        info "Проверьте логи выше для диагностики"
    fi
else
    error "❌ Приложение НЕ запущено"
    echo ""
    info "Рекомендации:"
    echo "1. Проверьте логи: sudo journalctl -u $SERVICE_NAME -n 50"
    echo "2. Проверьте конфигурацию: sudo systemctl cat $SERVICE_NAME"
    echo "3. Проверьте права доступа к файлам"
    echo "4. Проверьте, что порт 5000 не занят другим процессом"
fi

echo ""
echo "=== Полезные команды ==="
echo "Просмотр логов:        sudo journalctl -u $SERVICE_NAME -f"
echo "Перезапуск:            sudo systemctl restart $SERVICE_NAME"
echo "Остановка:             sudo systemctl stop $SERVICE_NAME"
echo "Проверка статуса:      sudo systemctl status $SERVICE_NAME"
echo "Проверка порта:        netstat -tuln | grep 5000"
echo ""

