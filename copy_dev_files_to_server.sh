#!/bin/bash
# Скрипт для копирования файлов dev окружения на сервер
# Использование: ./copy_dev_files_to_server.sh [SERVER_ADDRESS]

SERVER=${1:-"deploy@132742"}
# Если нужно указать другой адрес, используйте:
# ./copy_dev_files_to_server.sh deploy@ваш_сервер

echo "Копирование файлов dev окружения на сервер: $SERVER"
echo ""

# Проверка существования файлов
if [ ! -f "deployment/scripts/setup_dev_environment.sh" ]; then
    echo "Ошибка: deployment/scripts/setup_dev_environment.sh не найден"
    exit 1
fi

if [ ! -f "deployment/systemd/tournaments-dev.service" ]; then
    echo "Ошибка: deployment/systemd/tournaments-dev.service не найден"
    exit 1
fi

if [ ! -f "deployment/nginx/tournaments_with_dev.conf" ]; then
    echo "Ошибка: deployment/nginx/tournaments_with_dev.conf не найден"
    exit 1
fi

echo "1. Копирование скрипта настройки..."
scp deployment/scripts/setup_dev_environment.sh $SERVER:~/setup_dev_environment.sh

echo "2. Копирование конфигурации systemd..."
scp deployment/systemd/tournaments-dev.service $SERVER:~/tournaments-dev.service

echo "3. Копирование конфигурации Nginx..."
scp deployment/nginx/tournaments_with_dev.conf $SERVER:~/tournaments_with_dev.conf

echo ""
echo "✓ Все файлы скопированы на сервер"
echo ""
echo "Следующий шаг: подключитесь к серверу и выполните:"
echo "  chmod +x ~/setup_dev_environment.sh"
echo "  ~/setup_dev_environment.sh"

