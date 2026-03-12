param(
    [string]$TaskName = "SMAPService",
    [string]$ServiceBin = "",
    [string]$WorkingDir = ".",
    [string[]]$ServiceArgs = @(),
    [string]$Description = "SMAP Background Service"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

if ([string]::IsNullOrWhiteSpace($ServiceBin)) {
    $defaultBin = Join-Path $repoRoot "apps\service\dist\smap-service.exe"
    if (Test-Path $defaultBin) {
        $ServiceBin = $defaultBin
    } else {
        throw "Missing -ServiceBin and no default binary found at apps/service/dist/smap-service.exe"
    }
}

$templatePath = Join-Path $repoRoot "apps\desktop\resources\service_templates\windows.task.xml.tmpl"
if (!(Test-Path $templatePath)) {
    throw "Template not found: $templatePath"
}

$xmlEscape = {
    param([string]$Value)
    return [System.Security.SecurityElement]::Escape($Value)
}

$template = Get-Content $templatePath -Raw
$argsText = ($ServiceArgs -join " ")
$template = $template.Replace("{{DESCRIPTION}}", (& $xmlEscape $Description))
$template = $template.Replace("{{SERVICE_BIN}}", (& $xmlEscape $ServiceBin))
$template = $template.Replace("{{SERVICE_ARGS}}", (& $xmlEscape $argsText))
$template = $template.Replace("{{WORKING_DIRECTORY}}", (& $xmlEscape (Resolve-Path $WorkingDir).Path))

$tmp = New-TemporaryFile
Set-Content -Path $tmp.FullName -Value $template -Encoding Unicode

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

Register-ScheduledTask -TaskName $TaskName -Xml (Get-Content $tmp.FullName -Raw) | Out-Null
Remove-Item $tmp.FullName -Force
Start-ScheduledTask -TaskName $TaskName
Write-Host "Installed and started scheduled task $TaskName"
