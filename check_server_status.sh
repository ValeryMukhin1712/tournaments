#!/bin/bash
# Скрипт для проверки статуса приложения на сервере

echo "=== Проверка статуса сервиса tournaments ==="
sudo systemctl status tournaments

echo ""
echo "=== Перезапуск сервиса ==="
sudo systemctl restart tournaments

echo ""
echo "=== Проверка статуса после перезапуска ==="
sudo systemctl status tournaments

echo ""
echo "=== Последние 50 строк логов ==="
journalctl -u tournaments -n 50 --no-pager
















