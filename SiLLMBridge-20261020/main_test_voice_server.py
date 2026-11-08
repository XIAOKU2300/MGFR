"""Offline test fixture: real WebSocket pipeline, synthetic JSON LLM and PCM TTS."""
from pathlib import Path
import json
import sys
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'MainVoice-v1'))
from app import main as voice_main
from app.config import Config
from app.engines.factory import Engines
from app.engines.stub import EnergyVad, StubAsr, StubLlm, StubTts


def build(_cfg):
    plan = {'version': 1, 'text': '我有一点难过，不过会陪你慢慢说。', 'emotion': 'sad', 'emotion_intensity': .6,
            'actions': [{'name': 'think', 'at': 0}]}
    return Engines(vad=EnergyVad(), asr=StubAsr(),
                   llm=StubLlm(reply=json.dumps(plan, ensure_ascii=False), first_token_delay_s=.05, token_delay_s=.001),
                   tts=StubTts(realtime=True))


voice_main.build_all = build
app = voice_main.create_app(Config())
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8775, log_level='error', access_log=False)
