# PowerShell скрипт для создания коммита
Set-Location "C:\Cursor\Tournaments_v.1 — 04598ed коммит в main_1"

# Инициализируем git если нужно
if (!(Test-Path ".git")) {
    git init
    Write-Host "Git repository initialized"
}

# Добавляем файлы
git add .

# Проверяем статус
Write-Host "Git status:"
git status --porcelain

# Создаем коммит
$commitMessage = @"
Update project with dual repo setup and migration scripts

- Added dual repository setup scripts (setup_dual_repos.sh, copy_repo_content.sh)
- Created server migration tools (server_migration.py, check_server_db_structure.py)
- Updated documentation with dual repo setup guide
- Added database structure checking tools
- Prepared for production deployment workflow
- Added SSH key setup instructions
- Created workflow for dev/prod environment separation
"@

git commit -m $commitMessage

Write-Host "Commit completed successfully!"
Write-Host "Last commit:"
git log --oneline -1
