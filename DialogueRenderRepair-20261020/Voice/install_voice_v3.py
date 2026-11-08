"""Correct structured history and the known persona-name ASR homophone in TTS readback."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / 'SpeechNatural-20261019/VoiceService10').is_dir())
REVISION = 'structured-history-name-readback-v3'

def install(app, bridge_url):
    # Source can run from the final package or the repair's development folder.
    candidates = [HERE, ROOT / 'DialogueRenderRepair-20261020/Current/Voice', ROOT / 'DialogueRenderRepair-20261020/Release-v2/Voice']
    runtime = next(path for path in candidates if (path / 'install_voice_v2.py').is_file())
    sys.path.insert(0, str(runtime))
    from install_voice_v2 import install as install_base
    install_base(app, bridge_url)
    from app.engines import tts_gptsovits
    from app.speech_verify import numbers
    original = tts_gptsovits.speech_completeness
    if not getattr(original, '_mgfr_name_readback', False):
        def name_readback(expected, recognized):
            # Only this voice's known proper name, and only when no actual number
            # is expected. Never change speech text, ASR input or numeric validation.
            if '祀' in expected and not numbers(expected):
                recognized = recognized.replace('四', '祀').replace('寺', '祀').replace('嗣', '祀')
            return original(expected, recognized)
        name_readback._mgfr_name_readback = True
        tts_gptsovits.speech_completeness = name_readback
    # Health route reads the module revision dynamically.
    import avatar_upgrade
    avatar_upgrade.REVISION = REVISION
    app.state.avatar_revision = REVISION
    app.state.conversation_repair = REVISION
