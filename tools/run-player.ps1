<#
.SYNOPSIS
    Launch the MGFR desktop player after checking what it needs.

.DESCRIPTION
    One entry point for a morning check, or for any desktop run.

    It changes nothing about the machine. It does not touch ALVR, SteamVR, the
    network, the audio devices or any system default. It reads state, reports it,
    and then starts the player. Every failure is reported with the specific
    reason and a non-zero exit code, because "it did not start" is not a useful
    answer at 9am.

    The player needs the dialogue service on 127.0.0.1:8765. GPT-SoVITS on
    127.0.0.1:9880 is reported too: without it the service answers with its stub
    tone instead of real speech, which looks like a broken client.

.PARAMETER Player
    Path to MGFR.exe. Defaults to the delivered build.

.PARAMETER NoXr
    Force a desktop-only run. Passes -mgfr-noxr, which stops Unity's XR loader
    and keeps the keyboard and mouse in control.

.PARAMETER SelfTest
    Run the scripted test instead of the interactive preview.

.PARAMETER Seconds
    Self-test wall-clock limit, in seconds.

.PARAMETER Rounds
    Self-test round limit. 0 runs until the clock runs out.

.PARAMETER Prompt
    The text sent each round. Only passed through when you give it, so the
    player's own default is used otherwise (and no CJK text has to survive the
    console codepage).

.PARAMETER Report
    Where the self test writes its report.

.PARAMETER StartService
    Start the dialogue service if it is not already listening.

.EXAMPLE
    .\run-player.ps1
    .\run-player.ps1 -NoXr
    .\run-player.ps1 -SelfTest -Seconds 1800 -Report H:\MGFR\soak.txt
#>

[CmdletBinding()]
param(
    [string]$Player = "H:\MGFR-batch\unity-client\Build\Windows\MGFR.exe",
    [string]$Url = "ws://127.0.0.1:8765/ws",
    [switch]$NoXr,
    [switch]$SelfTest,
    [int]$Seconds = 120,
    [int]$Rounds = 0,
    [switch]$Interrupt,
    [switch]$Reconnect,
    [string]$Prompt = "",
    [string]$Report = "",
    [switch]$StartService
)

$ErrorActionPreference = "Continue"

function Say([string]$label, [string]$value) {
    "{0,-20} {1}" -f $label, $value
}

"MGFR player launcher"
(Say "started" (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
""

$exitCode = 0

# ---- the player binary -------------------------------------------------------

if (-not (Test-Path -LiteralPath $Player)) {
    Say "player" "NOT FOUND: $Player"
    ""
    "Build it first. From a shell:"
    ""
    "  H:\MGFR\Editor\Unity.exe -batchmode -quit -accept-apiupdate ``"
    "    -projectPath H:\MGFR\unity-client -logFile build.log ``"
    "    -executeMethod MGFR.EditorTools.MgfrBuild.PlayerMono"
    ""
    "or run MGFR > Build Player (Windows) in the editor."
    exit 2
}

$exe = Get-Item -LiteralPath $Player
Say "player" $exe.FullName
Say "built" $exe.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
Say "size" ("{0:N0} bytes" -f $exe.Length)
""

# ---- the two local services --------------------------------------------------

function Get-Listener([int]$port) {
    try {
        return Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction Stop
    } catch {
        return $null
    }
}

$service = Get-Listener 8765
if ($service) {
    $addresses = @($service | Select-Object -ExpandProperty LocalAddress -Unique)
    Say "dialogue service" ("listening on " + ($addresses -join ", ") + " (pid " + $service[0].OwningProcess + ")")

    # The service is meant to be local-only. Say so plainly if it is not, rather
    # than letting a wider bind go unnoticed.
    if ($addresses -contains "0.0.0.0" -or $addresses -contains "::") {
        "WARNING: the service is listening on every interface, not only 127.0.0.1."
        "         It is meant to be local-only. See docs\constraints.md."
    }
} else {
    Say "dialogue service" "NOT LISTENING on 127.0.0.1:8765"

    if ($StartService) {
        $runner = "H:\MGFR\dialogue-service\run.ps1"
        if (-not (Test-Path -LiteralPath $runner)) {
            Say "  start" "cannot start it: $runner does not exist"
            $exitCode = 1
        } else {
            Say "  start" "running $runner"
            Start-Process -FilePath "powershell.exe" `
                -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $runner) `
                -WorkingDirectory "H:\MGFR\dialogue-service" | Out-Null

            $deadline = (Get-Date).AddSeconds(30)
            while (-not (Get-Listener 8765) -and (Get-Date) -lt $deadline) {
                Start-Sleep -Milliseconds 500
            }

            if (Get-Listener 8765) {
                Say "  start" "the service came up"
            } else {
                Say "  start" "the service did not come up within 30s"
                "         Check dialogue-service\logs or start it by hand to see why."
                $exitCode = 1
            }
        }
    } else {
        "Start it first, or pass -StartService:"
        "  H:\MGFR\dialogue-service\run.ps1"
        $exitCode = 1
    }
}

$tts = Get-Listener 9880
if ($tts) {
    Say "GPT-SoVITS" ("listening on 127.0.0.1:9880 (pid " + $tts[0].OwningProcess + ")")
} else {
    Say "GPT-SoVITS" "NOT LISTENING on 127.0.0.1:9880"
    "WARNING: the service will answer with its stub tone instead of real speech."
    "         That still exercises the whole path, but it is not real TTS."
}
""

# ---- XR ----------------------------------------------------------------------

if ($NoXr) {
    Say "XR" "suppressed by -mgfr-noxr: desktop preview only"
} else {
    $steamvr = Get-Process -Name vrserver -ErrorAction SilentlyContinue
    if ($steamvr) {
        Say "XR" "SteamVR is running; the camera hands over once a head pose is tracked"
    } else {
        Say "XR" "SteamVR is not running; this will be a desktop preview"
        "The camera stays on the keyboard and mouse until a headset pose is tracked."
    }
}
""

if ($exitCode -ne 0) {
    "Not launching: fix the line above marked NOT LISTENING."
    exit $exitCode
}

# ---- launch ------------------------------------------------------------------

$arguments = @()
if ($SelfTest) {
    $arguments += "-mgfr-selftest"
    $arguments += @("-mgfr-seconds", $Seconds)
    $arguments += @("-mgfr-rounds", $Rounds)
    if ($Interrupt) { $arguments += "-mgfr-interrupt" }
    if ($Reconnect) { $arguments += "-mgfr-reconnect" }
    if ($Prompt -ne "") { $arguments += @("-mgfr-prompt", $Prompt) }
    if ($Report -eq "") {
        $Report = Join-Path (Split-Path -Parent $exe.FullName) "selftest.txt"
    }
    $arguments += @("-mgfr-report", $Report)
}
if ($NoXr) { $arguments += "-mgfr-noxr" }
$arguments += @("-mgfr-url", $Url)

Say "launching" ($exe.FullName + " " + ($arguments -join " "))
if ($SelfTest) { Say "report" $Report }
""

$process = Start-Process -FilePath $exe.FullName -ArgumentList $arguments -PassThru -Wait
Say "player exited" $process.ExitCode

if ($SelfTest) {
    if (Test-Path -LiteralPath $Report) {
        "Report: $Report"
        ""
        Get-Content -LiteralPath $Report | Select-Object -Last 20
    } else {
        "The player exited without writing $Report."
        $exitCode = 3
    }
}

if ($process.ExitCode -ne 0) { $exitCode = 3 }
exit $exitCode
