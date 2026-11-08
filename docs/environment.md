# Environment

Measured on this machine on **2026-10-17** by read-only inspection. Update the
"pinned baseline" table once the toolchain is installed (constraint #9).

## Hardware

| Item | Value |
|---|---|
| GPU | **NVIDIA GeForce RTX 5070, 12 GB** (12227 MiB per `nvidia-smi`) |
| GPU driver | 617.42 (`nvidia-smi`) / 32.0.16.1742 (`Win32_VideoController`) |
| Second adapter | AMD Radeon integrated graphics — present, must not be used for VR/encode |
| CPU | AMD Ryzen 7 9700X, 8 cores / 16 threads |
| RAM | 31 GB |

Note: `Win32_VideoController.AdapterRAM` reports 4 GB for the RTX 5070. That is a
known Windows reporting bug — trust `nvidia-smi`.

### VRAM budget — watch this early

12 GB has to hold, at the same time: the VR render, ALVR's encoder, and
GPT-SoVITS. Constraint #9 wants character rendering, TTS and the two concurrent
measured **separately**, so measure the concurrent peak in stage ③ rather than
discovering it in stage ④.

The integrated AMD adapter means the ALVR encoder must be **explicitly pinned to
the NVIDIA GPU**. Symptom of getting this wrong is a silent fallback and a much
worse experience than the numbers suggest.

## Software present

| Item | State |
|---|---|
| Python | 3.12.10 at `C:\Program Files\Python312` (venv + sqlite3 available) |
| pip | 25.0.1 (system); 26.2.1 in the service venv |
| PyPI reachable | yes, but **pip is configured for a mirror that does not carry these packages** — see below |
| git | **2.55.0.windows.5** at `C:\Program Files\Git\cmd\git.exe`. Installed 2026-10-17; shells opened before that do not have it on `PATH`, which is why `tools/check-no-ip-assets.ps1` resolves it explicitly |
| ALVR | **v20.14.1** at `E:\alvr_launcher_windows\installations\v20.14.1` |
| Steam client | `F:\SteamAPP\steam.exe`, library `F:\SteamAPP`. Other libraries: `X:`, `G:`, `Z:`, `H:\SteamLibrary` |
| SteamVR | **installed** at `F:\SteamAPP\steamapps\common\SteamVR`, and registered as the **active OpenXR runtime**: `HKLM\SOFTWARE\Khronos\OpenXR\1\ActiveRuntime` points at its `steamxr_win64.json`. This is constraint #2's arrangement, now confirmed rather than assumed |
| Unity Hub / Unity Editor | **installed, running.** Hub is at `H:\MGFR\Unity Hub`; the editor is **6000.3.26f1**, confirmed from `H:\MGFR\Editor\Unity.exe` (file version `6000.3.26.14582119`) and matching `unity-client/ProjectSettings/ProjectVersion.txt`. **Both are installed inside this repository**, because Hub's install root was pointed at `H:\MGFR`; `.gitignore` therefore carries root-level `/Editor/` and `/Unity Hub/` rules. The **Windows Build Support (IL2CPP)** module is present (`Editor\Data\PlaybackEngines\windowsstandalonesupport` and `Editor\Data\il2cpp`), so stage ④'s packaged build is unblocked. The project is opened from `H:\MGFR\unity-client`, not created from a template |

### pip and the package index

`pip config` on this machine sets
`global.index-url = https://pypi.tuna.tsinghua.edu.cn/simple`, which returns **no
versions at all** for `fastapi` and the rest. The failure reads as "package does
not exist" rather than "mirror is stale", which is worth knowing before going
looking for a network fault. `pypi.org` itself is reachable and serves them.

`bootstrap.ps1` therefore takes `-IndexUrl`; the working invocation is:

```powershell
powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 -IndexUrl https://pypi.org/simple
```

The mirror also intermittently drops TLS (`ConnectionResetError`, `SSLEOFError`);
the script retries rather than failing the whole bootstrap on one bad handshake.
Changing the pip config itself is the user's call, so it has not been touched.

## ALVR v20.14.1 — settings, and the 2026-10-17 headset session

Read from `E:\alvr_launcher_windows\installations\v20.14.1\session.json`, from
SteamVR's own logs, and from ALVR's `crash_log.txt`.

SteamVR keeps its config and logs at the **Steam root** (`F:\SteamAPP\config`,
`F:\SteamAPP\logs`), not inside the SteamVR folder. That is what
`%LOCALAPPDATA%\openvr\openvrpaths.vrpath` says, and it is where to look when
something misbehaves. `SteamVR\config` and `SteamVR\logs` do not exist and their
absence means nothing.

### How ALVR reaches SteamVR

ALVR is registered as an OpenVR **external driver**, not as a directory under
`SteamVR\drivers\`. There is no `SteamVR\drivers\alvr` and there should not be one.
The registration lives in `openvrpaths.vrpath`, which lists **two** drivers:

```json
"external_drivers" : [
    "E:/Pico/PICO Connect/openvr_driver/",
    "E:\\alvr_launcher_windows\\installations\\v20.14.1"
]
```

PICO Connect's driver (`name: "pico"`, `hmd_presence: ["*.*"]`) also claims an HMD,
so two drivers compete for the headset. ALVR won on 2026-10-17
(`ActualHMDDriver` is `alvr_server`).

**Do not uninstall it or delete the driver while the link is working.** If PICO
Connect ever has to be ruled out, exit the PICO Connect application first, and
only if that does not settle it, disable its SteamVR add-on for a single run.
Keep the exact way back and restore it the moment that run is over. A link that
connects is worth more than a tidy driver list.

### Gate items for milestone ①

Five defaults were wrong for what v1 needs. Four are fixed. **Two are still open**,
and both were briefly switched on and then rolled back:

| Setting | Was | Now | Needed | State |
|---|---|---|---|---|
| `openvr_config.refresh_rate` | `60` | `72` | `72` | done |
| `openvr_config.controllers_enabled` | `false` | `true` | `true` | done |
| `openvr_config.eye_resolution_width/height` | `800 × 900` | `2144 × 2144` | ≥ panel | done |
| `openvr_config.use_full_range_encoding` | `false` | `true` | `true` | done |
| `video.passthrough.content.variant` | `"Blend"` | `"RgbChromaKey"` | `"RgbChromaKey"` | done |
| `video.passthrough.enabled` | `false` | `false` | `true` | **open: no passthrough, so no MR** |
| `audio.microphone.enabled` | `false` | `false` | `true` | **open: no headset mic, so no button-free voice** |

`passthrough.enabled` and `microphone.enabled` were set to `true` at 23:18 and
returned to `false` at 23:39, together with the `mgfr`-named session backups.
**Codex made those changes**, not this project's scaffolding. After both were
turned back off and the headset's ALVR app was restarted, ordinary streaming
worked again, so the current combination is known-good. **Milestone ① cannot pass
in this state.**

Which of the two caused the fault is **not yet determined**, and the answer
matters. If passthrough was responsible, the chroma-key approach needs
rethinking; if the microphone was, the problem is narrower. Because they were
changed together, neither is isolated. Leave this configuration alone until the
single-item tests in [`acceptance.md`](acceptance.md) can separate them, and keep
a copy of the current session profile as the rollback target.

`audio.game_audio.enabled` is `true`, so the character's voice has a path to the
headset speakers, but `game_audio.device.set` is `false`, so ALVR picks the output
device itself rather than being pinned to one. With the AMD iGPU present, pin it
explicitly.

### The chroma key is green, and it is not the green Unity will emit

The `RgbChromaKey` block is configured as `red 0, green 255, blue 0` with
`distance_threshold 85` and `feathering 0.05`. Two consequences that are cheap to
state and expensive to discover:

- Unity's background must land on **exactly RGB(0, 255, 0) in the encoded frame**.
  A linear-space URP pipeline, any post-processing, tone mapping or anti-aliasing
  will move it off that value. This is the "audit colour conversion" half of
  constraint #3.
- `use_full_range_encoding` is now **`true`** and `encoding_gamma` is **`1.0`**, so
  the limited-range trap that used to be here is gone. That removes one way for
  "the material is pure green" to differ from "the encoded pixel is the keyed
  colour", but not the others. Verify the keyed result, not the material colour.

`distance_threshold` is generous and `feathering` is small, so the key is
reasonably tolerant. But a hair strand is not a background pixel, and thin
semi-transparent geometry is exactly what constraint #3 warns about. Check it in
both eyes.

### Encoder adapter

`openvr_config.adapter_index` is **`0`**. This machine has an AMD integrated GPU
alongside the RTX 5070, and index 0 is not guaranteed to be the NVIDIA part. The
VRAM note above already says the encoder must be pinned to NVIDIA; this is the
field that does it. Verify by name, not by assuming the numbering.

`encoder_quality_preset` is `0` and `nvenc_quality_preset` is `5`.
`eye_resolution_width/height` are **2144 × 2144** and bitrate is a constant
**30 Mbps**.

### What the 2026-10-17 headset session actually proved

This is a **headset run**, and the only evidence of its kind so far. It is not a
pass of milestone ①, but the link itself is real:

- SteamVR loaded ALVR: `Using existing HMD alvr_server.1WMHH000X00000`
  (`vrserver.txt`, 23:22:49).
- At **23:40:29** the driver activated an HMD, both controllers
  (`1WMHH000X00000_Controller_Left/Right`) and both full-skeletal hand devices
  (`ALVR_Left_Hand_Full_Skeletal`, `ALVR_Right_Hand_Full_Skeletal`).

  **Do not read the hand devices as proof that bare-hand tracking works.** ALVR
  declares that device pair as part of its device set, so their activation says
  the driver started, not that the headset was tracking fingers. Whether real
  hand data was ever sent was not checked. Milestone ① verifies the **physical
  controllers** first; bare hands are a separate question with a separate test.
- `vrcompositor.txt` shows stereo distortion surfaces and frames being handed to
  the driver in that same second, and a chaperone commit at 23:40:30.
- `steamvr.vrsettings` records `LastKnown.ActualHMDDriver = "alvr_server"`, with
  `HMDManufacturer "Oculus"` and `HMDModel "Miramar"`. ALVR presents a Quest 2, so
  SteamVR input bindings are Oculus Touch, not PICO. Do not read the word
  "Oculus" as evidence that an Oculus device was involved.
- The HMD was back in standby by 23:40:59, about **30 seconds** after activation,
  and no ALVR client was connected when this was written. Treat the link as "it
  can work", not "it works".

**Effective render target: 2624 × 2624 per eye.** ALVR is configured for
2144 × 2144, but `vrcompositor.txt` records `Raw ideal render target scale = 4.38`
clamped to `1.5x total area`, giving
`GetRecommendedRenderTargetSize for current app: 2624x2624`. SteamVR supersamples
on top of ALVR's resolution. Check `steamvr.vrsettings`' `supersampleScale` (`5`)
and `gpuSpeedRenderTargetScale` (`1.5`) before believing any frame time.

Pixel count is **not** a VRAM measurement. 2624 × 2624 × 2 eyes at 72 Hz is about
0.99 Gpx/s of throughput, but the same throughput can cost very different amounts
of memory depending on how many render targets are alive, whether MSAA is on, and
how many intermediates the pipeline keeps. Do not infer that 12 GB is enough, or
is not enough, from that number. Record the real figures from the running
application: `nvidia-smi` VRAM peak, application frame time, and dropped frames.
That is what constraint #9 asks for.

### The handshake failures

`crash_log.txt` in the ALVR install directory is an error log, not a crash of
ALVR. It holds **131 aborted handshakes** at roughly 1.5 s intervals between
23:11:27 and 23:37:07: `WSAECONNABORTED (10053)` and `WSAECONNRESET (10054)`,
from two client identities, the paired Pico 4 and an untrusted `8438.client`
with `display_name: Unknown`. They stopped once the link came up. Two things to
remember: an untrusted client keeps retrying, and the retry loop is fast enough
to fill a log in half an hour.

## Local (never committed) resources

| Resource | Path |
|---|---|
| Character model | `H:\MGFR\【明日方舟：终末地】祀_by_茶叶味香皂_ea803c2429de15a49d2b457b9cea9738\祀.pmx` |
| Model textures | `…\textures\` (8 files) and `…\other tex\` (~60 files) |
| GPT-SoVITS | `F:\GPT-SoVITS` (v2pro-20250604-**nvidia50** build), `api_v2.py`, `ref_xiaojiuhu.wav` |
| 小酒狐 voice | `F:\TTS\_xiaojiuhu_check\小酒狐语音包` (v2Pro GPT + SoVITS weights) |

The GPT-SoVITS install is a **read-only** dependency (constraint #6): its models,
dependencies and tuning scripts are not modified. It runs in its own environment;
the dialogue service gets its own venv and talks to it over HTTP.

The `nvidia50` build is the right one for this GPU. Note that RTX 5070 is a
Blackwell part, so any PyTorch used in *our* venv must be a Blackwell-capable
build (cu128 or newer) — this is one more reason to keep the engines in a separate
venv from GPT-SoVITS' runtime.

## Pinned baseline versions

Fill in as each is installed. A version counts as verified only once it has run.

| Component | Version | Notes |
|---|---|---|
| Unity | **6000.3.26f1** — installed and run | Unity 6.3 LTS is the 6000.3.x line, and 6000.3.26f1 is its latest patch as of 2026-10-18. `H:\MGFR\Editor\Unity.exe` reports `6000.3.26.14582119`, so the pin is confirmed on disk. The smoke test ran in the headset on 2026-10-18 and the packaged desktop player has run since, so the install is more than a version string. No headset frame time has been measured, so there is still no measured frame time behind this pin |
| Unity OpenXR plugin | **1.18.0** — resolved and run | 1.18 is the OpenXR release for 6000.3, and 1.18.0 is its only build that is not a pre-release. Pinned in `unity-client/Packages/manifest.json`, confirmed at exactly that version in `packages-lock.json`, and exercised by the headset run on 2026-10-18 (head and controller poses arrived through SteamVR's OpenXR runtime) |
| Unity XR Plugin Management | **4.7.0** — resolved and run | 4.7 is the XR Management release for 6000.3, and 4.7.0 is the newest version in Unity's registry. Pinned in the same manifest, confirmed at that exact version in `packages-lock.json`, and exercised by the same headset run |
| URP | deliberately **not installed** | The 6000.3 line is URP 17.3, but this project runs on the **Built-in** pipeline and stays there for this milestone. The character, the chroma-key background and the smoke test all work as they are, and migrating the pipeline would invalidate the smoke test as a regression baseline. There is no URP entry in `packages-lock.json`, and that is on purpose |
| Unity Input System | **1.20.0** — resolved, deliberately not pinned | Pulled in as a dependency of the OpenXR plugin, which asks for 1.6.3 or newer; the resolver picked 1.20.0. Left unpinned so it tracks the editor |
| ALVR — PC | **20.14.1** | `E:\alvr_launcher_windows\installations\v20.14.1`; loaded by SteamVR on 2026-10-17 |
| ALVR — headset | _TBD_ | must match 20.14.1 exactly. The launcher side-loaded an APK with `platform-tools\adb.exe` on 2026-10-17, but the installed version was never read back. Read it with `adb shell dumpsys package` before trusting the pair |
| SteamVR | 2.17.10 | from `steamvr.vrsettings` `lastVersionNotice`; appmanifest 250820 buildid `25330290`. `vrserver.exe` carries a stale `1.1.1` stamp, so do not read the version off the binary |
| PICO system | _TBD_ | |
| GPU driver | 617.42 | already recorded |
| GPT-SoVITS | v2pro-20250604-nvidia50 | present and **in use**. The service's GPT-SoVITS adapter has produced real speech through `dialogue-service`, and the Unity client has played that audio back and lip-synced to it (32000 Hz, mono, s16le). `F:\GPT-SoVITS` is called read-only through the adapter; its models, dependencies and launch scripts are never modified |
| ASR — SenseVoice INT8 | sherpa-onnx 1.13.8, onnxruntime 1.31.0 | **verified real on the CPU**, 2026-10-18. The model's own `zh.wav` transcribed to Chinese and the 小酒狐 reference clip to Japanese, through the service's adapter. Models live in the gitignored `dialogue-service/models/`; the packages are installed into the service venv only and never into GPT-SoVITS' runtime (constraint #6) |
| VAD — Silero v5 | onnxruntime 1.31.0 | **verified real on the CPU**, 2026-10-18, after fixing a genuine bug: the ONNX graph takes **576** samples per call — the previous window's last 64 plus this window's 512 — and feeding the bare 512 returned a near-zero probability for audible speech *without raising an error*. Speech start and speech end both fire on local audio now. See the module docstring in `app/engines/vad_silero.py` |
| LLM | — | **not configured, deliberately.** This project supplies no address, model or key, so the reply text is a stub. Keys are not hunted for in other projects, and this path is not called real AI dialogue |
