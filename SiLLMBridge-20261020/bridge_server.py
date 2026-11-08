"""Loopback JSON-to-character bridge. Python standard library only."""
from collections import deque, OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse
import json
import math
import random
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parent
EMOTIONS = ['neutral', 'happy', 'sad', 'angry', 'surprised', 'shy', 'thinking', 'affection']
SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'required': ['version', 'text', 'emotion', 'actions'],
    'properties': {
        'version': {'const': 1}, 'text': {'type': 'string', 'minLength': 1, 'maxLength': 4000},
        'emotion': {'type': 'string', 'enum': EMOTIONS},
        'emotion_intensity': {'type': 'number', 'minimum': 0, 'maximum': 1},
        'expression': {'type': 'string', 'enum': ['auto', 'native']},
        'speech_duration': {'type': 'number', 'minimum': 1, 'maximum': 120},
        'request_id': {'type': 'string', 'maxLength': 64},
        'actions': {'type': 'array', 'maxItems': 3, 'items': {
            'type': 'object', 'additionalProperties': False, 'required': ['name', 'at'],
            'properties': {'name': {'type': 'string'}, 'at': {'type': 'number', 'minimum': 0, 'maximum': 60}}
        }}
    }
}


class InvalidPlan(ValueError):
    pass


def number(value, lo, hi, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not lo <= value <= hi:
        raise InvalidPlan(field + ' must be a finite number in range')
    return float(value)


class Bridge:
    def __init__(self, catalog, *, clock=time.monotonic, rng=None):
        self.catalog = catalog
        self.actions = {a['name']: a for a in catalog['actions']}
        self.emotions = {e['name']: e['variants'] for e in catalog['emotions']}
        self.clock = clock
        self.rng = rng or random.Random()
        self.lock = threading.RLock()
        self.history = deque(maxlen=20)
        self.cache = OrderedDict()
        self.sequence = 0
        self.current = None
        self.player = {'connected': False}
        self.default_idle = 'idle'
        assert self.default_idle in self.actions

    def validate(self, value):
        if not isinstance(value, dict):
            raise InvalidPlan('JSON object required')
        if set(value) - set(SCHEMA['properties']):
            raise InvalidPlan('Unknown plan field')
        if type(value.get('version')) is not int or value['version'] != 1:
            raise InvalidPlan('version must be 1')
        text = value.get('text')
        if not isinstance(text, str) or not 1 <= len(text.strip()) <= 4000:
            raise InvalidPlan('text must contain 1..4000 characters')
        emotion = value.get('emotion')
        if not isinstance(emotion, str) or emotion not in self.emotions:
            raise InvalidPlan('Unsupported emotion; read /v1/catalog')
        expression = value.get('expression', 'auto')
        if expression not in ['auto', 'native']:
            raise InvalidPlan('expression must be auto or native')
        intensity = number(value.get('emotion_intensity', .65), 0, 1, 'emotion_intensity')
        duration = number(value.get('speech_duration', min(45, max(3, len(text) * .18))), 1, 120, 'speech_duration')
        request_id = value.get('request_id')
        if request_id is not None and (not isinstance(request_id, str) or not 1 <= len(request_id) <= 64):
            raise InvalidPlan('Invalid request_id')
        actions = value.get('actions')
        if not isinstance(actions, list) or len(actions) > 3:
            raise InvalidPlan('actions must be an array of at most 3 entries')
        normalized = []
        last = -1
        for action in actions:
            if not isinstance(action, dict) or set(action) != {'name', 'at'}:
                raise InvalidPlan('Each action requires only name and at')
            name = action['name']
            if not isinstance(name, str) or name not in self.actions or not self.actions[name].get('callable', True):
                raise InvalidPlan('Unknown or non-callable action; read /v1/catalog')
            at = number(action['at'], 0, 60, 'actions.at')
            if at < last:
                raise InvalidPlan('Action times must be sorted')
            last = at
            normalized.append({'name': name, 'at': at})
        return {'version': 1, 'text': text.strip(), 'emotion': emotion, 'emotion_intensity': intensity,
                'expression': expression, 'actions': normalized, 'speech_duration': duration, 'request_id': request_id}

    def perform(self, raw):
        # Validate everything before changing history or current playback.
        plan = self.validate(raw)
        with self.lock:
            request_id = plan.pop('request_id')
            if request_id and request_id in self.cache:
                old_raw, response = self.cache[request_id]
                if old_raw != raw:
                    raise InvalidPlan('request_id reused with different content')
                return response
            now = self.clock()
            warnings = []
            recent = {a['name'] for item in list(self.history)[-3:] for a in item['actions']}
            chosen = set()
            final = []
            end = 0
            for action in plan['actions']:
                name = action['name']
                data = self.actions[name]
                if name in recent or name in chosen:
                    alternatives = [a['name'] for a in self.actions.values()
                                    if a.get('family') == data.get('family') and a.get('family') not in [None, 'idle']
                                    and a.get('callable', True) and a['name'] not in recent | chosen
                                    and a.get('semantic_safe', True)]
                    if alternatives:
                        replacement = self.rng.choice(alternatives)
                        warnings.append('Repeated action ' + name + ' replaced by ' + replacement)
                        name = replacement
                        data = self.actions[name]
                    else:
                        warnings.append('Repeated action ' + name + ' skipped; preserved speech and emotion')
                        continue
                at = max(action['at'], end)
                if at != action['at']:
                    warnings.append('Overlapping action shifted after previous action')
                final.append({'name': name, 'at': at, 'duration': data['duration']})
                chosen.add(name)
                end = at + data['duration']
            variants = self.emotions[plan['emotion']]
            last_variants = {h['expression_variant'] for h in list(self.history)[-2:]}
            available = [v for v in variants if v['name'] not in last_variants]
            variant = self.rng.choice(available or variants)
            plan['actions'] = final
            plan['expression_variant'] = variant['name'] if plan['expression'] == 'auto' else 'native'
            self.sequence += 1
            turn_id = str(uuid.uuid4())
            self.current = {'turn_id': turn_id, 'started': now, 'plan': plan, 'end': max(end, plan['speech_duration'])}
            self.history.append({'turn_id': turn_id, 'emotion': plan['emotion'], 'expression_variant': plan['expression_variant'], 'actions': final})
            response = {'turn_id': turn_id, 'sequence': self.sequence, 'effective_plan': plan, 'warnings': warnings,
                        'speech': {'text': plan['text'], 'duration_hint': plan['speech_duration'], 'tts_included': False}}
            if request_id:
                self.cache[request_id] = (raw, response)
                while len(self.cache) > 64:
                    self.cache.popitem(last=False)
            return response

    def context(self):
        with self.lock:
            prompt = (
                '你通过JSON控制祀说话时的身体和面部。只输出一个符合schema的JSON对象，不要markdown。'
                'text是自然台词；emotion依据语义选择，emotion_intensity通常0.25到0.7，细微变化优先。'
                'expression使用auto，程序从该情绪的多个兼容表情中选变体，与身体动作同时播放。'
                '当前PMX动作没有原生97脸骨曲线；native只关闭面部叠加，语音接口会自动改为auto以免表情消失。'
                'actions最多3个，name只能从catalog的callable动作选，at是从本句开始的秒数，按升序。'
                '不要每句话都挥手、点头或摆弄头发。看recent_actions避开最近三轮重复，安静回应可以actions为空。'
                '尊重动作语义，悲伤时避免欢快互动，不要为了换动作而做无关动作。'
                '只有需要移动时才使用walk。不要编造动作名或使用文件路径。'
            )
            return {'system_prompt': prompt + '\ncatalog=' + json.dumps(self.catalog, ensure_ascii=False)
                    + '\nrecent_actions=' + json.dumps(list(self.history)[-6:], ensure_ascii=False),
                    'json_schema': SCHEMA, 'recent_actions': list(self.history)[-6:]}

    def state(self):
        with self.lock:
            now = self.clock()
            selected = self.actions[self.default_idle]
            elapsed = now % selected['duration']
            cue = 'idle'
            emotion = 'neutral'
            expression = 'native'
            intensity = 0.0
            speaking = False
            text = ''
            turn_id = ''
            if self.current:
                age = max(0, now - self.current['started'])
                plan = self.current['plan']
                turn_id = self.current['turn_id']
                text = plan['text'] if age < self.current['end'] else ''
                speaking = age < plan['speech_duration']
                if age < self.current['end']:
                    emotion = plan['emotion']
                    expression = plan['expression_variant']
                    intensity = plan['emotion_intensity']
                    for i, action in enumerate(plan['actions']):
                        if action['at'] <= age < action['at'] + action['duration']:
                            selected = self.actions[action['name']]
                            elapsed = age - action['at']
                            cue = turn_id + ':' + str(i)
                            break
            return {'sequence': self.sequence, 'turn_id': turn_id, 'cue_id': cue, 'text': text,
                    'action': selected['name'], 'motion_file': selected['file'], 'action_elapsed': elapsed,
                    'action_duration': selected['duration'], 'emotion': emotion, 'expression': expression,
                    'emotion_intensity': intensity, 'speaking': speaking, 'native_face_active': selected.get('native_face_active', False),
                    'loop': cue == 'idle', 'blend_seconds': .25}


class Handler(BaseHTTPRequestHandler):
    server_version = 'SiLocalBridge/1'

    def log_message(self, *args):
        pass

    def reply(self, status, value):
        data = json.dumps(value, ensure_ascii=False, allow_nan=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        try:
            self.wfile.write(data)
        except (ConnectionError, OSError):
            pass

    def allowed(self):
        return self.headers.get('Origin') is None and self.client_address[0] == '127.0.0.1'

    def do_GET(self):
        if not self.allowed():
            return self.reply(403, {'error': 'Local clients only'})
        bridge = self.server.bridge
        path = self.path.split('?')[0]
        if path == '/health':
            return self.reply(200, {'ok': True, 'version': 1})
        if path == '/v1/catalog':
            return self.reply(200, bridge.catalog)
        if path == '/v1/context':
            return self.reply(200, bridge.context())
        if path == '/v1/player/state':
            return self.reply(200, bridge.state())
        if path == '/v1/status':
            with bridge.lock:
                player = dict(bridge.player)
                player['connected'] = bridge.clock() - player.get('last_seen', -1e9) < 3
            return self.reply(200, {'player': player, 'state': bridge.state()})
        return self.reply(404, {'error': 'Unknown endpoint'})

    def do_POST(self):
        if not self.allowed():
            return self.reply(403, {'error': 'Local clients only'})
        if self.headers.get_content_type() != 'application/json':
            return self.reply(415, {'error': 'application/json required'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 65536:
                raise InvalidPlan('Body must be 1..65536 bytes')
            value = json.loads(self.rfile.read(length), parse_constant=lambda v: (_ for _ in ()).throw(InvalidPlan('Nonfinite JSON number')))
            if self.path == '/v1/perform':
                return self.reply(200, self.server.bridge.perform(value))
            if self.path == '/v1/player/ack':
                if not isinstance(value, dict) or set(value) - {'turn_id', 'action', 'expression', 'bones'}:
                    raise InvalidPlan('Invalid player acknowledgement')
                if value.get('bones') != 596 or any(not isinstance(value.get(k, ''), str) or len(value.get(k, '')) > 128 for k in ['turn_id', 'action', 'expression']):
                    raise InvalidPlan('Invalid player acknowledgement')
                with self.server.bridge.lock:
                    self.server.bridge.player = {**value, 'last_seen': self.server.bridge.clock(), 'connected': True}
                return self.reply(200, {'ok': True})
            return self.reply(404, {'error': 'Unknown endpoint'})
        except (InvalidPlan, ValueError, UnicodeError, TypeError):
            return self.reply(400, {'error': 'Invalid JSON plan; use /v1/context schema and /v1/catalog names'})


def make_server(catalog, port=18766):
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    server.bridge = Bridge(catalog)
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=18766)
    parser.add_argument('--catalog', type=Path, default=ROOT / 'catalog.json')
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text(encoding='utf-8'))
    server = make_server(catalog, args.port)
    print('Si bridge ready: http://127.0.0.1:' + str(server.server_port), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
