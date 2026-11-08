#Requires -Version 5.1
<#
.SYNOPSIS
  Create the dialogue-service virtual environment and install dependencies.

.DESCRIPTION
  Idempotent and non-destructive:
    * reuses an existing .venv instead of recreating it;
    * never overwrites an existing config.toml;
    * installs only the light requirements by default.

  The engine dependencies (sherpa-onnx, onnxruntime, torch) are NOT installed
  unless -WithEngines is passed, and none of them are verified yet. Stub mode
  needs none of them.

.PARAMETER Python
  The interpreter used to create the venv. Defaults to "python" on PATH.

.PARAMETER IndexUrl
  Package index to install from. Empty means "whatever pip is configured to use".
  Some machines pin a mirror in pip.ini that does not carry these packages; pass
  -IndexUrl https://pypi.org/simple to fall back to PyPI.

.PARAMETER WithEngines
  Also install requirements-engines.txt. Opt-in: large. SenseVoice ASR and Silero
  VAD are verified on CPU; torch is not installed.

.PARAMETER SkipTests
  Do not run the test suite at the end.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 -IndexUrl https://pypi.org/simple
#>
[CmdletBinding()]
param(
    [string]$Python = "python",
    [string]$IndexUrl = "",
    [switch]$WithEngines,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

$ServiceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir     = Join-Path $ServiceRoot ".venv"
$VenvPython  = Join-Path $VenvDir "Scripts\python.exe"

Write-Host "MGFR dialogue-service bootstrap" -ForegroundColor Cyan
Write-Host "  service root : $ServiceRoot"

# --- interpreter -----------------------------------------------------------
$pythonCmd = Get-Command $Python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    throw "Python not found on PATH as '$Python'. Install Python 3.12 (or 3.11+) and re-run."
}
$versionText = & $Python -c "import sys; print('%d.%d.%d' % sys.version_info[:3])"
if ($LASTEXITCODE -ne 0) { throw "'$Python' could not report its version." }
Write-Host "  interpreter  : $($pythonCmd.Source) ($versionText)"

$majorMinor = & $Python -c "import sys; print('%d.%d' % sys.version_info[:2])"
if ([version]$majorMinor -lt [version]"3.11") {
    Write-Warning "Python $majorMinor found; 3.11 or newer is required (tomllib, pydantic v2)."
}

# --- virtual environment ---------------------------------------------------
if (Test-Path $VenvPython) {
    Write-Host "  venv         : reusing $VenvDir"
} else {
    Write-Host "  venv         : creating $VenvDir"
    & $Python -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { throw "python -m venv failed (exit $LASTEXITCODE)." }
}

# --- dependencies ----------------------------------------------------------
# Shared argument list so an alternative index applies to every install below.
$pipArgs = @()
if ($IndexUrl) {
    $pipArgs += @("--index-url", $IndexUrl)
    Write-Host "  index        : $IndexUrl"
} else {
    Write-Host "  index        : pip default"
}
# PyPI intermittently drops the TLS connection from some networks; retry rather
# than fail the whole bootstrap on one broken handshake.
$pipArgs += @("--retries", "8", "--timeout", "30")

Write-Host "  pip          : upgrading"
& $VenvPython -m pip install @pipArgs --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed (exit $LASTEXITCODE)." }

Write-Host "  deps         : installing requirements.txt"
& $VenvPython -m pip install @pipArgs -r (Join-Path $ServiceRoot "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "dependency install failed (exit $LASTEXITCODE)." }

Write-Host "  deps         : installing requirements-dev.txt"
& $VenvPython -m pip install @pipArgs -r (Join-Path $ServiceRoot "requirements-dev.txt")
if ($LASTEXITCODE -ne 0) { throw "dev dependency install failed (exit $LASTEXITCODE)." }

if ($WithEngines) {
    Write-Host "  deps         : installing requirements-engines.txt" -ForegroundColor Yellow
    Write-Host "                 (sherpa-onnx / onnxruntime / torch — large)"
    & $VenvPython -m pip install @pipArgs -r (Join-Path $ServiceRoot "requirements-engines.txt")
    if ($LASTEXITCODE -ne 0) { throw "engine dependency install failed (exit $LASTEXITCODE)." }
} else {
    Write-Host "  deps         : engine dependencies skipped (pass -WithEngines to add them)"
}

# --- configuration ---------------------------------------------------------
$exampleConfig = Join-Path $ServiceRoot "config.example.toml"
$targetConfig  = Join-Path $ServiceRoot "config.toml"
if (Test-Path $targetConfig) {
    Write-Host "  config.toml  : already exists, left untouched"
} else {
    Copy-Item -Path $exampleConfig -Destination $targetConfig
    Write-Host "  config.toml  : created from config.example.toml" -ForegroundColor Green
}

# --- tests -----------------------------------------------------------------
$exitCode = 0
if (-not $SkipTests) {
    Write-Host "  tests        : running"
    Push-Location $ServiceRoot
    try {
        & $VenvPython -m pytest -q
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "the test suite failed (exit $LASTEXITCODE)."
            $exitCode = 1
        }
    } finally {
        Pop-Location
    }
}

Write-Host ""
Write-Host "Done." -ForegroundColor Cyan
Write-Host "  start the service : powershell -ExecutionPolicy Bypass -File .\run.ps1"
Write-Host "  smoke-test it     : .\.venv\Scripts\python.exe -m app.smoke_client"
Write-Host "  health check      : curl http://127.0.0.1:8765/health"
Write-Host ""
Write-Host "Stub mode needs no models, no GPU and no API key. Nothing has been"
Write-Host "verified against real engines or hardware yet (docs/acceptance.md)."
Write-Host ""
Write-Host "If the dependency install failed with 'No matching distribution found',"
Write-Host "your pip is pointed at a mirror that does not carry these packages:"
Write-Host "  powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 -IndexUrl https://pypi.org/simple"

exit $exitCode
