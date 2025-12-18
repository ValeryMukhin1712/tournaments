@echo off
chcp 65001 >nul
cd /d "C:\Cursor\Tournaments_v.1 — 04598ed коммит в main_1"
echo Активация виртуального окружения...
call venv\Scripts\activate.bat
echo Запуск приложения на http://localhost:5000
python app.py
pause



