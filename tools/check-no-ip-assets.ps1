#Requires -Version 5.1
<#
.SYNOPSIS
  Fail if a character-IP asset, a voice weight, or a secret is staged in git.

.DESCRIPTION
  The 祀 model ReadMe forbids redistribution, and the 小酒狐 voice weights and the
  LLM key are private. This is the pre-commit guard that makes docs/asset-policy.md
  enforceable rather than aspirational.

  It inspects the git index (``git ls-files``) — that is what a commit would
  actually contain — and also reports whether the unpacked model folder is present
  on disk, which is expected but must never be tracked.

  Exit codes:
    0  clean
    1  violations found (do not commit)
    2  git is not available, so nothing could be checked

.PARAMETER Quiet
  Print nothing when clean.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\check-no-ip-assets.ps1
#>
[CmdletBinding()]
param(
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

# Each entry is a regex tested against the slash-normalised repo-relative path.
$rules = @(
    @{ Name = "Commercial plugin"; Pattern = '(?i)(^|/)(MagicaCloth2|AmplifyShaderEditor)(/|\.meta$)' }
    @{ Name = "Build or model data"; Pattern = '(?i)\.(exe|dll|zip|7z|rar|bin|motion|hpose|assetbundle|safetensors|pt|tflite)$' }
    @{ Name = "Private runtime data"; Pattern = '(?i)(^|/)(data|models|library|logs|usersettings|streamingassets)/|(^|/)(voice\.toml|embedding\.json)$|\.(sqlite3?|db|db-shm|db-wal|token|pem|pfx|p12)$' }
    @{ Name = "MMD source asset";   Pattern = '\.(pmx|pmd|vmd|vpd)$' }
    @{ Name = "Converted model";    Pattern = '\.(fbx|blend\d*)$' }
    @{ Name = "Voice weights";      Pattern = '\.(ckpt|pth|onnx)$' }
    @{ Name = "Audio sample";       Pattern = '\.(wav|mp3|flac|m4a)$' }
    @{ Name = "Texture folder";     Pattern = '(^|/)(textures|other tex)/' }
    @{ Name = "Local secrets";      Pattern = '(^|/)config\.toml$|(^|/)\.env(\.|$)|\.key$' }
    @{ Name = "Model drop folder";  Pattern = '^【明日方舟：终末地】祀_' }
)

# Resolve git robustly. A fresh install (`winget install Git.Git`) lands on the
# machine PATH, which shells that were already open do not pick up. A guard that
# reports "git is missing" when git is merely off PATH is a guard people learn to
# ignore, and that is worse than having no guard at all — so check the known
# install locations before giving up.
function Resolve-Git {
    $cmd = Get-Command git -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    $candidates = @()
    if ($env:ProgramFiles)        { $candidates += (Join-Path $env:ProgramFiles 'Git\cmd\git.exe') }
    if (${env:ProgramFiles(x86)}) { $candidates += (Join-Path ${env:ProgramFiles(x86)} 'Git\cmd\git.exe') }
    if ($env:LOCALAPPDATA)        { $candidates += (Join-Path $env:LOCALAPPDATA 'Programs\Git\cmd\git.exe') }
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) { return $candidate }
    }
    return $null
}

$git = Resolve-Git
if (-not $git) {
    Write-Host "check-no-ip-assets: git is not installed; nothing was checked." -ForegroundColor Yellow
    Write-Host "  install it with:  winget install Git.Git"
    exit 2
}

Push-Location $RepoRoot
try {
    $tracked = & $git ls-files
    if ($LASTEXITCODE -ne 0) {
        Write-Host "check-no-ip-assets: 'git ls-files' failed; is this a repository?" -ForegroundColor Yellow
        exit 2
    }
} finally {
    Pop-Location
}

$violations = @()
foreach ($path in $tracked) {
    if (-not $path) { continue }
    $normalised = $path -replace '\\', '/'
    foreach ($rule in $rules) {
        if ($normalised -match $rule.Pattern) {
            $violations += [pscustomobject]@{ Path = $normalised; Rule = $rule.Name }
            break
        }
    }
}

# Report (but do not fail on) the model folder sitting on disk: it is expected to
# be there and must simply stay untracked.
$modelFolders = Get-ChildItem -Path $RepoRoot -Directory -Filter '【明日方舟：终末地】祀_*' -ErrorAction SilentlyContinue

if ($violations.Count -eq 0) {
    if (-not $Quiet) {
        Write-Host "check-no-ip-assets: clean ($($tracked.Count) tracked files)." -ForegroundColor Green
        if ($modelFolders) {
            Write-Host "  model folder present and untracked: $($modelFolders[0].Name)" -ForegroundColor DarkGray
        }
    }
    exit 0
}

Write-Host ""
Write-Host "check-no-ip-assets: $($violations.Count) violation(s) staged" -ForegroundColor Red
Write-Host "These must never be committed (see docs/asset-policy.md):"
Write-Host ""
foreach ($v in $violations) {
    Write-Host ("  {0,-18} {1}" -f $v.Rule, $v.Path) -ForegroundColor Red
}
Write-Host ""
Write-Host "Fix by unstaging without deleting the local file:"
Write-Host "  git rm --cached -- <path>"
Write-Host "and add a matching pattern to .gitignore."
exit 1
