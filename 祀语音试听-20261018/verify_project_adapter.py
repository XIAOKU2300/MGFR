"""Exercise MGFR's actual streaming TTS adapter with the proposed configuration."""
import asyncio
import hashlib
import json
import os
import sys
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, 'H:/MGFR/dialogue-service')
os.environ['NO_PROXY'] = '127.0.0.1,localhost'
from app.config import Config
from app.engines.tts_gptsovits import GptSovitsTts

async def main():
    cfg = Config.load(HERE / 'MGFR-config.preview.toml')
    adapter = GptSovitsTts(cfg.tts)
    chunks = [chunk async for chunk in adapter.synthesize('你好，今天过得怎么样？', asyncio.Event())]
    assert chunks, 'No audio received'
    rate, channels = chunks[0].sample_rate, chunks[0].channels
    assert rate == 32000 and channels == 1
    assert all(c.sample_rate == rate and c.channels == channels for c in chunks)
    pcm = b''.join(c.pcm for c in chunks)
    assert len(pcm) > rate
    path = HERE / 'MGFR接口验证.wav'
    with path.open('xb') as stream:
        with wave.open(stream, 'wb') as wav:
            wav.setnchannels(channels)
            wav.setsampwidth(2)
            wav.setframerate(rate)
            wav.writeframes(pcm)
    review = json.loads((HERE / 'config-review.json').read_text(encoding='utf-8'))
    assert hashlib.sha256(Path(review['target']).read_bytes()).hexdigest() == review['original_sha256']
    assert Path(review['backup']).read_bytes() == Path(review['target']).read_bytes()
    print(json.dumps({'verified': True, 'adapter': 'MGFR GptSovitsTts', 'streaming': True,
                      'chunks': len(chunks), 'sample_rate': rate, 'channels': channels,
                      'duration_s': round(len(pcm) / 2 / rate, 3),
                      'original_config_unchanged': True, 'backup_verified': True}, ensure_ascii=False))

if __name__ == '__main__':
    asyncio.run(main())
