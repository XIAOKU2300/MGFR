"""Real configured model, six turns, same session history contract; no raw content saved."""
import asyncio
import datetime
import importlib.util
import json
from pathlib import Path
import runpy
import sys

ROOT = Path('H:/MGFR')
HERE = Path(__file__).resolve().parent
SERVICE = ROOT / 'SpeechNatural-20261019/VoiceService10'
sys.dont_write_bytecode = True
sys.path[:0] = [str(SERVICE), str(ROOT / 'SpeechNatural-20261019/VoiceRepair')]

async def main():
    namespace = runpy.run_path(str(SERVICE / 'voice_server.py'), run_name='private_multiturn_check')
    app = namespace['namespace']['app']
    spec = importlib.util.spec_from_file_location('app.mgfr_avatar_json', HERE / 'avatar_json_v2.py')
    adapter = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = adapter
    spec.loader.exec_module(adapter)
    from app.engines.llm_openai import OpenAiCompatLlm
    engine = OpenAiCompatLlm(app.state.config.llm)
    import httpx
    async with httpx.AsyncClient(trust_env=False) as client:
        context = (await client.get(adapter.URL + '/v1/context')).json()
    instruction = context['system_prompt'] + '\nJSON Schema:\n' + json.dumps(context['json_schema'], ensure_ascii=False)
    instruction += '\n聊天身体动作仅允许以下已检查的名字，其余动作请省略：' + ','.join(sorted(adapter.REVIEWED_ACTIONS))
    history, rows = [], []
    prompts = ['你好，祀。用一句话打个招呼。', '你刚才说了什么？用一句话回答。', '我们接着聊，你现在想做什么？只说一句。', '可以陪我散步吗？一句话回答。', '那我们先休息一会儿，好吗？', '记得我们刚才说要做什么吗？一句话回答。']
    try:
        for index, prompt in enumerate(prompts, 1):
            adapter.ensure_json_budget(engine)
            messages = adapter.structured_history([*history, {'role': 'user', 'content': prompt}])
            raw = ''.join([delta async for delta in engine.stream([{'role': 'system', 'content': instruction}, *messages], asyncio.Event())])
            try:
                value = json.loads(raw)
                valid = isinstance(value, dict) and isinstance(value.get('text'), str) and bool(value['text'].strip())
                plan = adapter.normalize(adapter.decode_reply(raw), context.get('catalog') or {'actions': []})
                text = plan['text']
            except (ValueError, AttributeError):
                valid, text = False, ''
            row = {'turn': index, 'chars': len(raw), 'validTextObject': valid, 'finishReason': getattr(engine, '_mgfr_finish_reason', None), 'metrics': engine.metrics}
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
            if not valid:
                break
            history.extend([{'role': 'user', 'content': prompt}, {'role': 'assistant', 'content': text}])
    finally:
        await engine.aclose()
    passed = len(rows) == len(prompts) and all(row['validTextObject'] for row in rows)
    output = HERE / ('live-fixed-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.json')
    with output.open('x', encoding='utf-8') as stream:
        json.dump({'pass': passed, 'rawContentSaved': False, 'turns': rows}, stream, ensure_ascii=False, indent=2)
    print('REAL_MODEL_MULTITURN', passed, str(output), flush=True)
    return 0 if passed else 1

if __name__ == '__main__':
    try:
        raise SystemExit(asyncio.run(main()))
    except Exception as error:
        print('Multiturn check failed: ' + type(error).__name__, file=sys.stderr)
        raise SystemExit(1)
