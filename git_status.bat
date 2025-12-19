@echo off
cd /d "C:\Cursor\Tournaments_v.1 — 04598ed коммит в main_1"

echo Checking git status in project directory...
echo Current directory: %CD%
echo.

if exist .git (
    echo Git repository found.
    git status
) else (
    echo No git repository found. Initializing...
    git init
    echo Git repository initialized.
    git status
)

echo.
echo Press any key to exit...
pause >nul
