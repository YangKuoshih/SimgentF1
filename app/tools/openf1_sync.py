"""
OpenF1 sync for the Sprint Qualifying (2024 on) / Sprint Shootout (2023) session.

Jolpica does not publish this session, so it comes from the free OpenF1 API
(https://openf1.org, historical data from 2023, no key needed). OpenF1 labels both
formats "Sprint Qualifying". Each session is cached as
data/cache/openf1/{year}_{round}_sprint_qualifying.json in the row format that
jolpica_sync.sprint_qualifying() reads:

  pos, num, driver_name, driver_code, team, q1, q2, q3 (m:ss.sss), laps

OpenF1 data is licensed CC BY-NC-SA 4.0 (see data/cache/openf1/LICENSE.md). OpenF1 is
an unofficial community project, not affiliated with Formula 1.

Usage:
  .venv/bin/python -m app.tools.openf1_sync 2026 2025 2024 2023 [--refresh]
"""

import datetime
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from app.tools import jolpica_sync as J

logger = logging.getLogger("simgent.openf1")

BASE = "https://api.openf1.org/v1"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE = os.path.join(ROOT, "data", "cache", "openf1")
META = os.path.join(CACHE, "sprint_qualifying_meta.json")
FIRST_YEAR = 2023  # first season with a standalone sprint qualifying session

_last_call = 0.0
_sessions: Dict[int, List[Dict[str, Any]]] = {}


def _http(path: str, retries: int = 4) -> Optional[List[Dict[str, Any]]]:
    """Polite GET (OpenF1 free tier: 3 req/s, 30 req/min)."""
    url = f"{BASE}/{path}"
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc != "api.openf1.org" or not parsed.path.startswith("/v1/"):
        raise ValueError("Untrusted data URL")
    global _last_call
    for attempt in range(retries):
        wait = 2.1 - (time.time() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "F1-Simgent/1.0"})
            with J._HTTP_OPENER.open(req, timeout=20) as r:
                data = json.loads(r.read().decode("utf-8"))
            # OpenF1 answers an empty query with {"detail": "No results found."}
            return data if isinstance(data, list) else []
        except urllib.error.HTTPError as e:
            e.close()
            if e.code == 404:
                return []
            if e.code == 429:
                logger.warning(f"⚠️ [OPENF1 429 RATE LIMIT] Backing off {10 * (attempt + 1)}s on {url}")
                time.sleep(10 * (attempt + 1))
                continue
            logger.error(f"❌ [OPENF1 HTTP ERROR {e.code}] Request failed for {url}: {e.reason}")
            return None
        except Exception as e:
            logger.warning(f"⚠️ [OPENF1 RETRY] Attempt {attempt + 1}/{retries} failed for {url}: {e}")
            time.sleep(2)
    logger.error(f"❌ [OPENF1 EXHAUSTED] All {retries} retry attempts failed for {url}")
    return None


def _lap(seconds: Optional[float]) -> str:
    if seconds is None:
        return ""
    m, ms = divmod(round(seconds * 1000), 60000)
    return f"{m}:{ms / 1000:06.3f}"


def _session_key(year: int, rnd: int) -> Optional[int]:
    """OpenF1 session for this round's sprint qualifying, matched on the Jolpica schedule date.
    (Jolpica's session times are sometimes off by up to an hour; there is never more than
    one sprint qualifying on the same day.)"""
    race = next((r for r in J.schedule(year) if str(r.get("round")) == str(rnd)), None)
    sq = race and (race.get("SprintQualifying") or race.get("SprintShootout"))
    if not sq:
        return None
    if year not in _sessions:
        found = _http(f"sessions?year={year}&session_name=Sprint%20Qualifying")
        if found is None:
            return None
        _sessions[year] = found
    hits = [s for s in _sessions[year] if s["date_start"][:10] == sq["date"] and not s.get("is_cancelled")]
    return hits[0]["session_key"] if len(hits) == 1 else None


def convert(results: List[Dict[str, Any]], drivers: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """OpenF1 session_result + drivers -> cached sprint qualifying rows."""
    rows = []
    for r in sorted(results, key=lambda r: (r.get("position") is None, r.get("position") or 0)):
        d = drivers.get(r["driver_number"], {})
        seg = [_lap(t) for t in (list(r.get("duration") or []) + [None, None, None])[:3]]
        # Same convention as the published classification: a driver who reached a segment
        # but set no time there shows DNF/DNS in it (OpenF1 carries this as a flag).
        flag = "DNS" if r.get("dns") else "DNF" if r.get("dnf") else ""
        if flag and "" in seg:
            seg[seg.index("")] = flag
        pos = r.get("position")
        rows.append({
            "pos": str(pos) if pos else ("DQ" if r.get("dsq") else "NC"),
            "num": str(r["driver_number"]),
            "driver_name": f"{d.get('first_name', '')} {d.get('last_name', '')}".strip(),
            "driver_code": d.get("name_acronym", ""),
            "team": d.get("team_name", ""),
            "q1": seg[0], "q2": seg[1], "q3": seg[2],
            "laps": r.get("number_of_laps") or 0,
        })
    return rows


def _write_json(path: str, doc: Any) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def fetch_sprint_qualifying(year: int, rnd: int, refresh: bool = False) -> Optional[List[Dict[str, Any]]]:
    """Cache (and return) the sprint qualifying classification for one round.
    Returns None when the round has no such session or OpenF1 has no result for it yet."""
    if year < FIRST_YEAR:
        return None
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"{year}_{rnd}_sprint_qualifying.json")
    if os.path.exists(path) and not refresh:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    key = _session_key(year, rnd)
    if key is None:
        return None
    results = _http(f"session_result?session_key={key}")
    drivers = _http(f"drivers?session_key={key}")
    if not results or drivers is None:
        return None  # not run yet, or OpenF1 has not published it
    rows = convert(results, {d["driver_number"]: d for d in drivers})
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            if json.load(f) == rows:
                return rows
    source = f"{BASE}/session_result?session_key={key}"
    _write_json(path, rows)
    J._manifest_record(path, source)
    meta = {}
    if os.path.exists(META):
        with open(META, encoding="utf-8") as f:
            meta = json.load(f)
    meta[f"{year}_{rnd}"] = {"session": "Sprint Shootout" if year == 2023 else "Sprint Qualifying",
                             "session_key": key, "source_url": source}
    _write_json(META, dict(sorted(meta.items(), key=lambda kv: tuple(map(int, kv[0].split("_"))))))
    J._manifest_record(META, f"{BASE}/sessions")
    return rows


def _is_recent(sq_date: str) -> bool:
    """Within jolpica_sync.RECENT_DAYS of the session: re-fetch, results can still be amended."""
    try:
        d = datetime.date.fromisoformat(sq_date)
    except ValueError:
        return False
    return 0 <= (datetime.date.today() - d).days <= J.RECENT_DAYS


def sync(year: int, refresh: bool = False) -> None:
    today = datetime.date.today().isoformat()
    for r in J.schedule(year):
        sq = r.get("SprintQualifying") or r.get("SprintShootout")
        if not sq or sq.get("date", "9999") > today:
            continue
        rnd = int(r["round"])
        rows = fetch_sprint_qualifying(year, rnd, refresh or _is_recent(sq["date"]))
        print(f"  R{rnd:>2} {r['raceName']}: sprint_qualifying={'yes (' + str(len(rows)) + ' drivers)' if rows else 'not available yet'}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    for y in args or [str(datetime.date.today().year)]:
        print(f"[{y}] OpenF1 sprint qualifying")
        sync(int(y), refresh="--refresh" in sys.argv)
