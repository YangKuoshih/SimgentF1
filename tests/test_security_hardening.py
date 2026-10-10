"""Client-IP trust, test-only rate buckets, security headers and request bounds."""
import asyncio
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic import ValidationError  # noqa: E402
from starlette.requests import Request  # noqa: E402

from frontend import main as M  # noqa: E402


def _req(headers, client="169.254.169.126"):
    raw = [(k.lower().encode(), v.encode()) for k, v in headers]
    return Request({"type": "http", "method": "POST", "path": "/api/chat", "headers": raw,
                    "client": (client, 1234), "query_string": b""})


class ClientIpTests(unittest.TestCase):
    def test_forged_left_entries_are_ignored(self):
        r = _req([("X-Forwarded-For", "1.2.3.4, 203.0.113.9")])
        self.assertEqual(M._client_ip(r), "203.0.113.9")

    def test_cloudflare_edge_uses_cf_connecting_ip(self):
        r = _req([("X-Forwarded-For", "9.9.9.9, 172.70.1.1"), ("CF-Connecting-IP", "198.51.100.7")])
        self.assertEqual(M._client_ip(r), "198.51.100.7")

    def test_cf_header_is_ignored_when_not_from_cloudflare(self):
        r = _req([("X-Forwarded-For", "203.0.113.9"), ("CF-Connecting-IP", "198.51.100.7")])
        self.assertEqual(M._client_ip(r), "203.0.113.9")

    def test_last_header_wins_when_header_is_repeated(self):
        r = _req([("X-Forwarded-For", "1.1.1.1"), ("X-Forwarded-For", "5.6.7.8, 203.0.113.9")])
        self.assertEqual(M._client_ip(r), "203.0.113.9")

    def test_no_header_falls_back_to_peer(self):
        self.assertEqual(M._client_ip(_req([], client="10.0.0.5")), "10.0.0.5")


class TestClientHeaderTests(unittest.TestCase):
    def _flood(self, env):
        from app.tools import jolpica_sync as J
        from app.tools.guardrails import InMemoryRateLimiter
        limiter = InMemoryRateLimiter(requests_per_minute=2)
        allowed = 0
        with patch.dict(os.environ, env, clear=False), patch.object(M, "rate_limiter", limiter), \
                patch.object(J, "_http", lambda url, retries=4: None):
            for i in range(5):
                r = _req([("X-Forwarded-For", "203.0.113.9"), ("X-Test-Client", f"bucket-{i}")])
                try:
                    asyncio.run(M.api_chat(M.ChatMessage(query="Who won?", context=None, history=[]), r))
                    allowed += 1
                except M.HTTPException as e:
                    self.assertEqual(e.status_code, 429)
        return allowed

    def test_test_header_cannot_mint_buckets_in_production(self):
        os.environ.pop("SIMGENT_TRUST_TEST_CLIENT_HEADER", None)
        self.assertEqual(self._flood({}), 2)

    def test_test_header_works_only_when_enabled(self):
        self.assertEqual(self._flood({"SIMGENT_TRUST_TEST_CLIENT_HEADER": "1"}), 5)


class SecurityHeaderTests(unittest.TestCase):
    def test_headers_on_every_response(self):
        sent = {}

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(msg):
            if msg["type"] == "http.response.start":
                sent.update({k.decode().lower(): v.decode() for k, v in msg["headers"]})

        scope = {"type": "http", "method": "GET", "path": "/api/seasons", "raw_path": b"/api/seasons",
                 "headers": [], "query_string": b"", "client": ("127.0.0.1", 1), "server": ("t", 80),
                 "scheme": "http", "root_path": "", "http_version": "1.1"}
        asyncio.run(M.app(scope, receive, send))
        for h in ("content-security-policy", "x-content-type-options", "x-frame-options",
                  "referrer-policy", "strict-transport-security"):
            self.assertIn(h, sent)
        self.assertIn("frame-ancestors 'none'", sent["content-security-policy"])
        self.assertIn("connect-src 'self'", sent["content-security-policy"])


class PageCachingTests(unittest.TestCase):
    def test_html_pages_are_revalidated(self):
        sent = {}

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(msg):
            if msg["type"] == "http.response.start":
                sent.update({k.decode().lower(): v.decode() for k, v in msg["headers"]})

        scope = {"type": "http", "method": "GET", "path": "/", "raw_path": b"/",
                 "headers": [], "query_string": b"", "client": ("127.0.0.1", 1), "server": ("t", 80),
                 "scheme": "http", "root_path": "", "http_version": "1.1"}
        asyncio.run(M.app(scope, receive, send))
        self.assertTrue(sent.get("content-type", "").startswith("text/html"))
        self.assertEqual(sent.get("cache-control"), "no-cache")


class RequestBoundTests(unittest.TestCase):
    def test_simulation_iterations_are_bounded(self):
        with self.assertRaises(ValidationError):
            M.WhatIfRequest(iterations=10_000_000)
        with self.assertRaises(ValidationError):
            M.WhatIfRequest(total_laps=100_000)
        with self.assertRaises(ValidationError):
            M.WhatIfRequest(driver_1={"stints": [{}] * 50})
        self.assertEqual(M.WhatIfRequest().iterations, 200)


class ChatBoundTests(unittest.TestCase):
    def test_oversized_context_and_history_are_rejected(self):
        with self.assertRaises(ValidationError):
            M.ChatMessage(query="Who won?", context={"race": "x" * 5000})
        with self.assertRaises(ValidationError):
            M.ChatMessage(query="Who won?", history=[{"role": "user", "content": "hi"}] * 51)
        M.ChatMessage(query="Who won?", context={"year": 2026, "round": 4, "race": "Miami Grand Prix"})

    def test_race_label_is_linear_on_hostile_input(self):
        import time
        from app.tools.session_scope import scope_label
        scope = {"year": 2026, "round": 4, "session": "race", "race": " " * 3900 + "x"}
        t = time.perf_counter()
        scope_label(scope)
        self.assertLess(time.perf_counter() - t, 0.5)
        self.assertEqual(scope_label(dict(scope, race="Miami Grand Prix - Sprint Weekend")),
                         "2026 Miami Grand Prix · Race")


if __name__ == "__main__":
    unittest.main()
