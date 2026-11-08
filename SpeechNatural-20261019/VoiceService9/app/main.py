"""FastAPI application: ``/health`` plus the WebSocket protocol endpoint.

The service holds no state outside a connection, and nothing is persisted — v1 is
current-session memory only. One WebSocket carries both control messages and PCM,
so the transport preserves their relative order (see ``docs/protocol.md``).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any, Awaitable, Callable

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from . import __version__, protocol
from .audio import pcm_s16le_to_float32, resample_linear
from .config import Config
from .engines.base import EngineUnavailable, VadEvent
from .engines.factory import Engines, build_all
from .protocol import AudioKind, ControlMessage, ErrorCode, InterruptReason, State
from .session import Session

logger = logging.getLogger(__name__)

#: Bound on the outbound queue. A client that stops reading is dropped rather than
#: allowed to make the service buffer audio without limit.
OUT_QUEUE_MAX = 256

#: Audio kept from before a confirmed speech onset, so the first syllable is not
#: clipped by the VAD's confirmation delay.
PREROLL_MS = 300

Handler = Callable[["Connection", ControlMessage], Awaitable[None]]


class Connection:
    """One WebSocket client: handshake, inbound dispatch, outbound writer."""

    def __init__(self, ws: WebSocket, config: Config, engines: Engines) -> None:
        self.ws = ws
        self.config = config
        self.engines = engines
        self.out: asyncio.Queue[Any] = asyncio.Queue(maxsize=OUT_QUEUE_MAX)
        self.session = Session(engines=engines, config=config, out=self.out)

        self.hello_done = False
        self.started = False

        self._utterance: list[np.ndarray] = []
        self._utterance_samples = 0
        self._writer: asyncio.Task | None = None

    # -- lifecycle ---------------------------------------------------------

    async def run(self) -> None:
        self._writer = asyncio.create_task(self._write_loop(), name="ws-writer")
        try:
            while True:
                message = await self.ws.receive()
                if message["type"] == "websocket.disconnect":
                    break
                text = message.get("text")
                if text is not None:
                    await self._on_control(text)
                elif message.get("bytes") is not None:
                    await self._on_audio(message["bytes"])
        except WebSocketDisconnect:
            pass
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - a bad client must not crash the server
            logger.exception("connection failed")
        finally:
            await self._shutdown()

    async def _shutdown(self) -> None:
        await self.session.close()
        writer = self._writer
        self._writer = None
        if writer is not None and not writer.done():
            writer.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await writer

    async def _write_loop(self) -> None:
        """Sole writer for the socket, so sends never interleave."""
        try:
            while True:
                item = await self.out.get()
                if isinstance(item, bytes):
                    await self.ws.send_bytes(item)
                else:
                    await self.ws.send_text(item)
        except asyncio.CancelledError:
            raise
        except (WebSocketDisconnect, RuntimeError):
            pass

    # -- inbound -----------------------------------------------------------

    async def _on_control(self, text: str) -> None:
        try:
            message = protocol.loads(text)
        except protocol.ProtocolError as exc:
            await self.session.emit_json(protocol.error(None, ErrorCode.BAD_FRAME, str(exc)))
            return

        handler = _HANDLERS.get(message.type)
        if handler is None:
            logger.debug("ignoring unknown control message %r", message.type)
            return
        await handler(self, message)

    async def _on_audio(self, data: bytes) -> None:
        if not self.started:
            return  # audio before session.start is meaningless

        try:
            frame = protocol.decode_audio_frame(data)
        except protocol.ProtocolError as exc:
            await self.session.emit_json(protocol.error(None, ErrorCode.BAD_FRAME, str(exc)))
            return

        if frame.kind is not AudioKind.MIC:
            # The service never accepts client-side TTS audio.
            return

        current = self.session.current_round
        if frame.round and current is not None and frame.round != current.id:
            # Informational only. The service attributes microphone audio to its
            # own current round regardless, so the client needs no round
            # bookkeeping — but a persistent mismatch is worth seeing in the log.
            logger.debug(
                "mic frame echoes round %s while the service is on round %s",
                frame.round,
                current.id,
            )

        rate = self.config.audio.mic_sample_rate
        samples = pcm_s16le_to_float32(frame.payload, frame.channels)
        if frame.sample_rate != rate:
            samples = resample_linear(samples, frame.sample_rate, rate)

        self._append_utterance(samples, rate)

        event = self.engines.vad.push(samples, rate)
        if event is VadEvent.SPEECH_START:
            round_ = await self.session.on_speech_start()
            self._trim_utterance(PREROLL_MS, rate)
            await self.session.set_state(State.LISTENING, round_)
        elif event is VadEvent.SPEECH_END:
            utterance = self._take_utterance()
            if utterance.size:
                await self.session.begin_recognition(utterance, rate)

    # -- utterance buffer --------------------------------------------------

    def _append_utterance(self, samples: np.ndarray, rate: int) -> None:
        if samples.size == 0:
            return
        self._utterance.append(samples)
        self._utterance_samples += samples.size

        cap = int((self.config.vad.max_utterance_ms + PREROLL_MS) * rate / 1000)
        while self._utterance_samples > cap and len(self._utterance) > 1:
            self._utterance_samples -= self._utterance.pop(0).size

    def _trim_utterance(self, ms: int, rate: int) -> None:
        """Drop everything but the last ``ms`` milliseconds."""
        keep = int(ms * rate / 1000)
        while self._utterance and self._utterance_samples > keep:
            self._utterance_samples -= self._utterance.pop(0).size

    def _take_utterance(self) -> np.ndarray:
        if not self._utterance:
            return np.empty(0, dtype=np.float32)
        joined = np.concatenate(self._utterance)
        self._reset_utterance()
        return joined

    def _reset_utterance(self) -> None:
        self._utterance = []
        self._utterance_samples = 0


# ---------------------------------------------------------------------------
# Control handlers
# ---------------------------------------------------------------------------


async def _handle_hello(conn: Connection, message: ControlMessage) -> None:
    conn.hello_done = True
    tts = conn.engines.tts
    # 0 means "not yet known" — the real rate is announced on each tts.start.
    rate = getattr(tts, "last_sample_rate", None) or getattr(tts, "sample_rate", 0) or 0
    await conn.session.emit_json(
        protocol.hello_ack(
            server_version=__version__,
            tts_sample_rate=int(rate),
            tts_channels=int(getattr(tts, "channels", 1)),
            engines=conn.engines.names(),
            max_concurrent_tts=int(conn.config.tts.max_concurrent),
            round_=0,
        )
    )


async def _handle_session_start(conn: Connection, message: ControlMessage) -> None:
    await conn.session.reset_for_new_session()
    conn._reset_utterance()
    conn.started = True
    round_ = conn.session.new_round()
    await conn.session.set_state(State.LISTENING, round_)


async def _handle_session_end(conn: Connection, message: ControlMessage) -> None:
    conn.started = False
    await conn.session.interrupt(InterruptReason.SESSION_END)
    conn.session.current_round = None
    conn._reset_utterance()
    conn.engines.vad.reset()
    await conn.session.emit_json(protocol.state(0, State.IDLE))


async def _handle_interrupt(conn: Connection, message: ControlMessage) -> None:
    await conn.session.interrupt(InterruptReason.CLIENT_REQUEST)
    conn._reset_utterance()
    round_ = conn.session.new_round()
    await conn.session.set_state(State.LISTENING, round_)


async def _handle_ping(conn: Connection, message: ControlMessage) -> None:
    await conn.session.emit_json(protocol.pong(message.payload.get("t")))


async def _handle_playback_started(conn: Connection, message: ControlMessage) -> None:
    # Logged rather than acted on: the service does not gate on playback, it only
    # records the client's own view of when audio began.
    logger.debug("round %s: client started playback", message.round)


async def _handle_playback_finished(conn: Connection, message: ControlMessage) -> None:
    logger.debug(
        "round %s: client finished playback (%s)",
        message.round,
        message.payload.get("reason"),
    )


async def _handle_text_input(conn: Connection, message: ControlMessage) -> None:
    """Typed text in place of speech: skip ASR, go straight to the LLM.

    A missing or blank ``text`` is not fatal — it is reported as a recoverable
    ``BAD_FRAME`` and the session carries on, exactly as for any other malformed
    control message. No round is allocated, so the current round is untouched.
    """
    if not conn.started:
        await conn.session.emit_json(
            protocol.error(None, ErrorCode.BAD_FRAME, "text.input before session.start")
        )
        return
    raw = message.payload.get("text")
    text = raw.strip() if isinstance(raw, str) else ""
    if not text:
        await conn.session.emit_json(
            protocol.error(
                None, ErrorCode.BAD_FRAME, "text.input requires a non-empty 'text'"
            )
        )
        return
    await conn.session.begin_text_turn(text)


_HANDLERS: dict[str, Handler] = {
    "hello": _handle_hello,
    "session.start": _handle_session_start,
    "session.end": _handle_session_end,
    "text.input": _handle_text_input,
    "interrupt": _handle_interrupt,
    "ping": _handle_ping,
    "playback.started": _handle_playback_started,
    "playback.finished": _handle_playback_finished,
}


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------


def create_app(config: Config | None = None) -> FastAPI:
    cfg = config or Config.load()

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI):
        # Engines are built once at startup. A failure is recorded rather than
        # raised, so /health can report it and the operator sees a clear reason
        # instead of a service that refuses to boot.
        try:
            app.state.engines = build_all(cfg)
            app.state.engine_error = None
            logger.info("engines ready: %s", app.state.engines.names())
        except EngineUnavailable as exc:
            app.state.engines = None
            app.state.engine_error = str(exc)
            logger.error("engines unavailable: %s", exc)
        try:
            yield
        finally:
            engines = app.state.engines
            if engines is not None:
                for engine in (engines.llm, engines.tts):
                    close = getattr(engine, "aclose", None)
                    if close is not None:
                        await close()
            app.state.engines = None

    app = FastAPI(title="MGFR dialogue service", version=__version__, lifespan=lifespan)
    app.state.config = cfg
    app.state.engines = None
    app.state.engine_error = None

    @app.get("/health")
    async def health() -> dict[str, Any]:
        engines: Engines | None = app.state.engines
        return {
            "status": "ok" if engines is not None else "degraded",
            "version": __version__,
            "protocolVersion": protocol.PROTOCOL_VERSION,
            "speechRevision": "natural-phrases-v5",
            "speechQuality": {"verifiedPhrases": getattr(engines.tts, "verified_phrases", 0), "retries": getattr(engines.tts, "quality_retries", 0)} if engines else {},
            "configSource": str(cfg.source_path) if cfg.source_path else None,
            "engines": engines.names() if engines is not None else cfg.engines.as_dict(),
            "engineError": app.state.engine_error,
        }

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket) -> None:
        await ws.accept()
        engines: Engines | None = app.state.engines
        if engines is None:
            await ws.send_text(
                protocol.dumps(
                    protocol.error(
                        None,
                        ErrorCode.ENGINE_UNAVAILABLE,
                        app.state.engine_error or "engines are not available",
                        recoverable=False,
                    )
                )
            )
            await ws.close(code=1011)
            return
        await Connection(ws, cfg, engines).run()

    return app


app = create_app()
