$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$Port = if ($env:PORT) { $env:PORT } else { "8000" }
$Uvicorn = Join-Path $ProjectRoot ".venv\Scripts\uvicorn.exe"
$OutLog = Join-Path $ProjectRoot "uvicorn.out.log"
$ErrLog = Join-Path $ProjectRoot "uvicorn.err.log"

if (-not (Test-Path $Uvicorn)) {
    $env:UV_CACHE_DIR = Join-Path $ProjectRoot ".uv-cache"
    Set-Location $ProjectRoot
    uv sync --extra dev
}

$command = "cd /d `"$ProjectRoot`" && `"$Uvicorn`" app.main:app --host 127.0.0.1 --port $Port > `"$OutLog`" 2> `"$ErrLog`""
$process = Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", $command) -WindowStyle Hidden -PassThru
Start-Sleep -Seconds 3
Write-Output "Polymarket API started on http://127.0.0.1:$Port with PID $($process.Id)"
