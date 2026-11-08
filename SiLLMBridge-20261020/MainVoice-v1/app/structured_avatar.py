"""Collect strict model JSON before allowing any text into the speech pipeline."""
from __future__ import annotations
import asyncio
import json
import uuid
import httpx
from .engines.base import EngineUnavailable

URL = 'http://127.0.0.1:18766'


async def collect_avatar_reply(session, round_, messages):
    async with httpx.AsyncClient(timeout=5, trust_env=False) as client:
        try:
            response = await client.get(URL + '/v1/context')
            response.raise_for_status()
            context = response.json()
        except (httpx.HTTPError, ValueError, KeyError):
            raise EngineUnavailable('本地动作服务不可用，请从动作情绪版入口启动。') from None
        instruction = context['system_prompt'] + '\nJSON Schema:\n' + json.dumps(context['json_schema'], ensure_ascii=False)
        raw = ''
        async for delta in session.engines.llm.stream([{'role': 'system', 'content': instruction}, *messages], round_.cancel):
            if not session.is_current(round_):
                return None
            raw += delta
            if len(raw) > 32768:
                raise EngineUnavailable('模型结构化回复过长，本轮未执行动作。')
        if not session.is_current(round_):
            return None
        try:
            plan = json.loads(raw, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
            if not isinstance(plan, dict) or not isinstance(plan.get('text'), str):
                raise ValueError()
            # A local unique request key prevents a transport retry from replaying a turn.
            plan['request_id'] = 'voice-' + uuid.uuid4().hex
            response = await client.post(URL + '/v1/voice/perform', json={'round': round_.id, 'plan': plan})
            response.raise_for_status()
            effective = response.json()['effective_plan']
        except (ValueError, KeyError, TypeError, httpx.HTTPError):
            raise EngineUnavailable('模型没有返回有效的情绪动作JSON，本轮未朗读或执行。') from None
        if not session.is_current(round_):
            return None
        await session.emit_json({'v': 1, 'type': 'avatar.plan', 'round': round_.id,
                                 'emotion': effective['emotion'], 'expression': effective['expression_variant'],
                                 'actions': effective['actions']})
        return effective['text']
