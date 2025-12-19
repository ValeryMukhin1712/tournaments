#!/bin/bash
# Скрипт для настройки двух репозиториев на VDS серверах

echo "🚀 Настройка двух репозиториев для VDS серверов"

# Функция для настройки репозитория на сервере
setup_repo_on_server() {
    local server_name=$1
    local repo_url=$2
    local project_dir=$3

    echo "📋 Настройка репозитория на сервере: $server_name"
    echo "   Репозиторий: $repo_url"
    echo "   Директория: $project_dir"

    cat << EOF

Команды для выполнения на сервере $server_name:

# 1. Подключитесь к серверу
ssh $server_name

# 2. Перейдите в директорию проекта (или создайте если нужно)
cd $project_dir || mkdir -p $project_dir && cd $project_dir

# 3. Если директория пустая - клонируйте репозиторий
if [ ! -d ".git" ]; then
    git clone $repo_url .
fi

# 4. Настройте remote origin
git remote set-url origin $repo_url

# 5. Проверьте настройки
git remote -v
git status
git branch -a

# 6. Создайте и настройте ветки (если нужно)
git checkout -b main
git pull origin main

EOF
}

# Настройки для серверов
SERVER1="tournament-admin@45.135.164.202"
REPO1_URL="https://github.com/ValeryMukhin1712/tournaments.git"

SERVER2="deploy@89.19.44.212"
REPO2_URL="https://github.com/ValeryMukhin1712/tournaments-dev.git"

# Существующий репозиторий-источник
SOURCE_REPO="https://github.com/ValeryMukhin1712/quick-score.git"

PROJECT_DIR1="/home/tournament-admin/quick-score"
PROJECT_DIR2="/home/deploy/quick-score"

echo "🔧 Конфигурация:"
echo "Сервер 1 (Prod): $SERVER1"
echo "Репозиторий 1: $REPO1_URL"
echo ""
echo "Сервер 2 (Dev): $SERVER2"
echo "Репозиторий 2: $REPO2_URL"
echo ""
echo "Источник: $SOURCE_REPO"
echo ""

echo "⚠️  ПРЕДВАРИТЕЛЬНЫЕ ШАГИ:"
echo "1. Убедитесь, что содержимое из $SOURCE_REPO скопировано в $REPO1_URL"
echo "2. Создайте репозиторий $REPO2_URL и настройте ветку develop"
echo "3. Выполните: ./copy_repo_content.sh (если нужно)"
echo ""

setup_repo_on_server "$SERVER1" "$REPO1_URL" "$PROJECT_DIR1"
setup_repo_on_server "$SERVER2" "$REPO2_URL" "$PROJECT_DIR2"

echo "✅ Инструкции подготовлены!"
echo ""
echo "📝 Следующие шаги:"
echo "1. Создайте репозитории на GitHub/GitLab"
echo "2. Выполните команды на каждом сервере"
echo "3. Настройте SSH ключи для автоматической синхронизации"
echo "4. Протестируйте push/pull"
