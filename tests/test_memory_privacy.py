"""Privacy boundaries for public feedback, seed storage, and admin APIs."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import asyncio
from types import SimpleNamespace
from app.tools.agent_memory import AgentMemory, DEFAULT_MEMORIES, SEED_FILE
from frontend import main


class ASGIClient:
    """Exercise HTTP routing without extra client dependencies."""
    def request(self, method, path, headers=None, json=None):
        payload = __import__('json').dumps(json).encode() if json is not None else b''
        scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
                 "method": method, "scheme": "http", "path": path, "raw_path": path.encode(),
                 "query_string": b"", "root_path": "", "server": ("test", 80),
                 "client": ("127.0.0.1", 1234), "headers": [(b'content-type', b'application/json')]
                 + [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]}
        messages = []
        async def receive():
            return {"type": "http.request", "body": payload, "more_body": False}
        async def send(message):
            messages.append(message)
        asyncio.run(main.app(scope, receive, send))
        body = b''.join(m.get('body', b'') for m in messages).decode()
        return SimpleNamespace(status_code=messages[0]['status'], text=body,
                               json=lambda: __import__('json').loads(body))

    def get(self, path, **kwargs):
        return self.request('GET', path, **kwargs)

    def post(self, path, **kwargs):
        return self.request('POST', path, **kwargs)


class MemoryPrivacyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.manager = AgentMemory(str(Path(self.tmp.name) / 'memory.json'),
                                   str(Path(self.tmp.name) / 'feedback.json'))
        self.client = ASGIClient()
        self.replace_manager = patch.object(main, 'memory_manager', self.manager)
        self.replace_manager.start()

    def tearDown(self):
        self.replace_manager.stop()
        self.tmp.cleanup()

    def test_admin_routes_fail_closed(self):
        routes = [('get', '/api/memory'), ('post', '/api/memory/review'),
                  ('get', '/api/eval'),
                  ('post', '/api/eval/remediate')]
        with patch.dict(os.environ, {'SIMGENT_ADMIN_TOKEN': ''}):
            for method, url in routes:
                self.assertEqual(getattr(self.client, method)(url).status_code, 503)
        with patch.dict(os.environ, {'SIMGENT_ADMIN_TOKEN': 'synthetic-test-token'}):
            for method, url in routes:
                self.assertEqual(getattr(self.client, method)(url).status_code, 401)
                self.assertEqual(getattr(self.client, method)(url, headers={
                    'Authorization': 'Bearer invalid'}).status_code, 401)
            self.assertEqual(self.client.get('/api/memory', headers={
                'Authorization': 'Bearer synthetic-test-token'}).status_code, 200)
            self.assertEqual(self.client.post('/api/memory/review', headers={
                'Authorization': 'Bearer synthetic-test-token'}).status_code, 200)

    def test_public_feedback_is_private_and_does_not_learn(self):
        before = self.manager.load_memories()
        response = self.client.post('/api/feedback', json={
            'query': 'synthetic private query', 'response_text': 'synthetic private answer',
            'rating': 'down', 'comment': 'synthetic private correction'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['memory_updated'])
        self.assertEqual(self.manager.load_memories(), before)
        self.assertEqual(len(self.manager.load_feedback()), 1)
        public = self.client.get('/api/memory/stats')
        self.assertEqual(public.status_code, 200)
        self.assertNotIn('synthetic private', public.text)
        self.assertNotIn('recent_feedback', public.text)
        self.assertEqual(public.json()['memories'], DEFAULT_MEMORIES)

    def test_learned_memory_never_changes_public_seed(self):
        original = Path(SEED_FILE).read_bytes()
        self.manager.store('synthetic private query', 'synthetic private correction')
        learned = json.loads(Path(self.manager.memory_file).read_text())
        self.assertEqual(len(learned), 1)
        self.assertEqual(Path(SEED_FILE).read_bytes(), original)
        self.assertIsNotNone(self.manager.retrieve('synthetic private query'))
        self.assertEqual(len(self.manager.load_memories()), len(DEFAULT_MEMORIES) + 1)

    def test_seed_override_is_private_and_does_not_mutate_seed(self):
        seed = DEFAULT_MEMORIES[0]
        original = json.dumps(DEFAULT_MEMORIES, sort_keys=True)
        self.manager.store(seed['patterns'][0], 'synthetic private override', topic=seed['topic'])
        self.assertEqual(json.dumps(DEFAULT_MEMORIES, sort_keys=True), original)
        self.assertEqual(len(json.loads(Path(self.manager.memory_file).read_text())), 1)
        self.assertNotIn('synthetic private override', self.client.get('/api/memory/stats').text)


if __name__ == '__main__':
    unittest.main()
