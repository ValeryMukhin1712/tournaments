# Скрипт для просмотра логов сервера
# Использование: .\check_logs.ps1

Write-Host "=== Последние 50 строк логов ===" -ForegroundColor Green
Get-Content "app.log" -Tail 50 -Encoding UTF8

Write-Host "`n=== Поиск записей о добавлении опоздавшего участника ===" -ForegroundColor Green
Get-Content "app.log" -Encoding UTF8 | Select-String -Pattern "add_late_participant|опоздавш|late|participants/late" -Context 1,1 | Select-Object -Last 20

Write-Host "`n=== Поиск записей об удалении матчей ===" -ForegroundColor Yellow
Get-Content "app.log" -Encoding UTF8 | Select-String -Pattern "DELETE|удален|удалено|delete.*match|create_smart_schedule" -Context 1,1 | Select-Object -Last 20

Write-Host "`n=== Для просмотра логов в реальном времени используйте: ===" -ForegroundColor Cyan
Write-Host "Get-Content app.log -Wait -Tail 20" -ForegroundColor White

