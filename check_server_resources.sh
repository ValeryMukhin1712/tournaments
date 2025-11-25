#!/bin/bash
# Скрипт для проверки ресурсов VDS сервера

echo "=== Проверка ресурсов VDS сервера ==="
echo ""

# Цвета
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Функции для вывода
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. Информация о системе
echo "1️⃣  Информация о системе:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ОС: $(lsb_release -d 2>/dev/null | cut -f2 || cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
echo "Ядро: $(uname -r)"
echo "Архитектура: $(uname -m)"
echo "Время работы: $(uptime -p 2>/dev/null || uptime | awk -F'up ' '{print $2}' | awk -F',' '{print $1}')"
echo ""

# 2. CPU
echo "2️⃣  Процессор (CPU):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
CPU_CORES=$(nproc)
CPU_MODEL=$(grep "model name" /proc/cpuinfo | head -1 | cut -d':' -f2 | xargs)
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
LOAD_AVG=$(uptime | awk -F'load average:' '{print $2}')

echo "Модель: $CPU_MODEL"
echo "Ядер: $CPU_CORES"
echo "Загрузка CPU: ${CPU_USAGE}%"
echo "Средняя загрузка: $LOAD_AVG"

# Оценка загрузки CPU
if (( $(echo "$CPU_USAGE > 80" | bc -l 2>/dev/null || echo "0") )); then
    error "⚠️  Высокая загрузка CPU (>80%)"
elif (( $(echo "$CPU_USAGE > 60" | bc -l 2>/dev/null || echo "0") )); then
    warning "⚠️  Средняя загрузка CPU (>60%)"
else
    success "✓ Загрузка CPU в норме"
fi
echo ""

# 3. Память (RAM)
echo "3️⃣  Оперативная память (RAM):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if command -v free &> /dev/null; then
    MEM_INFO=$(free -h)
    MEM_TOTAL=$(free -h | grep Mem | awk '{print $2}')
    MEM_USED=$(free -h | grep Mem | awk '{print $3}')
    MEM_AVAILABLE=$(free -h | grep Mem | awk '{print $7}')
    MEM_PERCENT=$(free | grep Mem | awk '{printf "%.1f", ($3/$2) * 100}')
    
    echo "$MEM_INFO"
    echo ""
    echo "Использовано: ${MEM_PERCENT}%"
    
    # Оценка использования памяти
    if (( $(echo "$MEM_PERCENT > 90" | bc -l 2>/dev/null || echo "0") )); then
        error "⚠️  Критически мало свободной памяти (<10%)"
    elif (( $(echo "$MEM_PERCENT > 80" | bc -l 2>/dev/null || echo "0") )); then
        warning "⚠️  Мало свободной памяти (<20%)"
    else
        success "✓ Память в норме"
    fi
else
    warning "Команда 'free' не найдена"
fi
echo ""

# 4. Дисковое пространство
echo "4️⃣  Дисковое пространство:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if command -v df &> /dev/null; then
    df -h | grep -E '^/dev/|Filesystem' | head -5
    echo ""
    
    # Проверка корневого раздела
    ROOT_USAGE=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
    ROOT_AVAILABLE=$(df -h / | tail -1 | awk '{print $4}')
    
    echo "Корневой раздел (/) использовано: ${ROOT_USAGE}%"
    echo "Доступно: $ROOT_AVAILABLE"
    
    # Оценка дискового пространства
    if [ "$ROOT_USAGE" -gt 90 ]; then
        error "⚠️  Критически мало места на диске (<10%)"
    elif [ "$ROOT_USAGE" -gt 80 ]; then
        warning "⚠️  Мало места на диске (<20%)"
    else
        success "✓ Дисковое пространство в норме"
    fi
else
    warning "Команда 'df' не найдена"
fi
echo ""

