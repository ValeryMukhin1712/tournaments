@echo off
chcp 65001 >nul
cd /d "C:\Cursor\Tournaments_v.1 — 04598ed коммит в main_1"
git init
git remote add origin https://github.com/ValeryMukhin1712/quick-score.git 2>nul
git add .
git commit -m "Добавлена поддержка свободных матчей без турнира: миграции БД, API endpoints, форма создания матчей с автодополнением игроков"
echo Git commit completed


