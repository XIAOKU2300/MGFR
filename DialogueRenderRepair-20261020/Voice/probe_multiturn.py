"""Inspect real model reply structure without logging private content or credentials."""
import asyncio
import datetime
import json
from pathlib import Path
import runpy
import sys

ROOT = Path('H:/MGFR')
HERE = Path(__file__).resolve().parent
SERVICE = ROOT / 'SpeechNatural-20261019/VoiceService10'
REPAIR = ROOT / 'SpeechNatural-20261019/VoiceRepair'
sys.dont_write_bytecode = True
sys.path[:0] = [str(SERVICE), str(REPAIR)]

async def main():
    original = runpy.run_path(str(SERVICE / 'voice_server.py'), run_name='private_config_probe')
    app = original['namespace']['app']
    import avatar_upgrade
    avatar_upgrade.install(app)
    from app.engines.llm_openai import OpenAiCompatLlm
    from app import mgfr_avatar_json as adapter
    import httpx
    async with httpx.AsyncClient(trust_env=False) as client:
        context = (await client.get(adapter.URL + '/v1/context')).json()
    instruction = context['system_prompt'] + '\nJSON Schema:\n' + json.dumps(context['json_schema'], ensure_ascii=False)
    instruction += '\n聊天身体动作仅允许以下已检查的名字，其余动作请省略：' + ','.join(sorted(adapter.REVIEWED_ACTIONS))
    engine = OpenAiCompatLlm(app.state.config.llm)
    history = []
    rows = []
    try:
        for index, prompt in enumerate(['你好，祀。用一句话打个招呼。', '你刚才说了什么？用一句话回答。', '我们接着聊，你现在想做什么？只说一句。'], 1):
            adapter.ensure_json_budget(engine)
            raw = ''.join([delta async for delta in engine.stream([{'role': 'system', 'content': instruction}, *history, {'role': 'user', 'content': prompt}], asyncio.Event())])
            try:
                value = json.loads(raw)
                valid = isinstance(value, dict) and isinstance(value.get('text'), str) and bool(value['text'].strip())
                keys = sorted(key for key in value if key in ('text', 'speech', 'reply', 'actions', 'emotion')) if isinstance(value, dict) else []
            except ValueError:
                value, valid, keys = {}, False, []
            recovered = adapter.normalize(adapter.decode_reply(raw), context.get('catalog') or {'actions': []})
            fallback = recovered['text'] == '刚才那句没说完整，我们接着聊。'
            row = {'turn': index, 'chars': len(raw), 'nonWhitespace': len(raw.strip()), 'startsObject': raw.lstrip().startswith('{'), 'endsObject': raw.rstrip().endswith('}'), 'validTextObject': valid, 'recognizedKeys': keys, 'fallback': fallback, 'finishReason': getattr(engine, '_mgfr_finish_reason', None), 'metrics': engine.metrics}
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
            history.extend([{'role': 'user', 'content': prompt}, {'role': 'assistant', 'content': recovered['text']}])
    finally:
        await engine.aclose()
    output = HERE / ('live-legacy-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.json')
    with output.open('x', encoding='utf-8') as f:
        json.dump({'rawContentSaved': False, 'turns': rows}, f, ensure_ascii=False, indent=2)
    print(str(output))

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as error:
        print('Probe failed: ' + type(error).__name__, file=sys.stderr)
        raise SystemExit(1)
