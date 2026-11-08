# Binding implementation constraints

These are not suggestions. Each one came from a specific, checked observation,
and each has a concrete consequence for the code. If a change would violate one,
stop and raise it instead of working around it.

---

### 1. Minimal on-device validation before extending the project

First get **ALVR + SteamVR** running with *solid background + a cube + head/hand
tracking + two-way audio*, and confirm a plain PICO 4 composites passthrough
correctly.

**Consequence:** desktop preview, simulated tests and headset runs are recorded
**separately** and never substitute for one another. A green desktop test is not
evidence that passthrough works.

---

### 2. Keep the PC and headset OpenXR runtimes distinct

The Windows Unity app uses **SteamVR's** OpenXR runtime. Passthrough is handled by
the **ALVR client on the headset**.

**Consequence:** v1 adds no PICO Android SDK to the Windows client, and assumes
SteamVR does **not** expose headset cameras or room depth to the PC app. Any design
that needs a camera or depth feed from the PC side is out of scope.

---

### 3. Chroma key is not an alpha channel

Unity outputs a stable solid background; ALVR keys it out.

**Consequence:** audit post-processing, colour conversion and anti-aliasing for
anything that shifts the background colour. Verify hair strands, eyelashes, cloth
and UI are not accidentally keyed out. **Both eyes.** This is a device-only check.

---

### 4. Keep the original model; write conversion output elsewhere

Statically confirmed: ~73,000 triangles, 14 materials, 828 bones, 41 morphs,
506 rigid bodies, 682 constraints. Unity rendering is **not** yet verified.

**Consequence:** v1 disables full MMD physics simulation. Do **not** delete bones
or edit the original PMX to make things easier. Conversion output goes to a
separate gitignored directory. Optimise against measurements, not guesses.

---

### 5. Classify morphs individually during conversion

41 morphs, of which **40 are vertex morphs and 照れ is a material morph** — it is
not safe to assume all of them become Unity BlendShapes.

**Consequence:** verify the five vowels and the blink morph one by one. The file
`textures/T_actor_jsspsi_body_01_N.png` is missing from `textures/`; its same-named
counterpart is in `other tex/` and must be **mapped explicitly** during conversion.

---

### 6. Reuse GPT-SoVITS strictly through an adapter

Prefer the existing 小酒狐 configuration. **Do not modify** anything under
`F:\GPT-SoVITS` — not its models, dependencies, or tuning scripts.

**Consequence:** parse streamed audio by its **actual response format and sample
rate**; never hardcode them. Never hand an incomplete stream to Unity as if it were
a finished WAV.

---

### 7. Interrupting playback and stopping inference are two different things

The inspected `api_v2.py` has **no request-cancellation endpoint**. Closing the
HTTP connection does not mean GPU inference has stopped.

**Consequence:** keep TTS serial and synthesise in short sentences so a stale
request blocks for a bounded time. On interruption: stop playback immediately,
clear the queue, and **discard late audio by round id**. The protocol carries round
ids on every control message and every audio frame for exactly this reason.

---

### 8. Validate echo handling before trusting button-free voice

The user is on the headset's built-in speakers. The Windows module for
**WebRTC APM / AEC3 has not been built or integrated**, so no working DLL can be
assumed to exist. The real played audio must be used as the reference signal, and
streaming latency has to be accounted for.

**Consequence:** "mute the microphone while the character speaks" does **not** count
as a completed barge-in-capable conversation. Treat the AEC module as unverified
work with its own acceptance step.

---

### 9. Pin baseline versions and measure performance in stages

**Consequence:** record the versions of Unity, the OpenXR plugin, both ALVR ends,
the PICO system and the GPU driver. Test character rendering, TTS, and the two
running concurrently **separately**. Record frame time, VRAM and per-segment voice
latency. **Promise no frame rate and no response time in advance.**

---

### 10. Separate open-source code from character resources

The model ReadMe forbids redistribution (二次配布).

**Consequence:** the original model, its textures, conversion output, voice weights
and keys are excluded from version control **before the first commit**. v1 scope
stays: passthrough placement, basic standing pose, blinking, lip sync, current-session
dialogue. Emotion/motion, depth occlusion and multiple characters are later work.

See [`asset-policy.md`](asset-policy.md) for how this is enforced.
