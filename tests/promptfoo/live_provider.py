"""promptfoo provider that asks the live site (simgent.tonyyang.work) instead of the local code,
to check the deployed app answers like the tested one. One question at a time, paced under the
site's per-visitor rate limit.
"""

import json
import time
import urllib.error
import urllib.request

URL = "https://simgent.tonyyang.work/api/chat"
_last = [0.0]


def call_api(prompt, options, context):
    screen = ((context or {}).get("vars") or {}).get("screen") or {}
    body = json.dumps({"query": prompt, "context": screen, "history": []}).encode()
    for attempt in range(4):
        wait = 1.2 - (time.time() - _last[0])  # stay under ~50 questions a minute
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        try:
            req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json",
                                                                  "User-Agent": "simgent-promptfoo-playground"})
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.load(resp)
            return {"output": data.get("text", ""), "metadata": {"tool": data.get("tool")}}
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(20 * (attempt + 1))
                continue
            return {"error": f"live site returned HTTP {e.code}"}
        except OSError as e:
            return {"error": f"live site unreachable: {e}"}
    return {"error": "live site kept rate-limiting"}
