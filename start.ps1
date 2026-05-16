param(
  [int]$Port = 8000,
  [string]$BindHost = "127.0.0.1"
)

$python = Join-Path $PSScriptRoot ".healthee\Scripts\python.exe"

if (-not (Test-Path $python)) {
  Write-Error "Project virtual environment not found: $python"
  exit 1
}

& $python -m uvicorn app.main:app --host $BindHost --port $Port
