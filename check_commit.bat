@echo off
chcp 65001 >nul
cd /d "C:\Cursor\Tournaments_v.1 — 04598ed коммит в main_1"
if exist .git (
    echo Checking git repository...
    git log -1 --oneline
    echo.
    git rev-parse HEAD
    echo.
    git status --short
) else (
    echo Git repository not initialized
)



