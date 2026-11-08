"""JSON speech adapter: optional gestures cannot prevent a spoken reply."""
import contextlib
import asyncio
import json
import logging
import math
import re
import uuid
import httpx

URL = 'http://127.0.0.1:18766'
logger = logging.getLogger(__name__)
REVIEWED_ACTIONS = {'arms_crossed', 'base_idle', 'common_touchhead_end', 'common_touchhead_loop', 'common_touchhead_start', 'idle', 'idle_special_2', 'introduce', 'nod', 'point', 'ponder', 'receive_gift', 'relaxed_idle', 'scratch_head', 'scratch_head_start', 'settle', 'shake_head', 'story_dialog_single_chesthugging3_talk', 'story_dialog_state_adjust_loop', 'story_dialog_state_angry02_end', 'story_dialog_state_angry02_loop', 'story_dialog_state_angry02_start', 'story_dialog_state_censure_end', 'story_dialog_state_censure_loop', 'story_dialog_state_censure_start', 'story_dialog_state_chesthugging1_end', 'story_dialog_state_chesthugging1_start', 'story_dialog_state_chesthugging3_end', 'story_dialog_state_chesthugging3_loop', 'story_dialog_state_chesthugging3_start', 'story_dialog_state_halfraise_end', 'story_dialog_state_halfraise_loop', 'story_dialog_state_halfraise_start', 'story_dialog_state_muse_end', 'story_dialog_state_muse_start', 'story_dialog_state_point_end', 'story_dialog_state_point_start', 'story_dialog_state_surprise_end', 'story_dialog_state_surprise_start', 'story_dialog_virtual_single_idle_talklefthand1', 'story_dialog_virtual_single_idle_talklefthand2', 'story_dialog_virtual_single_idle_talkrighthand1', 'story_dialog_virtual_single_idle_talkrighthand2', 'story_dialog_virtual_state_akimbo1_end', 'story_dialog_virtual_state_akimbo1_loop', 'story_dialog_virtual_state_akimbo1_start', 'story_dialog_virtual_state_akimboleft_end', 'story_dialog_virtual_state_akimboleft_loop', 'story_dialog_virtual_state_akimboleft_start', 'story_dialog_virtual_state_akimboright_end', 'story_dialog_virtual_state_akimboright_loop', 'story_dialog_virtual_state_akimboright_start', 'story_dialog_virtual_state_introduction_end', 'story_dialog_virtual_state_introduction_start', 'story_dialog_virtual_state_scratchhead_end', 'story_dialog_virtual_state_think1_end', 'story_dialog_virtual_state_think1_start', 'surprised_pose', 'talk_hands', 'think', 'tsundere', 'wave'}
EMOTIONS = {'neutral', 'happy', 'sad', 'angry', 'surprised', 'shy', 'thinking', 'affection'}
ALIASES = {'joy': 'happy', 'happiness': 'happy', 'sadness': 'sad', 'anger': 'angry',
           'surprise': 'surprised', 'love': 'affection', 'think': 'thinking', 'bashful': 'shy'}


def warning(kind):
    # Never include model content, user text, upstream bodies or credentials.
    logger.warning('structured_voice_recovery kind=%s', kind)


class CompletionResponse:
    def __init__(self, response, engine):
        self.response, self.engine = response, engine

    def __getattr__(self, name):
        return getattr(self.response, name)

    async def aiter_lines(self):
        async for line in self.response.aiter_lines():
            if line.startswith('data:'):
                try:
                    item = json.loads(line[5:].strip())
                    for choice in item.get('choices', []):
                        if choice.get('finish_reason'):
                            self.engine._mgfr_finish_reason = choice['finish_reason']
                except (ValueError, AttributeError, TypeError):
                    pass
            yield line


class BudgetClient:
    def __init__(self, client, engine):
        self.client, self.engine = client, engine

    @contextlib.asynccontextmanager
    async def stream(self, method, url, **kwargs):
        payload = dict(kwargs['json'])
        # The installed plain-speech config has 180 tokens. JSON needs overhead.
        # Adjust this request only; retain the user's existing configuration.
        payload['max_tokens'] = max(512, int(payload.get('max_tokens', 180)))
        payload['response_format'] = {'type': 'json_object'}
        kwargs['json'] = payload
        async with self.client.stream(method, url, **kwargs) as response:
            yield CompletionResponse(response, self.engine)


