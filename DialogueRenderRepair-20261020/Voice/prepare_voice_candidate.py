"""Create reviewed voice candidates; never change the installed service."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = Path('H:/MGFR/SpeechNatural-20261019/VoiceRepair')

def create(name, text):
    with (HERE / name).open('x', encoding='utf-8') as stream:
        stream.write(text)

source = (OLD / 'avatar_json.py').read_text(encoding='utf-8')
source = source.replace("    warning('unrecoverable_json_short_spoken_fallback')\n    return {'text': '刚才那句没说完整，我们接着聊。'}", "    raise InvalidStructuredReply('Model did not return usable speech')")
source = source.replace("        warning('missing_text_short_spoken_fallback')\n        text = '刚才那句没说完整，我们接着聊。'", "        raise InvalidStructuredReply('Model reply has no speech text')")
start = source.index('        raw = \'\'\n        async for delta')
end = source.index('        try:\n            response = await client.post', start)
source = source[:start] + '''        # The provider's JSON mode requires prior assistant turns in JSON too.
        # Session history stays spoken text; only the outgoing model payload is encoded.
        request_messages = structured_history(messages)
        plan = None
        for attempt in range(2):
            raw = ''
            async with asyncio.timeout(session.config.llm.request_timeout_s + 2):
                async for delta in session.engines.llm.stream([{'role': 'system', 'content': instruction}, *request_messages], round_.cancel):
                    if not session.is_current(round_):
                        return None
                    raw += delta
                    if len(raw) > 32768:
                        warning('response_size_bound')
                        break
            if not session.is_current(round_):
                return None
            try:
                if len(raw) > 32768:
                    raise InvalidStructuredReply('Model reply exceeded size bound')
                plan = normalize(decode_reply(raw), catalog)
                break
            except InvalidStructuredReply:
                warning('invalid_reply_retry' if attempt == 0 else 'invalid_reply_exhausted')
                if attempt:
                    from .engines.base import EngineUnavailable
                    raise EngineUnavailable('LLM returned no usable reply; please try again') from None
                # Do not append failed output or synthetic speech to conversation history.
                request_messages = [*request_messages, {'role': 'system', 'content': '上一请求没有可用回复。请直接输出一个完整JSON对象，必须含非空text，actions可为空。'}]
        if plan is None:
            return None
''' + source[end:]
source = source.replace('import contextlib\n', 'import contextlib\nimport asyncio\n')
insert = '''
class InvalidStructuredReply(ValueError):
    pass


def structured_history(messages):
    result = []
    for message in messages:
        item = dict(message)
        if item.get('role') == 'assistant':
            text = clean_text(item.get('content'))
            item['content'] = json.dumps({'text': text, 'emotion': 'neutral', 'actions': []}, ensure_ascii=False)
        result.append(item)
    return result


'''
source = source.replace('def decode_reply(raw):\n', insert + 'def decode_reply(raw):\n')
create('avatar_json_v2.py', source)

pipeline = (OLD / 'avatar_pipeline.py').read_text(encoding='utf-8')
pipeline = pipeline.replace('''        except Exception as error:
            await queue.put(error)
            return
        await queue.put(None)''', '''        except asyncio.CancelledError:
            raise
        except Exception as error:
            await queue.put(error)
        finally:
            if session.is_current(round_):
                await queue.put(None)''')
pipeline = pipeline.replace('''                await session.set_state(State.ERROR, round_, str(item))
                return False''', '''                await session.emit_json({"v": 1, "type": "audio.done", "round": round_.id})
                round_.finished = True
                await session.set_state(State.LISTENING, round_, "reply unavailable; ready for next turn")
                return False''')
create('avatar_pipeline_v2.py', pipeline)
print('Created two new voice candidate files; installed files preserved.')
