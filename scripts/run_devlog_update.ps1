# run_devlog_update.ps1
# Windows Task Scheduler runner for the weekly dev log automation.
# Schedule: weekly, Sunday 9:00 AM
# Action: powershell.exe -ExecutionPolicy Bypass -File "C:\Users\ReconUnPro\Documents\GitHub\playinstigator-website\scripts\run_devlog_update.ps1"

$logFile = "C:\Users\ReconUnPro\Documents\GitHub\playinstigator-website\scripts\devlog_update.log"
$scriptDir = "C:\Users\ReconUnPro\Documents\GitHub\playinstigator-website"

# Rotate log if > 1 MB
if (Test-Path $logFile) {
    $size = (Get-Item $logFile).Length
    if ($size -gt 1MB) {
        $archive = $logFile -replace '\.log$', "_$(Get-Date -Format 'yyyyMMdd').log"
        Rename-Item -Path $logFile -NewName $archive
    }
}

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $logFile -Value "`n=== Run started $timestamp ==="

Set-Location $scriptDir

# Run the script (uses system Python -- ensure it's on PATH)
& python scripts\generate_devlog.py 2>&1 | Tee-Object -FilePath $logFile -Append

$exitCode = $LASTEXITCODE
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $logFile -Value "=== Run finished $timestamp (exit $exitCode) ==="
