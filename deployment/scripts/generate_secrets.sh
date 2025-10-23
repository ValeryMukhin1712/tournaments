#!/bin/bash

###############################################################################
# Generate Secrets Script
# Генерация секретных ключей для приложения
###############################################################################

echo "=== Генератор секретных ключей ==="
echo ""

# Генерация SECRET_KEY для Flask
echo "SECRET_KEY для Flask (.env):"
python3 -c 'import secrets; print(secrets.token_hex(32))'
echo ""

# Генерация WEBHOOK_SECRET
echo "WEBHOOK_SECRET для GitHub webhook:"
python3 -c 'import secrets; print(secrets.token_hex(32))'
echo ""

# Генерация случайного пароля
echo "Случайный пароль (для admin):"
python3 -c 'import secrets, string; print("".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16)))'
echo ""

echo "Скопируйте сгенерированные значения в соответствующие конфигурационные файлы."
echo "Не сохраняйте их в публичных местах!"

