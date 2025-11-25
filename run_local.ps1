# Скрипт для запуска приложения локально
Write-Host "=== Запуск Quick Score Tournaments локально ===" -ForegroundColor Green

# Проверка виртуального окружения
if (Test-Path "venv\Scripts\activate.ps1") {
    Write-Host "Активация виртуального окружения..." -ForegroundColor Yellow
    . venv\Scripts\activate.ps1
} else {
    Write-Host "Виртуальное окружение не найдено. Создаю..." -ForegroundColor Yellow
    python -m venv venv
    . venv\Scripts\activate.ps1
    Write-Host "Установка зависимостей..." -ForegroundColor Yellow
    pip install -r requirements.txt
}

# Проверка .env файла
if (-not (Test-Path ".env")) {
    Write-Host "Файл .env не найден. Создаю из env.example..." -ForegroundColor Yellow
    if (Test-Path "env.example") {
        Copy-Item "env.example" ".env"
        Write-Host "Файл .env создан. Отредактируйте его при необходимости." -ForegroundColor Yellow
    } else {
        Write-Host "ВНИМАНИЕ: env.example не найден!" -ForegroundColor Red
    }
}

# Проверка базы данных
if (-not (Test-Path "instance\tournament.db")) {
    Write-Host "База данных не найдена. Инициализация..." -ForegroundColor Yellow
    python init_db.py
}

# Установка переменной окружения для разработки
$env:FLASK_ENV = "development"
$env:FLASK_DEBUG = "True"

Write-Host "Запуск приложения на http://localhost:5000" -ForegroundColor Green
Write-Host "Для остановки нажмите Ctrl+C" -ForegroundColor Yellow
Write-Host ""

# Запуск приложения
python app.py