def ensure_json_budget(engine):
    if hasattr(engine, '_get_client') and not getattr(engine, '_mgfr_json_budget', False):
        original = engine._get_client
        engine._get_client = lambda: BudgetClient(original(), engine)
        engine._mgfr_json_budget = True
    engine._mgfr_finish_reason = None


def clean_text(value):
    if not isinstance(value, str):
        return ''
    return ''.join(c for c in value if c >= ' ' or c in '\n\t').encode('utf-8', 'replace').decode('utf-8').strip()[:4000]


def finite(value, default, lo, hi):
    if isinstance(value, bool):
        return default
    try:
        value = float(value)
    except (ValueError, TypeError, OverflowError):
        return default
    return max(lo, min(hi, value)) if math.isfinite(value) else default



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


def decode_reply(raw):
    raw = raw.strip().lstrip('\ufeff')
    if raw.startswith('```'):
        raw = re.sub(r'^```(?:json)?\s*', '', raw, count=1, flags=re.I)
        raw = re.sub(r'\s*```\s*$', '', raw, count=1)
    try:
        value = json.loads(raw, parse_constant=lambda _: None)
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            return {'text': value}
    except ValueError:
        # Preserve a complete text string if only later JSON metadata was cut.
        match = re.search(r'"text"\s*:\s*', raw)
        if match:
            try:
                text, _ = json.JSONDecoder().raw_decode(raw, match.end())
                if isinstance(text, str):
                    warning('metadata_truncated_text_preserved')
                    return {'text': text}
            except ValueError:
                pass
        # Ordinary prose is usable speech; apparent JSON/code is never read out.
        if raw and not raw.startswith(('{', '[', '`')) and '"text"' not in raw:
            warning('plain_text_without_metadata')
            return {'text': raw}
    raise InvalidStructuredReply('Model did not return usable speech')


def normalize(value, catalog):
    text = clean_text(value.get('text') or value.get('speech') or value.get('reply'))
    if not text:
        raise InvalidStructuredReply('Model reply has no speech text')
    emotion = str(value.get('emotion') or 'neutral').strip().lower()
    emotion = ALIASES.get(emotion, emotion)
    if emotion not in EMOTIONS:
        emotion = 'neutral'
        warning('unknown_emotion_neutral')
    allowed = {a['name'] for a in catalog.get('actions', []) if a.get('callable', True) and a['name'] in REVIEWED_ACTIONS}
    actions = []
    candidates = value.get('actions', [])
    if not isinstance(candidates, list):
        candidates = []
    for cue in candidates[:3]:
        if isinstance(cue, str):
            cue = {'name': cue, 'at': 0}
        if not isinstance(cue, dict) or not isinstance(cue.get('name'), str) or cue['name'] not in allowed:
            warning('unknown_action_skipped')
            continue
        actions.append({'name': cue['name'], 'at': finite(cue.get('at', 0), 0, 0, 60)})
    actions.sort(key=lambda cue: cue['at'])
    return {'version': 1, 'text': text, 'emotion': emotion,
            'emotion_intensity': finite(value.get('emotion_intensity', .55), .55, 0, 1),
            'expression': value.get('expression') if value.get('expression') in ('auto', 'native') else 'auto',
            'actions': actions, 'request_id': 'voice-' + uuid.uuid4().hex}


_bridge_client = None


def install_http_lifespan(app):
    """Build TLS/connection pools before accepting microphone frames, once per worker."""
    original_lifespan = app.router.lifespan_context

    @contextlib.asynccontextmanager
    async def lifespan(application):
        global _bridge_client
        async with original_lifespan(application):
            async with httpx.AsyncClient(timeout=5, trust_env=False) as client:
                _bridge_client = client
                try:
                    engines = getattr(application.state, 'engines', None)
                    if engines:
                        # HTTPX client construction loads certificate stores synchronously.
                        # Keep that startup work out of the realtime audio receive loop.
                        for engine in (engines.llm, engines.tts):
                            getter = getattr(engine, '_get_client', None)
                            if getter:
                                getter()
                    yield
                finally:
                    _bridge_client = None
    app.router.lifespan_context = lifespan


