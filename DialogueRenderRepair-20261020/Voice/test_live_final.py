"""Real configured LLM/TTS, multiple WebSocket rounds; no transcript/credentials saved."""
import asyncio
import datetime
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True

async def main():
    import websockets
    rows = []
    async with websockets.connect('ws://127.0.0.1:8775/ws', max_size=8*1024*1024) as ws:
        await ws.send(json.dumps({'v': 1, 'type': 'hello', 'client': 'repair-real-llm-tts-review'}))
        await ws.send(json.dumps({'v': 1, 'type': 'session.start'}))
        async def event():
            return await asyncio.wait_for(ws.recv(), timeout=50)
        while True:
            msg = await event()
            if isinstance(msg, str):
                value = json.loads(msg)
                if value.get('type') == 'state' and value.get('state') == 'listening':
                    break
        for prompt in ['你好，祀，用一句话打个招呼。', '你刚才说了什么？一句话回答。', '接下来陪我散步好吗？一句话回答。', '记得我们刚才说要做什么吗？一句话回答。']:
            await ws.send(json.dumps({'v': 1, 'type': 'text.input', 'text': prompt}))
            row = {'turn': len(rows)+1, 'pcmBytes': 0, 'textChars': 0, 'errors': 0, 'audioDone': False, 'listening': False, 'fallback': False}
            started = time.monotonic()
            while True:
                msg = await event()
                if isinstance(msg, bytes):
                    row['pcmBytes'] += max(0, len(msg)-28)
                    continue
                value = json.loads(msg)
                if value.get('type') == 'llm.delta':
                    delta = value.get('text', value.get('delta', ''))
                    row['textChars'] += len(delta)
                    row['fallback'] |= '刚才那句没说完整' in delta
                row['errors'] += value.get('type') == 'error'
                row['audioDone'] |= value.get('type') == 'audio.done'
                if value.get('type') == 'state' and value.get('state') == 'listening':
                    row['listening'] = True
                    break
            row['seconds'] = round(time.monotonic()-started, 3)
            rows.append(row)
            print(json.dumps(row), flush=True)
    passed = len(rows)==4 and all(r['pcmBytes']>0 and r['textChars']>0 and r['errors']==0 and r['audioDone'] and r['listening'] and not r['fallback'] for r in rows)
    output = HERE / ('live-final-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.json')
    with output.open('x', encoding='utf-8') as stream:
        json.dump({'pass': passed, 'mode': 'Real configured LLM and GPT-SoVITS through corrected worker WebSocket/PCM; text input bypasses microphone/ASR', 'turns': rows}, stream, indent=2)
    print('LIVE_VOICE_WORKER', passed, str(output), flush=True)
    return 0 if passed else 1

if __name__ == '__main__':
    try:
        raise SystemExit(asyncio.run(main()))
    except Exception as error:
        print('Live worker check failed: ' + type(error).__name__, file=sys.stderr)
        raise SystemExit(1)
