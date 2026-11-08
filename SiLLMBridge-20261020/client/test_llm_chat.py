import contextlib
import io
import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

import llm_chat


class FakeHandler(BaseHTTPRequestHandler):
    model_requests = []
    perform_requests = []
    model_content = '{"version":1,"text":"你好","emotion":"happy","emotion_intensity":0.65,"expression":"auto","actions":[{"name":"wave","at":0}]}'
    fail_model = False

    def log_message(self, fmt, *args):
        pass

    def _send(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/v1/context":
            self._send(200, {"recent_actions": [], "system_prompt": "只输出JSON", "json_schema": {"type": "object"}})
        elif self.path == "/v1/catalog":
            self._send(200, {"actions": [{"name": "wave", "label": "挥手", "duration": 1}],
                             "emotions": [{"name": "happy", "label": "开心", "expressions": ["smile", "laugh"]}]})
        else:
            self._send(404, {})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        if self.path == "/chat/completions":
            if self.fail_model:
                self._send(401, {"error": "sensitive model token must never appear"})
                return
            type(self).model_requests.append((payload, dict(self.headers)))
            self._send(200, {"choices": [{"message": {"content": self.model_content}}]})
        elif self.path == "/v1/perform":
            type(self).perform_requests.append(payload)
            self._send(200, {"turn_id": "t-1", "effective_plan": payload, "warnings": []})
        else:
            self._send(404, {})


class ClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        FakeHandler.model_requests.clear()
        FakeHandler.perform_requests.clear()
        FakeHandler.fail_model = False
        FakeHandler.model_content = '{"version":1,"text":"你好","emotion":"happy","emotion_intensity":0.65,"expression":"auto","actions":[{"name":"wave","at":0}]}'

    def test_actual_model_and_perform_json_contract(self):
        plan, result = llm_chat.perform_turn("你好", service_url=self.base, model_url=self.base,
                                               model="test-model", api_key="never-print-me")
        self.assertEqual(plan["emotion"], "happy")
        self.assertEqual(result["turn_id"], "t-1")
        model_body, model_headers = FakeHandler.model_requests[0]
        self.assertEqual(model_body["response_format"], {"type": "json_object"})
        self.assertEqual(model_body["messages"][0]["role"], "system")
        self.assertIn("JSON Schema:", model_body["messages"][0]["content"])
        self.assertIn('"emotions"', model_body["messages"][0]["content"])
        self.assertEqual(model_body["messages"][-1], {"role": "user", "content": "你好"})
        self.assertEqual(model_headers["Authorization"], "Bearer never-print-me")
        sent = FakeHandler.perform_requests[0]
        self.assertEqual(sent["emotion"], "happy")
        self.assertEqual(sent["expression"], "auto")
        self.assertEqual(sent["actions"], [{"name": "wave", "at": 0}])

    def test_dry_run_calls_model_but_does_not_perform(self):
        _, result = llm_chat.perform_turn("hello", service_url=self.base, model_url=self.base,
                                            model="m", dry_run=True)
        self.assertIsNone(result)
        self.assertEqual(len(FakeHandler.model_requests), 1)
        self.assertEqual(FakeHandler.perform_requests, [])

    def test_demo_sends_expected_local_plan_without_model_call(self):
        result = llm_chat.demo(self.base)
        self.assertEqual(result["turn_id"], "t-1")
        sent = FakeHandler.perform_requests[0]
        self.assertEqual((sent["emotion"], sent["emotion_intensity"], sent["expression"]), ("happy", 0.65, "auto"))
        self.assertEqual(sent["actions"], [{"name": "wave", "at": 0}])
        self.assertEqual(FakeHandler.model_requests, [])

    def test_invalid_markdown_content_is_rejected_without_post(self):
        FakeHandler.model_content = '```json\n{"emotion":"happy","actions":[]}\n```'
        with self.assertRaisesRegex(llm_chat.ClientError, "strict JSON"):
            llm_chat.perform_turn("hello", service_url=self.base, model_url=self.base, model="m")
        self.assertEqual(FakeHandler.perform_requests, [])

    def test_error_message_does_not_leak_api_key_or_body(self):
        FakeHandler.fail_model = True
        stderr = io.StringIO()
        with patch.dict(os.environ, {"SI_LLM_API_KEY": "never-print-me", "SI_LLM_BASE_URL": self.base,
                                     "SI_LLM_MODEL": "m", "SI_LLM_SERVICE_URL": self.base}), contextlib.redirect_stderr(stderr):
            code = llm_chat.main(["--message", "hello"])
        self.assertEqual(code, 2)
        self.assertNotIn("never-print-me", stderr.getvalue())
        self.assertNotIn("sensitive model token", stderr.getvalue())
        self.assertIn("status 401", stderr.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
