#!/bin/bash
# Скрипт для копирования содержимого из репозитория quick-score в tournaments

echo "📋 Копирование содержимого из quick-score в tournaments"

# Настройки репозиториев
SOURCE_REPO="https://github.com/ValeryMukhin1712/quick-score.git"
TARGET_REPO="https://github.com/ValeryMukhin1712/tournaments.git"

# Временная директория для работы
TEMP_DIR="/tmp/repo_copy_$(date +%s)"

echo "🔧 Создание временной директории: $TEMP_DIR"
mkdir -p "$TEMP_DIR"
cd "$TEMP_DIR"

echo "📥 Клонирование исходного репозитория..."
git clone "$SOURCE_REPO" source_repo
cd source_repo

echo "📊 Информация об исходном репозитории:"
echo "Ветка: $(git branch --show-current)"
echo "Последний коммит: $(git log -1 --oneline)"
echo "Количество файлов: $(find . -type f -not -path './.git/*' | wc -l)"

echo "🔄 Подготовка файлов для копирования..."
# Исключаем .git директорию и временные файлы
find . -name ".git" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.tmp" -delete 2>/dev/null || true
find . -name "*.log" -delete 2>/dev/null || true

echo "📤 Клонирование целевого репозитория..."
cd "$TEMP_DIR"
git clone "$TARGET_REPO" target_repo
cd target_repo

echo "🧹 Очистка целевого репозитория..."
# Сохраняем только .git директорию
find . -maxdepth 1 -not -name ".git" -not -name "." -exec rm -rf {} \;

echo "📋 Копирование файлов из исходного репозитория..."
cp -r ../source_repo/* .
cp -r ../source_repo/.* . 2>/dev/null || true

echo "📊 Проверка скопированных файлов:"
echo "Количество файлов: $(find . -type f -not -path './.git/*' | wc -l)"
ls -la

echo "📝 Проверка статуса git..."
git status

echo "✅ Подготовка завершена!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Проверьте содержимое: cd $TEMP_DIR/target_repo"
echo "2. Если все корректно, выполните:"
echo "   git add ."
echo "   git commit -m 'Copy content from quick-score repository'"
echo "   git push origin main"
echo ""
echo "⚠️  ВАЖНО: Перед выполнением убедитесь, что:"
echo "   - В целевом репозитории нет важных несохраненных изменений"
echo "   - У вас есть права на push в tournaments репозиторий"
