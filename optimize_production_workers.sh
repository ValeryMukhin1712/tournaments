#!/bin/bash
# Скрипт для оптимизации количества workers в production

echo "=== Оптимизация production сервиса ==="
echo ""

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SERVICE_FILE="/etc/systemd/system/tournaments.service"
BACKUP_FILE="/etc/systemd/system/tournaments.service.backup"

# Проверка прав
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Ошибка: Запустите скрипт с sudo${NC}"
    exit 1
fi

# Проверка существования файла
if [ ! -f "$SERVICE_FILE" ]; then
    echo -e "${RED}Ошибка: Файл $SERVICE_FILE не найден${NC}"
    exit 1
fi

# Создание бэкапа
echo "1. Создание бэкапа конфигурации..."
cp "$SERVICE_FILE" "$BACKUP_FILE"
echo -e "${GREEN}✓ Бэкап создан: $BACKUP_FILE${NC}"
echo ""

# Проверка текущего количества workers
CURRENT_WORKERS=$(grep '--workers' "$SERVICE_FILE" | sed 's/.*--workers \([0-9]\+\).*/\1/' | head -1)

if [ -z "$CURRENT_WORKERS" ]; then
    echo -e "${YELLOW}⚠️  Не удалось определить текущее количество workers${NC}"
    echo "Проверьте файл вручную: $SERVICE_FILE"
    exit 1
fi

echo "2. Текущая конфигурация:"
echo "   Workers: $CURRENT_WORKERS"
echo ""

# Рекомендация
if [ "$CURRENT_WORKERS" -gt 2 ]; then
    echo -e "${YELLOW}⚠️  Обнаружено $CURRENT_WORKERS workers${NC}"
    echo "   Для сервера с ограниченной RAM (961MB) рекомендуется 2 workers"
    echo ""
    read -p "Уменьшить workers до 2? (y/n): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Замена workers
        sed -i 's/--workers [0-9]\+/--workers 2/g' "$SERVICE_FILE"
        
        echo ""
        echo "3. Применение изменений..."
        systemctl daemon-reload
        
        echo "4. Перезапуск сервиса..."
        systemctl restart tournaments
        
        sleep 3
        
        # Проверка статуса
        if systemctl is-active --quiet tournaments; then
            echo -e "${GREEN}✓ Сервис успешно перезапущен${NC}"
            echo ""
            echo "Новая конфигурация:"
            systemctl status tournaments --no-pager | grep workers | head -1
        else
            echo -e "${RED}❌ Ошибка при перезапуске сервиса${NC}"
            echo "Восстановление из бэкапа..."
            cp "$BACKUP_FILE" "$SERVICE_FILE"
            systemctl daemon-reload
            systemctl restart tournaments
            exit 1
        fi
    else
        echo "Отменено пользователем"
        exit 0
    fi
elif [ "$CURRENT_WORKERS" -eq 2 ]; then
    echo -e "${GREEN}✓ Количество workers уже оптимально (2)${NC}"
else
    echo -e "${GREEN}✓ Количество workers: $CURRENT_WORKERS (приемлемо)${NC}"
fi

echo ""
echo "=== Готово ==="
echo ""
echo "Проверка использования памяти:"
free -h

