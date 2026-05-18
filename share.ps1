param(
  [int]$Port = 8010,
  [string]$BindHost = "127.0.0.1",
  [string]$CloudflaredPath = ""
)

$python = Join-Path $PSScriptRoot ".healthee\Scripts\python.exe"

if (-not (Test-Path $python)) {
  Write-Error "Project virtual environment not found: $python"
  exit 1
}

if ([string]::IsNullOrWhiteSpace($CloudflaredPath)) {
  $candidates = @(
    (Join-Path $PSScriptRoot "cloudflared.exe"),
    "cloudflared.exe"
  )

  foreach ($candidate in $candidates) {
    $resolved = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($resolved) {
      $CloudflaredPath = $resolved.Source
      break
    }

    if (Test-Path $candidate) {
      $CloudflaredPath = (Resolve-Path $candidate).Path
      break
    }
  }
}

if ([string]::IsNullOrWhiteSpace($CloudflaredPath) -or -not (Test-Path $CloudflaredPath)) {
  Write-Error "cloudflared.exe not found. Download it first or pass -CloudflaredPath."
  exit 1
}

$uvicornCommand = "& '$python' -m uvicorn app.main:app --host $BindHost --port $Port"
$serverProcess = $null
$healthUrl = "http://$BindHost`:$Port/api/v1/health"

try {
  $serverProcess = Start-Process `
    -FilePath "powershell.exe" `
    -ArgumentList @("-NoProfile", "-Command", $uvicornCommand) `
    -WorkingDirectory $PSScriptRoot `
    -WindowStyle Hidden `
    -PassThru

  $ready = $false
  for ($attempt = 1; $attempt -le 20; $attempt++) {
    Start-Sleep -Seconds 1

    if ($serverProcess.HasExited) {
      Write-Error "Local web service failed to start."
      exit 1
    }

    try {
      Invoke-WebRequest -UseBasicParsing -Uri $healthUrl -TimeoutSec 2 | Out-Null
      $ready = $true
      break
    }
    catch {
    }
  }

  if (-not $ready) {
    Write-Error "Local web service did not become ready in time."
    exit 1
  }

  Write-Host "Local service running at http://$BindHost`:$Port"
  Write-Host "Quick Tunnel is temporary. Use the newest trycloudflare.com link only."
  Write-Host "If you close this window or restart sharing, the previous public link will stop working."
  Write-Host "Starting Cloudflare Tunnel. Press Ctrl+C to stop sharing."

  & $CloudflaredPath tunnel --url "http://$BindHost`:$Port"
}
finally {
  if ($serverProcess -and -not $serverProcess.HasExited) {
    Stop-Process -Id $serverProcess.Id -Force
  }
}
