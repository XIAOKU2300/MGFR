#Requires -Version 5.1
<#
.SYNOPSIS
  Start the dialogue service on the loopback interface.

.DESCRIPTION
  Runs uvicorn from the service's own virtual environment. The bind address
  defaults to 127.0.0.1: the service holds the LLM key server-side, and there is
  no reason to expose it on the network for a single-headset setup.

.PARAMETER BindHost
  Address to bind. Defaults to 127.0.0.1.

.PARAMETER Port
  Port to bind. Defaults to 8765.

.PARAMETER Config
  Path to a config.toml. Sets MGFR_CONFIG for this process only; the default is
  dialogue-service\config.toml.

.PARAMETER Reload
  Restart on source changes. Convenient while developing the service.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\run.ps1

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\run.ps1 -Port 9000 -Reload
#>
[CmdletBinding()]
param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8765,
    [string]$Config = "",
    [switch]$Reload
)

$ErrorActionPreference = "Stop"

$ServiceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython  = Join-Path $ServiceRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    throw "No virtual environment at $ServiceRoot\.venv. Run .\bootstrap.ps1 first."
}

if ($Config) {
    if (-not (Test-Path $Config)) { throw "Config file not found: $Config" }
    $env:MGFR_CONFIG = (Resolve-Path $Config).Path
    Write-Host "config : $env:MGFR_CONFIG"
} else {
    $default = Join-Path $ServiceRoot "config.toml"
    if (Test-Path $default) {
        Write-Host "config : $default"
    } else {
        Write-Host "config : none (built-in defaults; stub engines)" -ForegroundColor Yellow
    }
}

Write-Host "listen : http://${BindHost}:${Port}  (ws://${BindHost}:${Port}/ws)"
Write-Host "health : http://${BindHost}:${Port}/health"
Write-Host ""

$uvicornArgs = @(
    "-m", "uvicorn", "app.main:app",
    "--host", $BindHost,
    "--port", "$Port",
    "--log-level", "info"
)
if ($Reload) { $uvicornArgs += "--reload" }

Push-Location $ServiceRoot
try {
    & $VenvPython @uvicornArgs
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
