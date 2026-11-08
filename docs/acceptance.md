# Acceptance

## Three test modes — recorded separately, never substituted

Constraint #1 is explicit that these do not stand in for one another. Every
result must name the mode it came from.

| Mode | What it proves | What it does **not** prove |
|---|---|---|
| **Desktop preview** | Logic, protocol, layout, material look on a monitor | Anything about passthrough, stereo, or latency |
| **Simulated / loopback** | Protocol conformance, stub pipeline, interruption semantics, unit behaviour | Anything about ALVR, tracking, or real audio |
| **Headset run** | Passthrough compositing, both-eye correctness, tracking, real audio, end-to-end latency | — |

A passing desktop test is **not** evidence that passthrough works.

## Runs recorded

| Date | Mode | Stage | Result |
|---|---|---|---|
| 2026-10-17 | **Headset run** | ① | **Not a pass.** ALVR served SteamVR an HMD, two controllers and two full-skeletal hands for about 30 seconds, and the compositor rendered stereo frames before the HMD returned to standby. Passthrough was off and the headset microphone was off, so neither the room nor two-way audio was exercised. Details in [`environment.md`](environment.md) |
| 2026-10-17 | **Simulated** (`app/smoke_client.py`) | — | Protocol only: 4 rounds, 326 TTS frames at 24 kHz, barge-in allocating new round ids, 0 errors. Says nothing about Unity, audio devices or the headset |

## Stages

| Stage | Work | Passes when |
|---|---|---|
| **① ALVR base link** | Matched versions; simple object, passthrough, head and controller tracking, speaker and microphone | Room and object visible together; view moves correctly; audio works both ways; recovers after reconnect |
| **② Fixed character** | Offline conversion, material mapping, standing pose, placement, blink, lip sync | No missing textures; both eyes look identical; no obvious bone deformation; lip sync starts and stops with playback |
| **③ Voice loop** | Echo cancellation, VAD, ASR, LLM, GPT-SoVITS | Continuous conversation with no button presses; the character does not retrigger itself; after an interruption the old reply never plays again |
| **④ Concurrency and recovery** | Packaged build runs continuously; test network loss, service failure, re-centring, reconnect | No crash, no VRAM exhaustion, no audio backlog, no stale request bleeding into a new session |

**A failing base link is fixed before moving on.** Do not build stage ② on an
unverified stage ①.

### Stage ① is verified one variable at a time

The 2026-10-17 fault is still unattributed, because passthrough and the
microphone were switched on together and switched off together. Do not repeat
that. The order is:

1. **Plain VR, both features off.** Solid green background, one white object,
   head tracking, **physical controller** tracking, and a test tone. Run it long
   enough to be boring, then disconnect and reconnect the headset. This is the
   baseline that every later step is compared against.
2. **Microphone only.** Change that one setting. Everything else stays at the
   baseline. Confirm the PC actually receives audio from the headset.
3. **Passthrough only.** Change that one setting, with the microphone back off.
   Confirm the room composites and that the key holds in both eyes.
4. **Combine.** Only once 2 and 3 have each passed on their own.

One change per run. Record which setting changed and what happened. On any
failure, restore the last configuration that connected and say so, rather than
stacking a second change on top of a broken one. The known-good configuration
from 2026-10-17 is the rollback target.

Two things this stage does **not** establish. Bare-hand tracking is not tested
here; ALVR declares its hand devices whether or not real hand data is arriving,
so their presence in a log is not evidence. And a VRAM conclusion is not drawn
from the render resolution; it comes from measured usage.

## Metrics to record

Acceptance uses the **packaged** build, not the editor.

- **Frame rate** — target 72 Hz initially. Record application frame time, plus
  encode, network and decode latency.
- **Concurrency** — run character rendering and GPT-SoVITS together for at least
  **30 minutes**. Record VRAM peak, dropped frames, and audio backlog.
- **Scenarios** — short sentences, long sentences, pauses, repeated interruption,
  and the character speaking while the user stays silent.
- **Voice latency, in segments** — end of speech → recognition complete; → first
  LLM text; → first TTS audio. Recorded separately so the slow segment is
  identifiable.

## Explicitly not promised

No frame rate and no response time are promised in advance (constraint #9). The
72 Hz figure is an initial target to measure against, not a commitment.

## Per-stage prerequisites that are easy to forget

- **②** morph verification is per-morph: the five vowels and the blink are checked
  individually, and 照れ is a material morph, not a BlendShape.
- **②** `T_actor_jsspsi_body_01_N.png` must be mapped explicitly from `other tex/`.
- **③** the WebRTC APM / AEC3 Windows module is **unverified work**. "Mute the mic
  while speaking" does not satisfy this stage.
- **③** interrupting playback and stopping GPU inference are separate; the test is
  that late audio is discarded by round id, not that the server stopped computing.
- **④** re-centring the tracking space requires re-calibration before the placement
  test is valid.
