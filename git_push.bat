@echo off
chcp 65001 >nul
cd /d "C:\Cursor\Tournaments_v.1 — 04598ed коммит в main_1"
echo Проверка статуса git...
git status --short
echo.
echo Push в origin/main...
git push origin main
if %errorlevel% equ 0 (
    echo.
    echo Push выполнен успешно!
) else (
    echo.
    echo Ошибка при push. Код ошибки: %errorlevel%
)
pause



