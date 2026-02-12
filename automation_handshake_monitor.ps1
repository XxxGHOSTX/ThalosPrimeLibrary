# Thalos Prime Handshake Monitor (no auto-restart)
# Sends periodic handshakes and logs status. Alerts on failure but does NOT restart.

param(
    [string]$Url = "http://127.0.0.1:8000/api/handshake",
    [int]$IntervalSeconds = 60,
    [string]$LogFile = "handshake_monitor.log"
)

Write-Host "Starting Thalos Prime handshake monitor..." -ForegroundColor Cyan
Write-Host "URL: $Url" -ForegroundColor Cyan
Write-Host "Interval: $IntervalSeconds seconds" -ForegroundColor Cyan
Write-Host "Log: $LogFile" -ForegroundColor Cyan
Write-Host "(No auto-restart will be performed.)" -ForegroundColor Yellow

while ($true) {
    $timestamp = (Get-Date).ToString("s") + "Z"
    try {
        $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10
        $json = $resp.Content | ConvertFrom-Json
        $status = $json.status
        $mode = $json.mode
        $line = "$timestamp OK status=$status mode=$mode"
        Add-Content -Path $LogFile -Value $line
        Write-Host $line -ForegroundColor Green
    }
    catch {
        $line = "$timestamp ERROR $_"
        Add-Content -Path $LogFile -Value $line
        Write-Host $line -ForegroundColor Red
        [console]::beep(1000,300)
    }
    Start-Sleep -Seconds $IntervalSeconds
}