@contextlib.asynccontextmanager
async def bridge_client():
    if _bridge_client is not None:
        yield _bridge_client
    else:
        # Standalone unit callers without the application lifespan retain support.
        async with httpx.AsyncClient(timeout=5, trust_env=False) as client:
            yield client


def compact_instruction(context, catalog):
    """Keep every callable action and its semantics; omit asset paths and rig metadata."""
    prompt = context['system_prompt'].split('\ncatalog=', 1)[0]
    actions = [{key: action[key] for key in ('name', 'label', 'duration', 'tags', 'family', 'semantic_safe') if key in action}
               for action in catalog.get('actions', [])
               if action.get('callable', True) and action.get('name') in REVIEWED_ACTIONS]
    emotions = [item['name'] for item in catalog.get('emotions', [])]
    recent = [{key: row[key] for key in ('actions', 'emotion', 'expression_variant') if key in row}
              for row in context.get('recent_actions', [])[-3:]]
    return (prompt + '\ncatalog=' + json.dumps({'actions': actions, 'emotions': emotions}, ensure_ascii=False, separators=(',', ':'))
            + '\nrecent_actions=' + json.dumps(recent, ensure_ascii=False, separators=(',', ':'))
            + '\nJSON Schema:\n' + json.dumps(context['json_schema'], ensure_ascii=False, separators=(',', ':')))


async def collect_reply(session, round_, messages):
    catalog = {'actions': []}
    async with bridge_client() as client:
        try:
            response = await client.get(URL + '/v1/context')
            response.raise_for_status()
            context = response.json()
            catalog = context.get('catalog') or catalog
            if not catalog['actions']:
                response = await client.get(URL + '/v1/catalog')
                response.raise_for_status()
                catalog = response.json()
            instruction = compact_instruction(context, catalog)
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            warning('local_action_context_unavailable')
            instruction = '只输出JSON对象，text是自然简短的台词，emotion为neutral，actions为空数组。'
        instruction += '\n聊天身体动作仅允许以下已检查的名字，其余动作请省略：' + ','.join(sorted(REVIEWED_ACTIONS))
        ensure_json_budget(session.engines.llm)
        # The provider's JSON mode requires prior assistant turns in JSON too.
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
        try:
            response = await client.post(URL + '/v1/voice/perform', json={'round': round_.id, 'plan': plan})
            response.raise_for_status()
            effective = response.json()['effective_plan']
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            warning('local_action_plan_unavailable_speech_preserved')
            return plan['text'] if session.is_current(round_) else None
        if not session.is_current(round_):
            return None
        await session.emit_json({'v': 1, 'type': 'avatar.plan', 'round': round_.id,
                                 'emotion': effective['emotion'], 'expression': effective['expression_variant'],
                                 'actions': effective['actions']})
        return effective['text']


def install_reviewed_catalog():
    # The existing worker imports its bridge after this adapter. Keep the API's
    # callable list and repeat substitutions consistent with the reviewed rig.
    from pathlib import Path
    import sys
    from app.config import SERVICE_ROOT
    assets = SERVICE_ROOT.parents[1] / 'SiLLMBridge-20261020'
    if str(assets) not in sys.path:
        sys.path.append(str(assets))
    import bridge_server
    if getattr(bridge_server.Bridge, '_mgfr_reviewed_catalog', False):
        return
    original_init = bridge_server.Bridge.__init__
    def reviewed_init(self, catalog, *args, **kwargs):
        catalog = json.loads(json.dumps(catalog, ensure_ascii=False))
        for action in catalog.get('actions', []):
            if action['name'] not in REVIEWED_ACTIONS:
                action['callable'] = False
        original_init(self, catalog, *args, **kwargs)
    bridge_server.Bridge.__init__ = reviewed_init
    bridge_server.Bridge._mgfr_reviewed_catalog = True


install_reviewed_catalog()
