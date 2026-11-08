# unity-client

The Windows x64 Unity client for MGFR. It renders the converted character **祀**
against the chroma-key green background, plays the audio the dialogue service
sends, drives her mouth from the audio that is actually playing, and blinks on
her own.

It is no longer only a link test. The link test it grew out of is still here as
`SmokeTest`, and it stays as the regression baseline.

## Where this project actually stands

**Unity 6000.3.26f1** is installed at `H:\MGFR\Editor`, which is inside this
repository and gitignored (`.gitignore` has root-level `/Editor/` and
`/Unity Hub/` rules for exactly that reason). The project is configured and has
run:

| Setting | Value | Why |
|---|---|---|
| Colour space | **Linear** | read back from the player log |
| Render pipeline | **Built-in** | URP is deliberately not installed; see [Building](#building) |
| Graphics API | Direct3D11 | the only API the project enables |
| Scripting backend | **Mono** for builds | the IL2CPP C++ toolchain is incomplete on this machine |
| XR | OpenXR enabled, SteamVR as the runtime | head and controller poses arrive through it |

There is **no uGUI** in this project, so every panel is drawn with `OnGUI`.

## What is in here

| Path | What it is |
|---|---|
| `Assets/MGFR/Scripts/SmokeTestRig.cs` | The milestone ① regression baseline: camera, green background, cube, hand trackers, test tone, head follower. Builds itself at runtime |
| `Assets/MGFR/Scripts/XrDeviceFollower.cs` | Copies a head or controller pose onto a transform, reads its buttons, and carries the `-mgfr-noxr` desktop switch |
| `Assets/MGFR/Scripts/Character/SiCharacterLoader.cs` | Builds 祀 at runtime from the converted model binary |
| `Assets/MGFR/Scripts/Character/SiCharacterController.cs` | Placement, blink, mouth, expression keys and the on-screen panel |
| `Assets/MGFR/Scripts/Character/SiCharacterBootstrap.cs` | Builds the character scene in code: camera, light, character, preview controls, optional ground grid |
| `Assets/MGFR/Scripts/Character/SiModelData.cs` | The data contract for the converted model |
| `Assets/MGFR/Scripts/Character/SiDialogueLipSync.cs` | Drives the mouth from the level of the audio that is actually playing |
| `Assets/MGFR/Scripts/Dialogue/DialogueClient.cs` | The protocol client: handshake, session, text prompts, rounds, interrupt |
| `Assets/MGFR/Scripts/Dialogue/WebSocketConnection.cs` | RFC 6455 WebSocket over a raw socket, no third-party dependency |
| `Assets/MGFR/Scripts/Dialogue/DialogueAudioOutput.cs` | Streaming PCM playback with a bounded queue |
| `Assets/MGFR/Scripts/Dialogue/DialogueHud.cs` | The IMGUI panel: state, text, hotkeys, prompt field |
| `Assets/MGFR/Scripts/Diagnostics/SiSelfTest.cs` | The scripted end-to-end test and the soak run |
| `Assets/MGFR/Editor/MgfrEditorMenu.cs` | The `MGFR` menu: check setup, configure, create scenes, copy character data |
| `Assets/MGFR/Editor/MgfrBuild.cs` | The build entry point, its menu items and its exit codes |
| `Assets/MGFR/Editor/CharacterProbe.cs` | Checks the converted character binary offline |
| `ProjectSettings/ProjectVersion.txt` | Pins Unity **6000.3.26f1** |
| `Packages/manifest.json` | Pins OpenXR **1.18.0**, XR Management **4.7.0** and the built-in modules |

Both saved scenes are empty apart from one component. Every object is created in
code at runtime, so there is no hand-written scene YAML to drift out of step with
the code.

The character model itself is **not** in here. It is a local resource: the
converted binary is gitignored and is copied into `StreamingAssets` by
`MGFR > Copy Character Data`. See [`../docs/asset-policy.md`](../docs/asset-policy.md).

## Scenes

| Scene | What it is |
|---|---|
| `Assets/MGFR/Scenes/SiCharacter.unity` | The character scene: green background, 祀, preview camera, dialogue HUD |
| `Assets/MGFR/Scenes/SmokeTest.unity` | The milestone ① baseline: camera, cube, hand trackers, tone. Keep it working |

`SmokeTestRig` installs itself for every scene **except** `SiCharacter`, and
`SiCharacterBootstrap` installs itself **only** for `SiCharacter`. That pairing is
what stops the two rigs fighting over the camera. Both scenes have to be enabled
in Build Settings for a player build; `MgfrBuild` refuses to build without the
character scene, because a player that opens the smoke test instead of the
character is not the thing anyone asked for.

## Running the desktop preview

1. Start the dialogue service (see the root `README.md`).
2. Open `Assets/MGFR/Scenes/SiCharacter.unity` and press **Play**.

The character appears in front of the preview camera and the panel reports the
service state. Nothing here needs a headset. If SteamVR is running with a headset
attached, the camera hands over to the head pose **only once a real tracked pose
has been seen**; until then the keyboard and mouse keep control. XR being active
is not the same thing as a headset being worn, and the preview must not be taken
away by a runtime that merely started. On the command line, `-mgfr-noxr` stops
XR from coming up at all.

### Keys

| Key | Does |
|---|---|
| Right mouse drag | orbit the preview camera |
| Scroll wheel | zoom |
| Up / Down arrow | move the character forward and back |
| Z / X | strafe left and right |
| Left / Right arrow | turn the character |
| Page Up / Page Down | raise and lower her above the ground |
| `-` / `=` | scale her down and up |
| Home | reset position, turn, scale and ground height |
| B | blink once, by hand |
| 0 | clear the expression |
| 1 – 5 | drive the five vowel mouth shapes directly, without the service |
| 6 | toggle 照れ, a **material** morph, not a blend shape |
| G | toggle the wireframe ground grid. Off by default: in the headset it would sit in the middle of the real room |

The panel's own keys, active while the prompt field does not have focus:

| Key | Does |
|---|---|
| C / D | connect / disconnect |
| S / E | start / end the session |
| I | interrupt playback |
| P | ping |
| Return | send whatever is in the prompt field |

## The self test and the soak

The player can drive itself, which is how the desktop results in this project
were produced without a mouse:

```powershell
MGFR.exe -mgfr-selftest -mgfr-noxr -mgfr-seconds 60 -mgfr-rounds 3 `
         -mgfr-interrupt -mgfr-reconnect -mgfr-report selftest.txt
```

| Flag | Meaning |
|---|---|
| `-mgfr-selftest` | Run the scripted test instead of waiting for input |
| `-mgfr-noxr` | Stop XR and never query it: a guaranteed desktop-only run |
| `-mgfr-url <url>` | Service to connect to. Default `ws://127.0.0.1:8765/ws` |
| `-mgfr-prompt <text>` | The text sent each round |
| `-mgfr-seconds <n>` | Wall-clock limit |
| `-mgfr-rounds <n>` | Stop after n rounds. 0 runs until the clock runs out |
| `-mgfr-gap <n>` | Seconds between rounds |
| `-mgfr-interrupt` | Interrupt every even round and record how fast the mouth closes |
| `-mgfr-interrupt-after <n>` | How long the reply speaks before the interrupt |
| `-mgfr-reconnect` | Drop the socket mid-session during round 2 and reconnect |
| `-mgfr-report <path>` | Where the report goes |

It exits 0 when nothing failed and nothing timed out, and 1 otherwise, and it
writes a report either way: the model that was built, the handshake, every round,
the interrupt and reconnect evidence, a per-second table of frame time, VRAM,
queue depth and dropped audio, and a summary.

`tools/run-player.ps1` wraps this: it checks the player, the service and
GPT-SoVITS, reports what it found, and then launches. It changes nothing about
the machine.

## Building

`MGFR > Build > Windows Development Player (Mono)` from the menu, or from a
script:

```powershell
H:\MGFR\Editor\Unity.exe -batchmode -quit -accept-apiupdate `
  -projectPath H:\MGFR\unity-client -logFile build.log `
  -executeMethod MGFR.EditorTools.MgfrBuild.PlayerMono
```

Do **not** add `-nographics`: the build needs the graphics device.

The output is `Build/Windows/MGFR.exe`, and `Build/Windows/build-report.txt`
records what was built. Exit codes:

| Code | Meaning |
|---|---|
| 0 | built |
| 2 | the Windows standalone module is not installed |
| 3 | the IL2CPP toolchain is incomplete |
| 4 | the character shader was not found |
| 5 | the character scene is not enabled in Build Settings |
| 6 | the build failed |
| 7 | an exception |

**IL2CPP does not work on this machine.** The editor's Windows module is
installed, but the C++ toolchain behind it is not: no `vswhere.exe`, no Visual
Studio, no MSVC toolset, no `cl.exe`, no Windows 10/11 SDK include directory.
Having the IL2CPP module is not the same thing as having a C++ build environment,
and `MGFR > Check Setup` reports each missing piece by name. Until that is
resolved the builds use **Mono**; the project setting is restored after the build,
so a later switch to IL2CPP is a one-line change rather than a migration.

## What this does not test

- **The headset.** Everything in this file is measured on the desktop unless it
  says otherwise. Desktop frame time is not headset frame time, and neither is MR
  acceptance.
- **Bare-hand tracking.** ALVR declares its hand devices whether or not real hand
  data is arriving, so a device appearing in a log is not evidence.
- **Echo cancellation.** There is no working AEC module yet and the user is on the
  headset's built-in speakers, so barge-in during playback is unverified
  (constraint #8). Muting the microphone while the character speaks does not count
  as a working natural interruption.
- **VRAM headroom.** 12 GB has to cover VR rendering, NVENC and GPT-SoVITS at
  once, and the machine also has an AMD iGPU that must not be selected for VR or
  encoding.

## Three test modes, never substituted for each other

| Mode | What it proves | What it does not |
|---|---|---|
| Desktop preview / `-mgfr-selftest` | The code runs, the protocol works, the audio plays, the mouth follows it | Anything about VR, passthrough or stereo |
| Simulated (`dialogue-service/app/smoke_client.py`) | The protocol and the interruption path, without Unity | Anything about Unity, audio devices or the headset |
| Headset run | The actual product | — |

The service runs **real GPT-SoVITS TTS with a stub LLM**. SenseVoice ASR and
Silero VAD are real and verified on the CPU, but they are not on this path: the
text-debug entry point types a prompt straight to TTS, so the "recognition" is
skipped and the "reply" is simulated. Results from that path are labelled
simulation mode, and the text-debug entry point is not called a real AI
conversation.

## Version pinning

| Component | Pinned | Why that value |
|---|---|---|
| Unity | **6000.3.26f1** | `ProjectSettings/ProjectVersion.txt` |
| OpenXR plugin | **1.18.0** | the OpenXR release for 6000.3, and 1.18.0 is its only build that is not a pre-release |
| XR Plugin Management | **4.7.0** | the 4.7 line for 6000.3, and the newest version in the registry |
| URP | **not installed** | the project runs on Built-in and stays there this milestone |
| Input System | not pinned, resolved **1.20.0** | declared by the OpenXR plugin |
| XR Core Utils, Legacy Input Helpers | not pinned, resolved **2.6.0** and **2.1.13** | also declared by the OpenXR plugin |
| uGUI (`com.unity.ugui`) | **not installed** | every panel uses `OnGUI`; the built-in `com.unity.modules.ui` module carries only Canvas and CanvasRenderer |

`Packages/packages-lock.json` is committed on purpose: it is the resolver's
answer, so a "pinned" row above means the resolver agreed with the pin.

`../docs/environment.md` holds the project's "Pinned baseline versions" table.
A version string is not a measurement, and a frame time without one is not a
measurement either.
