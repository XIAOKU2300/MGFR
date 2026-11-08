"""Keep a short structured reply in one prosodic context for GPT-SoVITS."""
from pathlib import Path
import re
import hashlib
import sys

HERE = Path(__file__).resolve().parent
# Preserve the launcher contract and all existing history/name-readback repairs.
REVISION = 'structured-history-natural-clauses-v4'
SPEECH_REVISION = 'si-coherent-neutral-v1'


def group_reply(text, normalize, max_chars=64, min_chars=12):
    """Keep punctuation inside a bounded request, rather than resetting at it.

    The structured pipeline already has the complete reply before calling TTS.
    Only replies above its existing length budget need multiple requests.
    """
    text = normalize(text)
    groups = []
    while len(text) > max_chars:
        window = text[:max_chars]
        stops = [m.end() for m in re.finditer(r'[。！？](?:[”’」』])?', window)
                 if m.end() >= min_chars]
        commas = [m.end() for m in re.finditer(r'[，、；]', window)
                  if m.end() >= min_chars]
        cut = stops[-1] if stops else commas[-1] if commas else max_chars
        # Do not split a decimal, version token or English word at the cap.
        if not stops and not commas:
            while cut < len(text) and text[cut - 1].isascii() and text[cut - 1].isalnum() and (text[cut].isalnum() or text[cut] in '.-_'):
                cut += 1
        groups.append(normalize(text[:cut]))
        text = text[cut:].lstrip()
    if text:
        groups.append(normalize(text))
    return [group for group in groups if group]


class CoherentReplyAccumulator:
    """Collect the already completed JSON reply, then plan bounded breath groups."""
    def __init__(self, max_chars=64, min_chars=12):
        if max_chars < 8:
            raise ValueError('speech phrase limit must be at least 8')
        self.max_chars = max_chars
        self.min_chars = min(min_chars, max_chars)
        self._buf = ''

    @property
    def pending(self):
        return self._buf

    def push(self, delta):
        self._buf += delta
        return []

    def flush(self):
        from app.text import normalize_for_speech
        text, self._buf = self._buf, ''
        return group_reply(text, normalize_for_speech, self.max_chars, self.min_chars)


def install(app, bridge_url):
    sys.path.insert(0, str(HERE))
    from install_voice_v3 import install as base_install
    base_install(app, bridge_url)
    from app.engines import tts_gptsovits
    from app.text import normalize_for_speech
    from app import mgfr_avatar_pipeline
    # Keep commas and full stops as model prosody tokens. Existing completeness
    # retries still protect short onsets and reject missing words.
    tts_gptsovits.prepare_tts_text = normalize_for_speech
    mgfr_avatar_pipeline.SentenceAccumulator = CoherentReplyAccumulator
    # Scope this audition-approved reference to the existing Si variant 1.
    root = next(path for path in HERE.parents if (path / 'SpeechNatural-20261019/VoiceService10').is_dir())
    reference = root / '祀语音/祀语音/祀1/祀1/祀语音-cut.wav_0011476480_0011615040.wav'
    if hashlib.sha256(reference.read_bytes()).hexdigest() != '3ee3cc8e4e294ee81f466187a4969895184c63f2fe9f4fc787dd2d3df6bb7396':
        raise RuntimeError('Reviewed Si reference identity changed')
    original_payload = tts_gptsovits.GptSovitsTts.payload
    if not getattr(original_payload, '_si_neutral_reference_v1', False):
        def neutral_payload(self, text):
            payload = original_payload(self, text)
            if Path(self.cfg.ref_audio).name == 'ref_si_1.wav':
                payload['ref_audio_path'] = str(reference)
                payload['prompt_text'] = '你们别分心了，再磨蹭天就要黑了。'
            return payload
        neutral_payload._si_neutral_reference_v1 = True
        tts_gptsovits.GptSovitsTts.payload = neutral_payload
    import avatar_upgrade
    avatar_upgrade.REVISION = REVISION
    app.state.avatar_revision = REVISION
    app.state.conversation_repair = REVISION
    app.state.speech_revision = SPEECH_REVISION