# 5. Сетевая активность
echo "5️⃣  Сетевая активность:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if command -v ifconfig &> /dev/null; then
    INTERFACES=$(ifconfig -s | awk '{print $1}' | tail -n +2)
    for iface in $INTERFACES; do
        if [ "$iface" != "lo" ]; then
            RX_BYTES=$(cat /sys/class/net/$iface/statistics/rx_bytes 2>/dev/null || echo "0")
            TX_BYTES=$(cat /sys/class/net/$iface/statistics/tx_bytes 2>/dev/null || echo "0")
            if [ "$RX_BYTES" != "0" ] || [ "$TX_BYTES" != "0" ]; then
                RX_MB=$(echo "scale=2; $RX_BYTES/1024/1024" | bc 2>/dev/null || echo "0")
                TX_MB=$(echo "scale=2; $TX_BYTES/1024/1024" | bc 2>/dev/null || echo "0")
                echo "Интерфейс $iface:"
                echo "  Получено: ${RX_MB} MB"
                echo "  Отправлено: ${TX_MB} MB"
            fi
        fi
    done
elif command -v ip &> /dev/null; then
    ip -s link show | grep -A 2 -E "^[0-9]+:" | head -10
else
    warning "Не удалось получить информацию о сети"
fi
echo ""

# 6. Запущенные процессы
echo "6️⃣  Топ процессов по использованию памяти:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if command -v ps &> /dev/null; then
    ps aux --sort=-%mem | head -6 | awk '{printf "%-10s %6s %6s %s\n", $1, $2, $3"%", $11}'
else
    warning "Команда 'ps' не найдена"
fi
echo ""

# 7. Запущенные сервисы приложения
echo "7️⃣  Сервисы приложения:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if systemctl is-active --quiet tournaments 2>/dev/null; then
    success "✓ tournaments (production) - запущен"
    systemctl status tournaments --no-pager -l | head -5
else
    warning "⚠️  tournaments (production) - не запущен"
fi
echo ""

if systemctl is-active --quiet tournaments-dev 2>/dev/null; then
    success "✓ tournaments-dev - запущен"
    systemctl status tournaments-dev --no-pager -l | head -5
else
    info "tournaments-dev - не настроен"
fi
echo ""

# 8. Использование портов
echo "8️⃣  Использование портов:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if command -v netstat &> /dev/null; then
    netstat -tuln | grep -E ":5000|:5001|:80|:443" | head -10
elif command -v ss &> /dev/null; then
    ss -tuln | grep -E ":5000|:5001|:80|:443" | head -10
else
    warning "Не удалось проверить порты"
fi
echo ""

# 9. Рекомендации
echo "9️⃣  Рекомендации:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Проверка минимальных требований
MIN_RAM_GB=1
MIN_DISK_GB=5

# Проверка RAM
TOTAL_RAM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
TOTAL_RAM_GB=$(echo "scale=2; $TOTAL_RAM_KB/1024/1024" | bc 2>/dev/null || echo "0")

if (( $(echo "$TOTAL_RAM_GB < $MIN_RAM_GB" | bc -l 2>/dev/null || echo "0") )); then
    error "⚠️  Рекомендуется минимум ${MIN_RAM_GB}GB RAM (сейчас: ${TOTAL_RAM_GB}GB)"
else
    success "✓ RAM: ${TOTAL_RAM_GB}GB (минимум: ${MIN_RAM_GB}GB)"
fi

# Проверка диска
TOTAL_DISK_GB=$(df -BG / | tail -1 | awk '{print $2}' | sed 's/G//')
if [ -n "$TOTAL_DISK_GB" ] && [ "$TOTAL_DISK_GB" -lt "$MIN_DISK_GB" ]; then
    error "⚠️  Рекомендуется минимум ${MIN_DISK_GB}GB диска (сейчас: ${TOTAL_DISK_GB}GB)"
else
    success "✓ Диск: ${TOTAL_DISK_GB}GB (минимум: ${MIN_DISK_GB}GB)"
fi

echo ""
echo "=== Проверка завершена ==="

