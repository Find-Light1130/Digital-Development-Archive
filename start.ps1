param([switch]$NoData)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "=== AI Digital Education System ===" -ForegroundColor Cyan

if (-not $NoData -and -not (Test-Path "$root\data\school.db")) {
    Write-Host ">>> Generating mock data..." -ForegroundColor Yellow
    python "$root\data\raw_data_gen.py"
    if (-not $?) { Write-Host "Data generation failed!" -ForegroundColor Red; exit 1 }
    Write-Host "Data generated" -ForegroundColor Green
} else {
    Write-Host ">>> Skipping data generation" -ForegroundColor Gray
}

Write-Host ">>> Starting backend (port 8000)..." -ForegroundColor Yellow
$process = Start-Process -NoNewWindow python -ArgumentList "-m uvicorn backend.app:app --host 127.0.0.1 --port 8000" -WorkingDirectory $root -PassThru

Write-Host "Waiting for backend..." -NoNewline
$deadline = (Get-Date).AddSeconds(60)
$ready = $false
while ((Get-Date) -lt $deadline) {
    Start-Sleep 1
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $client.Connect("127.0.0.1", 8000)
        $ready = $true
        $client.Close()
        break
    } catch {
        $client.Dispose()
    }
    Write-Host "." -NoNewline
}
if (-not $ready) {
    $process.Kill()
    Write-Host ""
    Write-Host "Backend failed to start within 60s!" -ForegroundColor Red
    exit 1
}
Write-Host " OK" -ForegroundColor Green

try {
    Write-Host ">>> Starting frontend (port 3000)..." -ForegroundColor Yellow
    Push-Location "$root\frontend"
    npm run dev
    Pop-Location
} finally {
    if (-not $process.HasExited) { $process.Kill() }
}
