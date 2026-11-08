import json
import random
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from bridge_server import Bridge, InvalidPlan, make_server


def catalog():
    return {'actions': [
        {'name': 'idle', 'label': 'Idle', 'family': 'idle', 'file': 'idle.motion', 'duration': 2},
        {'name': 'wave', 'label': 'Wave', 'family': 'greeting', 'file': 'wave.motion', 'duration': 4},
        {'name': 'intro', 'label': 'Introduction', 'family': 'greeting', 'file': 'intro.motion', 'duration': 3},
        {'name': 'nod', 'label': 'Nod', 'family': 'affirm', 'file': 'nod.motion', 'duration': 1.5},
    ], 'emotions': [{'name': name, 'variants': [{'name': name + str(i)} for i in range(3)]}
                    for name in ['neutral', 'happy', 'sad', 'angry', 'surprised', 'shy', 'thinking', 'affection']]}


def plan(name='wave', emotion='sad'):
    return {'version': 1, 'text': '我在听。', 'emotion': emotion, 'emotion_intensity': .5,
            'speech_duration': 8, 'actions': [{'name': name, 'at': 0}]}


class SchedulingTests(unittest.TestCase):
    def setUp(self):
        self.now = 10.0
        self.bridge = Bridge(catalog(), clock=lambda: self.now, rng=random.Random(1))

    def test_emotion_and_body_run_together_then_idle(self):
        result = self.bridge.perform(plan())
        state = self.bridge.state()
        self.assertEqual((state['action'], state['emotion']), ('wave', 'sad'))
        self.assertTrue(state['expression'].startswith('sad'))
        self.assertEqual(state['turn_id'], result['turn_id'])
        self.now += 4.1
        state = self.bridge.state()
        self.assertEqual(state['action'], 'idle')
        self.assertEqual(state['emotion'], 'sad')
        self.now += 4
        self.assertEqual(self.bridge.state()['expression'], 'native')

    def test_repetition_uses_semantic_alternative_then_quiet(self):
        first = self.bridge.perform(plan())['effective_plan']
        second = self.bridge.perform(plan())['effective_plan']
        third = self.bridge.perform(plan())['effective_plan']
        self.assertEqual(first['actions'][0]['name'], 'wave')
        self.assertEqual(second['actions'][0]['name'], 'intro')
        self.assertEqual(third['actions'], [])
        self.assertEqual(len({v['expression_variant'] for v in [first, second, third]}), 3)

    def test_overlap_shift_preserves_order(self):
        value = plan()
        value['actions'].append({'name': 'nod', 'at': 1})
        result = self.bridge.perform(value)
        self.assertEqual(result['effective_plan']['actions'][1]['at'], 4)

    def test_invalid_inputs_do_not_mutate_state(self):
        mutations = [dict(plan(), emotion='made_up'), dict(plan(), emotion_intensity=True),
                     dict(plan(), emotion_intensity=float('nan')), dict(plan(), unknown='field'),
                     dict(plan(), actions=[{'name': '../bad', 'at': 0}]),
                     dict(plan(), actions=[{'name': 'wave', 'at': float('inf')}]),
                     dict(plan(), version=True), dict(plan(), actions='wave')]
        for value in mutations:
            with self.assertRaises(InvalidPlan):
                self.bridge.perform(value)
        self.assertIsNone(self.bridge.current)
        self.assertEqual(len(self.bridge.history), 0)

    def test_request_id_is_idempotent_and_conflicts_rejected(self):
        value = dict(plan(), request_id='one')
        a = self.bridge.perform(value)
        b = self.bridge.perform(value)
        self.assertEqual(a, b)
        self.assertEqual(len(self.bridge.history), 1)
        with self.assertRaises(InvalidPlan):
            self.bridge.perform(dict(value, text='另一句'))

    def test_native_keeps_expression_layer_off(self):
        self.bridge.perform(dict(plan(), expression='native'))
        self.assertEqual(self.bridge.state()['expression'], 'native')


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server(catalog(), 0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = 'http://127.0.0.1:' + str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_real_http_perform_state_context_and_player_ack(self):
        with urlopen(self.url + '/v1/context') as r:
            context = json.load(r)
        self.assertIn('emotion', context['json_schema']['required'])
        request = Request(self.url + '/v1/perform', json.dumps(plan()).encode(), {'Content-Type': 'application/json'})
        with urlopen(request) as r:
            result = json.load(r)
        with urlopen(self.url + '/v1/player/state') as r:
            self.assertEqual(json.load(r)['turn_id'], result['turn_id'])
        ack = {'turn_id': result['turn_id'], 'action': 'wave', 'expression': 'sad0', 'bones': 596}
        with urlopen(Request(self.url + '/v1/player/ack', json.dumps(ack).encode(), {'Content-Type': 'application/json'})) as r:
            self.assertTrue(json.load(r)['ok'])
        with urlopen(self.url + '/v1/status') as r:
            self.assertTrue(json.load(r)['player']['connected'])

    def test_nonfinite_json_and_browser_origin_rejected(self):
        for body, headers, expected in [(b'{"emotion_intensity":NaN}', {'Content-Type': 'application/json'}, 400),
                                        (b'{}', {'Content-Type': 'application/json', 'Origin': 'https://example.com'}, 403)]:
            with self.assertRaises(HTTPError) as error:
                urlopen(Request(self.url + '/v1/perform', body, headers))
            self.assertEqual(error.exception.code, expected)


if __name__ == '__main__':
    unittest.main(verbosity=2)
