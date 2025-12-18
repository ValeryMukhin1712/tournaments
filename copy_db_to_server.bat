@echo off
chcp 65001 >nul
echo ========================================
echo Копирование базы данных на сервер через SSH
echo ========================================
echo.

REM Определяем путь к файлу базы данных
set LOCAL_DB=tournament.db
if not exist "%LOCAL_DB%" (
    set LOCAL_DB=instance\tournament.db
)

if not exist "%LOCAL_DB%" (
    echo ОШИБКА: Файл базы данных не найден!
    echo Проверьте наличие файла tournament.db или instance\tournament.db
    pause
    exit /b 1
)

echo Найден файл базы данных: %LOCAL_DB%
echo.

REM Параметры подключения
set SERVER_USER=deploy
set SERVER_HOST=89.19.44.212
set REMOTE_PATH=/home/deploy/quick-score/instance/tournament.db

echo Параметры подключения:
echo   Сервер: %SERVER_USER%@%SERVER_HOST%
echo   Локальный файл: %CD%\%LOCAL_DB%
echo   Удаленный путь: %REMOTE_PATH%
echo.

REM Проверяем наличие scp (обычно доступен через Git Bash или WSL)
where scp >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ВНИМАНИЕ: Команда scp не найдена в PATH!
    echo.
    echo Установите один из вариантов:
    echo   1. Git for Windows (включает Git Bash с scp)
    echo   2. WSL (Windows Subsystem for Linux)
    echo   3. Используйте команду вручную в Git Bash или WSL
    echo.
    echo Команда для выполнения:
    echo   scp "%CD%\%LOCAL_DB%" %SERVER_USER%@%SERVER_HOST%:%REMOTE_PATH%
    echo.
    pause
    exit /b 1
)

echo Выполняется копирование...
echo Введите пароль при запросе.
echo.

scp "%CD%\%LOCAL_DB%" %SERVER_USER%@%SERVER_HOST%:%REMOTE_PATH%

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo Копирование завершено успешно!
    echo ========================================
    echo.
    echo Теперь подключитесь к серверу и выполните:
    echo   ssh %SERVER_USER%@%SERVER_HOST%
    echo   cd /home/deploy/quick-score
    echo   sudo chmod 644 instance/tournament.db
    echo   sudo chown deploy:deploy instance/tournament.db
    echo   sudo systemctl start tournaments
    echo.
) else (
    echo.
    echo ========================================
    echo ОШИБКА при копировании!
    echo ========================================
    echo.
    echo Проверьте:
    echo   1. Правильность пароля
    echo   2. Доступность сервера
    echo   3. Права доступа на сервере
    echo.
)

pause



