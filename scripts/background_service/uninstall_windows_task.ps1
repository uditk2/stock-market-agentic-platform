param(
    [string]$TaskName = "SMAPService"
)

$ErrorActionPreference = "Stop"
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Uninstalled scheduled task $TaskName"
} else {
    Write-Host "Scheduled task $TaskName not found"
}
