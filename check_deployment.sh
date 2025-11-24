#!/bin/bash
# Скрипт для проверки деплоя приложения на сервере

echo "=== Проверка деплоя приложения ==="
echo ""

# Цвета
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 1. Проверка статуса сервиса
echo "1️⃣  Проверка статуса сервиса tournaments:"
if sudo systemctl is-active --quiet tournaments; then
    echo -e "${GREEN}✅ Сервис запущен${NC}"
    sudo systemctl status tournaments --no-pager -l | head -10
else
    echo -e "${RED}❌ Сервис не запущен!${NC}"
    sudo systemctl status tournaments --no-pager -l | head -10
fi
echo ""

# 2. Проверка версии на сервере
echo "2️⃣  Проверка версии на сервере:"
cd ~/quick-score 2>/dev/null || cd /home/deploy/quick-score 2>/dev/null || {
    echo -e "${RED}❌ Не удалось найти директорию приложения${NC}"
    exit 1
}

LOCAL_COMMIT=$(git rev-parse HEAD 2>/dev/null)
LOCAL_MSG=$(git log -1 --pretty=format:"%s" 2>/dev/null)
LOCAL_DATE=$(git log -1 --pretty=format:"%ar" 2>/dev/null)

if [ -n "$LOCAL_COMMIT" ]; then
    echo -e "${GREEN}✅ Текущий коммит на сервере:${NC}"
    echo "   Хеш: ${LOCAL_COMMIT:0:7}"
    echo "   Сообщение: $LOCAL_MSG"
    echo "   Дата: $LOCAL_DATE"
else
    echo -e "${RED}❌ Не удалось получить информацию о коммите${NC}"
fi
echo ""

# 3. Сравнение с GitHub
echo "3️⃣  Сравнение с GitHub:"
git fetch origin 2>/dev/null
REMOTE_COMMIT=$(git rev-parse origin/main 2>/dev/null)

if [ -n "$REMOTE_COMMIT" ]; then
    if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ]; then
        echo -e "${GREEN}✅ Версия на сервере совпадает с GitHub${NC}"
    else
        echo -e "${YELLOW}⚠️  Версия на сервере отличается от GitHub${NC}"
        echo "   Локально:  ${LOCAL_COMMIT:0:7}"
        echo "   На GitHub: ${REMOTE_COMMIT:0:7}"
        echo ""
        echo "   Новые коммиты на GitHub:"
        git log HEAD..origin/main --oneline -5 2>/dev/null || echo "   (не удалось получить)"
    fi
else
    echo -e "${YELLOW}⚠️  Не удалось подключиться к GitHub${NC}"
fi
echo ""

# 4. Проверка порта
echo "4️⃣  Проверка порта 5000:"
if netstat -tuln 2>/dev/null | grep -q ":5000" || ss -tuln 2>/dev/null | grep -q ":5000"; then
    echo -e "${GREEN}✅ Приложение слушает порт 5000${NC}"
else
    echo -e "${RED}❌ Приложение не слушает порт 5000${NC}"
fi
echo ""

# 5. Проверка доступности через HTTP
echo "5️⃣  Проверка доступности через HTTP:"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "301" ]; then
    echo -e "${GREEN}✅ Приложение отвечает (HTTP $HTTP_CODE)${NC}"
else
    echo -e "${RED}❌ Приложение не отвечает (HTTP $HTTP_CODE)${NC}"
fi
echo ""

# 6. Проверка последних логов
echo "6️⃣  Последние 10 строк логов:"
sudo journalctl -u tournaments -n 10 --no-pager 2>/dev/null || echo "Не удалось получить логи"
echo ""

# 7. Проверка несохраненных изменений
echo "7️⃣  Проверка несохраненных изменений:"
if git diff --quiet 2>/dev/null && git diff --cached --quiet 2>/dev/null; then
    echo -e "${GREEN}✅ Нет несохраненных изменений${NC}"
else
    echo -e "${YELLOW}⚠️  Есть несохраненные изменения:${NC}"
    git status --short
fi
echo ""

# Итоговая информация
echo "=== Итоговая информация ==="
echo ""
echo "📌 Текущий коммит на сервере: ${LOCAL_COMMIT:0:7}"
echo "📌 Последнее сообщение коммита: $LOCAL_MSG"
echo ""
echo "💡 Для обновления до последней версии с GitHub:"
echo "   git pull origin main"
echo "   sudo systemctl restart tournaments"
echo ""
echo "💡 Для просмотра логов в реальном времени:"
echo "   sudo journalctl -u tournaments -f"
echo ""

