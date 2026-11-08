"""Smoke client — drives the whole protocol with no Unity and no models.

Run it against a stub-mode service to verify the skeleton end to end:

    python -m app.smoke_client

It synthesises microphone input (silence, a tone, silence) so the VAD fires
without a real microphone, prints every control message, writes the received TTS
audio to ``smoke-tts.wav`` (gitignored), and exercises barge-in by speaking again
while the character is still talking.

This is the **simulated** test mode from ``docs/acceptance.md``. It proves the
protocol and the interruption path. It proves nothing about the headset, the
character, or real speech.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import wave
from pathlib import Path

import numpy as np

from . import protocol

SAMPLE_RATE = 16000
FRAME_MS = 20
#: Pause between microphone frames. Not real time — the VAD is frame-based, not
#: wall-clock-based — but enough to avoid dumping the whole utterance in one burst.
FRAME_SEND_DELAY_S = 0.001


def _tone(seconds: float, freq: float = 440.0, amplitude: float = 0.3) -> np.ndarray:
    count = int(seconds * SAMPLE_RATE)
    t = np.arange(count, dtype=np.float64) / SAMPLE_RATE
    return (amplitude * np.sin(2.0 * np.pi * freq * t)).astype(np.float32)


def _silence(seconds: float) -> np.ndarray:
    return np.zeros(int(seconds * SAMPLE_RATE), dtype=np.float32)


class Smoke:
    def __init__(self, ws, args: argparse.Namespace) -> None:
        self.ws = ws
        self.args = args
        self.state: str | None = None
        self.rounds: set[int] = set()
        self.tts_frames = 0
        self.tts_bytes = bytearray()
        self.tts_rate = 0
        self.errors: list[str] = []
        self._received = 0

    # -- receive -----------------------------------------------------------

    async def receive_loop(self) -> None:
        async for message in self.ws:
            if isinstance(message, bytes):
                frame = protocol.decode_audio_frame(message)
                if frame.kind is protocol.AudioKind.TTS:
                    self.tts_frames += 1
                    self.tts_rate = frame.sample_rate
                    self.tts_bytes.extend(frame.payload)
                continue
            self._handle_control(json.loads(message))

    def _handle_control(self, msg: dict) -> None:
        self._received += 1
        mtype = msg.get("type")
        round_ = msg.get("round")
        if isinstance(round_, int) and round_:
            self.rounds.add(round_)

        if mtype == "state":
            self.state = msg.get("state")
        elif mtype == "error":
            self.errors.append(f"{msg.get('code')}: {msg.get('message')}")

        if self.args.verbose or mtype in ("error", "interrupt", "tts.start", "tts.end", "asr.final"):
            extra = ""
            if mtype == "llm.delta":
                extra = repr(msg.get("text"))
            elif mtype == "state":
                extra = str(msg.get("state"))
            elif mtype == "asr.final":
                extra = repr(msg.get("text"))
            elif mtype == "tts.start":
                extra = f"#{msg.get('sentenceIndex')} {msg.get('text')!r} @ {msg.get('audio')}"
            elif mtype == "tts.end":
                extra = f"#{msg.get('sentenceIndex')} {msg.get('reason')}"
            elif mtype == "interrupt":
                extra = str(msg.get("reason"))
            elif mtype == "error":
                extra = f"{msg.get('code')}: {msg.get('message')}"
            print(f"  <- {mtype:<16} round={round_} {extra}")

    # -- send --------------------------------------------------------------

    async def send_control(self, payload: dict) -> None:
        payload.setdefault("v", protocol.PROTOCOL_VERSION)
        await self.ws.send(protocol.dumps(payload))

    async def send_mic(self, samples: np.ndarray) -> None:
        """Chop float32 mono into 20 ms S16LE frames and send them."""
        step = int(SAMPLE_RATE * FRAME_MS / 1000)
        for start in range(0, samples.size, step):
            block = samples[start : start + step]
            if block.size == 0:
                continue
            pcm = (np.clip(block, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()
            frame = protocol.AudioFrame(
                kind=protocol.AudioKind.MIC,
                round=0,
                seq=0,
                sample_rate=SAMPLE_RATE,
                channels=1,
                frame_ms=FRAME_MS,
                payload=pcm,
            )
            await self.ws.send(protocol.encode_audio_frame(frame))
            await asyncio.sleep(FRAME_SEND_DELAY_S)

    async def say_something(self) -> None:
        """One utterance: a little lead-in, a voiced stretch, then a pause."""
        await self.send_mic(_silence(0.30))
        await self.send_mic(_tone(1.20))
        await self.send_mic(_silence(1.60))

    # -- synchronisation ---------------------------------------------------

    async def wait_state(self, target: str, timeout: float, label: str) -> None:
        deadline = time.monotonic() + timeout
        while self.state != target:
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"timed out after {timeout:.0f}s waiting for state {target!r} "
                    f"while {label} (last state: {self.state!r})"
                )
            await asyncio.sleep(0.05)

    # -- script ------------------------------------------------------------

    async def run(self) -> int:
        print(f"connecting to {self.args.url}")
        await self.send_control({"type": "hello", "client": "smoke-client"})
        await self.send_control({"type": "session.start"})
        await self.wait_state("listening", 10, "handshaking")
        print("  session started")

        print("round 1: one utterance, allowed to finish")
        await self.say_something()
        await self.wait_state("speaking", self.args.timeout, "waiting for the reply")
        print("  the character is speaking")
        await self.wait_state("listening", self.args.timeout, "waiting for round 1 to finish")
        print("  round 1 complete")

        print("round 2: speak while the character is still talking (barge-in)")
        await self.say_something()
        await self.wait_state("speaking", self.args.timeout, "waiting for the reply")
        print("  interrupting")
        await self.say_something()
        await self.wait_state("listening", self.args.timeout, "waiting for round 2 to finish")
        print("  round 2 complete")

        await self.send_control({"type": "session.end"})
        await asyncio.sleep(0.3)
        return self.report()

    def report(self) -> int:
        print()
        print("summary")
        print(f"  control messages : {self._received}")
        print(f"  rounds seen      : {sorted(self.rounds)}")
        print(f"  tts frames       : {self.tts_frames} ({self.tts_rate} Hz)")
        print(f"  errors           : {len(self.errors)}")

        if self.tts_bytes and self.tts_rate:
            path = Path(self.args.out)
            with wave.open(str(path), "wb") as fh:
                fh.setnchannels(1)
                fh.setsampwidth(2)
                fh.setframerate(self.tts_rate)
                fh.writeframes(bytes(self.tts_bytes))
            print(f"  tts audio        : {path} ({len(self.tts_bytes) / 2 / self.tts_rate:.1f}s)")
        else:
            print("  tts audio        : none received")

        if self.errors:
            for line in self.errors:
                print(f"  ! {line}", file=sys.stderr)
            return 1
        if self.tts_frames == 0:
            print("  ! no TTS audio arrived", file=sys.stderr)
            return 1
        print("  ok")
        return 0


async def _main(args: argparse.Namespace) -> int:
    import websockets

    async with websockets.connect(args.url, max_size=None) as ws:
        smoke = Smoke(ws, args)
        receiver = asyncio.create_task(smoke.receive_loop())
        try:
            return await smoke.run()
        except TimeoutError as exc:
            print(f"! {exc}", file=sys.stderr)
            return 2
        finally:
            receiver.cancel()
            try:
                await receiver
            except (asyncio.CancelledError, Exception):
                pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--url", default="")
    parser.add_argument("--out", default="smoke-tts.wav")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("-v", "--verbose", action="store_true", help="print every message")
    args = parser.parse_args()
    if not args.url:
        args.url = f"ws://{args.host}:{args.port}/ws"
    return asyncio.run(_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
