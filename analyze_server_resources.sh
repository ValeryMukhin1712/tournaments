#!/bin/bash
# Анализ ресурсов сервера и рекомендации

echo "=== Анализ ресурсов сервера ==="
echo ""

# Цвета
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Получение данных
DISK_USAGE=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
DISK_AVAILABLE=$(df -h / | tail -1 | awk '{print $4}')
TOTAL_RAM=$(free -h | grep Mem | awk '{print $2}')
USED_RAM=$(free -h | grep Mem | awk '{print $3}')
AVAILABLE_RAM=$(free -h | grep Mem | awk '{print $7}')
RAM_PERCENT=$(free | grep Mem | awk '{printf "%.0f", ($3/$2) * 100}')

echo "📊 Текущее состояние:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💾 Диск:"
echo "   Использовано: ${DISK_USAGE}%"
echo "   Доступно: ${DISK_AVAILABLE}"
echo ""
echo "🧠 Память (RAM):"
echo "   Всего: ${TOTAL_RAM}"
echo "   Использовано: ${USED_RAM} (${RAM_PERCENT}%)"
echo "   Доступно: ${AVAILABLE_RAM}"
echo ""

# Анализ
echo "🔍 Анализ:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Диск
if [ "$DISK_USAGE" -gt 90 ]; then
    echo -e "${RED}❌ КРИТИЧНО: Диск заполнен более чем на 90%${NC}"
elif [ "$DISK_USAGE" -gt 80 ]; then
    echo -e "${YELLOW}⚠️  ВНИМАНИЕ: Диск заполнен на ${DISK_USAGE}% (рекомендуется <80%)${NC}"
else
    echo -e "${GREEN}✓ Диск: ${DISK_USAGE}% - в норме${NC}"
fi

# RAM
if [ "$RAM_PERCENT" -gt 90 ]; then
    echo -e "${RED}❌ КРИТИЧНО: Память использована более чем на 90%${NC}"
elif [ "$RAM_PERCENT" -gt 80 ]; then
    echo -e "${YELLOW}⚠️  ВНИМАНИЕ: Память использована на ${RAM_PERCENT}% (рекомендуется <80%)${NC}"
else
    echo -e "${GREEN}✓ Память: ${RAM_PERCENT}% - в норме${NC}"
fi

echo ""

# Рекомендации
echo "💡 Рекомендации:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Проверка возможности добавления dev окружения
echo "Для добавления dev окружения потребуется:"
echo "  • ~500MB дискового пространства (код + зависимости)"
echo "  • ~200-300MB RAM (дополнительный процесс Gunicorn)"
echo ""

if [ "$DISK_USAGE" -gt 85 ]; then
    echo -e "${RED}❌ НЕ РЕКОМЕНДУЕТСЯ добавлять dev окружение: мало места на диске${NC}"
    echo "   Сначала освободите место (см. рекомендации ниже)"
elif [ "$RAM_PERCENT" -gt 75 ]; then
    echo -e "${YELLOW}⚠️  ОСТОРОЖНО: Можно добавить dev, но с ограничениями${NC}"
    echo "   • Используйте --workers 1 для dev версии"
    echo "   • Мониторьте использование памяти"
else
    echo -e "${GREEN}✓ Можно добавить dev окружение${NC}"
fi

echo ""

# Рекомендации по оптимизации
echo "🔧 Оптимизация перед добавлением dev:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Очистка диска
echo "1. Очистка дискового пространства:"
echo "   # Очистить старые логи (может освободить 100-500MB):"
echo "   sudo journalctl --vacuum-time=7d"
echo "   sudo journalctl --vacuum-size=100M"
echo ""
echo "   # Очистить кэш пакетов:"
echo "   sudo apt clean"
echo "   sudo apt autoremove"
echo ""
echo "   # Проверить размер баз данных:"
echo "   du -sh ~/quick-score/instance/tournament.db"
echo ""

# 2. Оптимизация RAM
echo "2. Оптимизация памяти:"
echo "   # Уменьшить количество workers в production:"
echo "   sudo nano /etc/systemd/system/tournaments.service"
echo "   # Измените --workers 4 на --workers 2"
echo ""
echo "   # Для dev версии использовать минимум workers:"
echo "   # --workers 1 (в tournaments-dev.service)"
echo ""

# 3. Проверка больших файлов
echo "3. Поиск больших файлов:"
echo "   # Найти самые большие директории:"
echo "   du -sh ~/* | sort -h | tail -10"
echo ""
echo "   # Найти большие файлы:"
echo "   find ~ -type f -size +50M 2>/dev/null"
echo ""

# 4. Мониторинг
echo "4. Мониторинг после добавления dev:"
echo "   # Проверить использование ресурсов:"
echo "   ~/check_server_resources.sh"
echo ""
echo "   # Мониторинг в реальном времени:"
echo "   watch -n 5 'free -h && df -h /'"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Итоговая оценка
echo "📋 Итоговая оценка:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

TOTAL_SCORE=0

if [ "$DISK_USAGE" -lt 80 ]; then
    TOTAL_SCORE=$((TOTAL_SCORE + 1))
fi
if [ "$RAM_PERCENT" -lt 75 ]; then
    TOTAL_SCORE=$((TOTAL_SCORE + 1))
fi

if [ "$TOTAL_SCORE" -eq 2 ]; then
    echo -e "${GREEN}✓ Сервер готов для добавления dev окружения${NC}"
elif [ "$TOTAL_SCORE" -eq 1 ]; then
    echo -e "${YELLOW}⚠️  Рекомендуется оптимизация перед добавлением dev${NC}"
else
    echo -e "${RED}❌ Требуется оптимизация перед добавлением dev${NC}"
fi

echo ""

