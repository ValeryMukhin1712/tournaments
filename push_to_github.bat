@echo off
chcp 65001 >nul
cd /d "c:\Cursor\Tournaments_v.1 — 04598ed коммит в main_1"

echo Checking git status...
git status

echo Adding all files...
git add .

echo Committing changes...
git commit -m "Update project - latest version with all fixes"

echo Setting remote origin...
git remote remove origin 2>nul
git remote add origin https://github.com/ValeryMukhin1712/tournaments.git

echo Pushing to main with force...
git push -u origin main --force

echo Done! Project uploaded to GitHub.
pause
