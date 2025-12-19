@echo off
cd /d "C:\Cursor\Tournaments_v.1 — 04598ed коммит в main_1"

echo Initializing git repository if needed...
if not exist .git (
    git init
    echo Git repository initialized
)

echo Adding files to git...
git add .

echo Checking status...
git status

echo Making commit...
git commit -m "Update project with dual repo setup and migration scripts

- Added dual repository setup scripts
- Created server migration tools
- Updated documentation
- Added database structure checking tools
- Prepared for production deployment"

echo Commit completed!
pause
