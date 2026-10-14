# Registers a daily 6:30 PM weekday run of the stock-trader pipeline.
# Run once from PowerShell:
#   pwsh -File utils/register_daily_task.ps1

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = (Get-Command python).Source
$action = New-ScheduledTaskAction -Execute $python `
    -Argument "main.py --skip-email" -WorkingDirectory $projectRoot
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 6:30PM
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
Register-ScheduledTask -TaskName "StockTrader-DailyPipeline" -Action $action `
    -Trigger $trigger -Settings $settings -Description "stock-trader daily signal pipeline" -Force
Write-Host "Registered task 'StockTrader-DailyPipeline' (weekdays 6:30 PM). Remove --skip-email in Task Scheduler if the email report is wanted."
