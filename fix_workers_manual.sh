#!/bin/bash
# Простой скрипт для уменьшения workers (совместимый с любым grep)

echo "=== Оптимизация production сервиса ==="
echo ""

SERVICE_FILE="/etc/systemd/system/tournaments.service"
BACKUP_FILE="/etc/systemd/system/tournaments.service.backup"

# Проверка прав
if [ "$EUID" -ne 0 ]; then 
    echo "Ошибка: Запустите скрипт с sudo"
    exit 1
fi

# Создание бэкапа
echo "1. Создание бэкапа..."
cp "$SERVICE_FILE" "$BACKUP_FILE"
echo "✓ Бэкап создан: $BACKUP_FILE"
echo ""

# Проверка текущего количества workers
CURRENT_LINE=$(grep '--workers' "$SERVICE_FILE")
echo "Текущая строка: $CURRENT_LINE"
echo ""

# Извлечение числа
CURRENT_WORKERS=$(echo "$CURRENT_LINE" | sed 's/.*--workers \([0-9]\+\).*/\1/')

if [ -z "$CURRENT_WORKERS" ]; then
    echo "⚠️  Не удалось определить количество workers"
    echo "Проверьте файл вручную: $SERVICE_FILE"
    exit 1
fi

echo "2. Текущее количество workers: $CURRENT_WORKERS"
echo ""

if [ "$CURRENT_WORKERS" -gt 2 ]; then
    echo "⚠️  Обнаружено $CURRENT_WORKERS workers"
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
            echo "✓ Сервис успешно перезапущен"
            echo ""
            echo "Новая конфигурация:"
            systemctl status tournaments --no-pager | grep workers | head -1
        else
            echo "❌ Ошибка при перезапуске сервиса"
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
    echo "✓ Количество workers уже оптимально (2)"
else
    echo "✓ Количество workers: $CURRENT_WORKERS (приемлемо)"
fi

echo ""
echo "=== Готово ==="
echo ""
echo "Проверка использования памяти:"
free -h

