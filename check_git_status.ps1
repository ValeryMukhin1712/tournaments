# PowerShell скрипт для проверки статуса git в директории проекта
Set-Location "C:\Cursor\Tournaments_v.1 — 04598ed коммит в main_1"

Write-Host "🔍 Проверка статуса git в директории проекта..." -ForegroundColor Green
Write-Host "Текущая директория: $(Get-Location)" -ForegroundColor Yellow
Write-Host ""

# Проверяем наличие .git директории
if (Test-Path ".git") {
    Write-Host "✅ Git репозиторий найден!" -ForegroundColor Green

    # Выполняем git status
    Write-Host "📊 Git status:" -ForegroundColor Cyan
    git status

    Write-Host ""
    Write-Host "📋 Доступные действия:" -ForegroundColor Yellow
    Write-Host "1. Добавить файлы: git add ."
    Write-Host "2. Создать коммит: git commit -m 'сообщение'"
    Write-Host "3. Проверить историю: git log --oneline"

} else {
    Write-Host "❌ Git репозиторий не найден!" -ForegroundColor Red
    Write-Host "Инициализация git репозитория..." -ForegroundColor Yellow

    git init
    Write-Host "✅ Git репозиторий инициализирован!" -ForegroundColor Green
}

Write-Host ""
Write-Host "Для выхода нажмите любую клавишу..." -ForegroundColor Gray
Read-Host
