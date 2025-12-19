# PowerShell скрипт для создания коммита в директории проекта
Set-Location "C:\Cursor\Tournaments_v.1 — 04598ed коммит в main_1"

Write-Host "🚀 Создание коммита в директории проекта..." -ForegroundColor Green
Write-Host "Текущая директория: $(Get-Location)" -ForegroundColor Yellow
Write-Host ""

# Проверяем наличие .git директории
if (!(Test-Path ".git")) {
    Write-Host "❌ Git репозиторий не найден! Инициализируем..." -ForegroundColor Red
    git init
    Write-Host "✅ Git репозиторий инициализирован!" -ForegroundColor Green
}

Write-Host "📊 Текущий статус:" -ForegroundColor Cyan
git status --porcelain

Write-Host ""
Write-Host "➕ Добавляем все файлы..." -ForegroundColor Yellow
git add .

Write-Host "📋 Изменения к коммиту:" -ForegroundColor Cyan
git status --porcelain

Write-Host ""
$commitMessage = @"
Update project with dual repo setup and migration scripts

- Added dual repository setup scripts (setup_dual_repos.sh, copy_repo_content.sh)
- Created server migration tools (server_migration.py, check_server_db_structure.py)
- Updated documentation with dual repo setup guide
- Added database structure checking tools
- Prepared for production deployment workflow
- Added SSH key setup instructions
- Created workflow for dev/prod environment separation
"@

Write-Host "💾 Создаем коммит..." -ForegroundColor Yellow
git commit -m $commitMessage

Write-Host ""
Write-Host "✅ Коммит создан успешно!" -ForegroundColor Green
Write-Host "📊 Информация о коммите:" -ForegroundColor Cyan
git log --oneline -1

Write-Host ""
Write-Host "Для выхода нажмите любую клавишу..." -ForegroundColor Gray
Read-Host
