# dialogue-service

Python + FastAPI service that turns microphone audio into a spoken reply.

```
mic PCM ──► VAD ──► ASR ──► LLM (stream) ──► sentence split ──► GPT-SoVITS ──► TTS PCM
```

It speaks the protocol in [`../docs/protocol.md`](../docs/protocol.md) over a
loopback WebSocket, and it is the only component that holds the LLM API key.

## Stub mode — start here

Stub mode needs **no models, no GPU and no API key**. It exists so the Unity client
can be built against the real protocol before the heavy engines are wired up.

| Engine | Stub behaviour |
|---|---|
| VAD | energy threshold — a genuinely usable fallback, not just a mock |
| ASR | returns a canned Chinese phrase |
| LLM | streams a canned multi-sentence reply with realistic pacing |
| TTS | emits a tone at a declared sample rate, so playback and lip sync can be developed |

```powershell
cd H:\MGFR\dialogue-service
.\bootstrap.ps1     # creates .venv, installs core deps
.\run.ps1           # 127.0.0.1:8765, all engines = stub
```

Then, from another shell:

```powershell
.\.venv\Scripts\python.exe -m app.smoke_client
```

That connects, handshakes, sends fake mic audio, and prints every event the
service emits — including the interruption path.

## Real engines

Switch one engine at a time in `config.toml` (`[engines]`), and install the
matching deps from `requirements-engines.txt` into this venv. **None of the real
engines are verified yet** — each needs its own acceptance step.

- `asr = "sensevoice"` — sherpa-onnx SenseVoice INT8 on CPU. Needs a model
  directory supplied locally.
- `vad = "silero"` — Silero VAD.
- `llm = "openai"` — any OpenAI-compatible streaming endpoint.
- `tts = "gptsovits"` — the existing 小酒狐 configuration, **read-only**.

## Rules this service is built to

- **GPT-SoVITS is used only through an adapter** (constraint #6). Nothing under
  `F:\GPT-SoVITS` is modified. Streamed audio is parsed by its actual response
  format and sample rate — never hardcoded — and a partially written WAV is never
  forwarded as if complete.
- **Interruption stops playback, not necessarily inference** (constraint #7).
  GPT-SoVITS has no cancel endpoint, so synthesis stays serial, sentences stay
  short, and stale output is discarded by round id.
- **The service owns the key.** It is read from the environment or `config.toml`;
  neither `config.toml` nor any secret is committed.

## Layout

| Path | Purpose |
|---|---|
| `app/main.py` | FastAPI app: `/health`, `/ws` |
| `app/config.py` | TOML + environment configuration |
| `app/protocol.py` | Wire protocol: binary framing and control messages |
| `app/session.py` | Round lifecycle, state machine, cancellation |
| `app/pipeline.py` | VAD → ASR → LLM → TTS orchestration |
| `app/text.py` | Sentence splitting for short-sentence synthesis |
| `app/engines/` | Pluggable engines; `stub.py` is the default |
| `tests/` | Protocol and session tests |
