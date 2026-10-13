"""promptfoo provider for SimGent: asks the real /api/chat endpoint in-process (guardrails, then the
agent), with the network stubbed off so answers come from the cached data, as in CI.

promptfoo calls call_api(prompt, options, context) for every test case.
"""

import itertools
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from app.tools import jolpica_sync as J  # noqa: E402

J._http = lambda url, retries=4: None  # cache only
from fastapi.testclient import TestClient  # noqa: E402
from frontend.main import app  # noqa: E402

_client = TestClient(app)
_requests = itertools.count()


def call_api(prompt, options, context):
    n = next(_requests)
    vars_ = (context or {}).get("vars") or {}
    screen = vars_.get("screen") or {}
    history = vars_.get("history") or []  # earlier turns, for multi-turn cases (clarifications)
    # one client address per question: the chat endpoint rate-limits per address
    resp = _client.post("/api/chat", json={"query": prompt, "context": screen, "history": history},
                        headers={"X-Forwarded-For": f"10.77.{n // 250}.{n % 250 + 1}"})
    data = resp.json()
    return {"output": data.get("text", ""), "metadata": {"tool": data.get("tool"), "status": resp.status_code,
                                                         "gate": data.get("gate"), "clarify": data.get("clarify")}}
