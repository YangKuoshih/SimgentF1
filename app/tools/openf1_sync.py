"""
OpenF1 sync for weekend sessions (https://openf1.org, from 2023, no key needed).

- Sprint Qualifying (2024 on) / Sprint Shootout (2023): Jolpica does not publish this
  session, so OpenF1 is its only source. OpenF1 labels both formats "Sprint Qualifying".
- Sprint and Qualifying: Jolpica is the main source; OpenF1 fills in until Jolpica
  publishes (often hours after the session).

Each session is cached as data/cache/openf1/{year}_{round}_{session}.json. Qualifying-type
rows (read by jolpica_sync.sprint_qualifying / qualifying_results):

  pos, num, driver_name, driver_code, team, q1, q2, q3 (m:ss.sss), laps

Sprint rows (read by jolpica_sync.sprint_results):

  pos, num, driver_name, driver_code, team, laps, points, status, time, millis

During a live F1 session OpenF1 closes free access to all data until it ends; fetches then
return nothing and the next sync retries.

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
_sessions: Dict[Any, List[Dict[str, Any]]] = {}

# session -> (OpenF1 session_name, Jolpica schedule fields holding its date)
SESSIONS = {
    "sprint_qualifying": ("Sprint Qualifying", ("SprintQualifying", "SprintShootout")),
    "sprint": ("Sprint", ("Sprint",)),
    "qualifying": ("Qualifying", ("Qualifying",)),
}


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


def _position(r: Dict[str, Any]) -> Optional[int]:
    """Classified position, or None. OpenF1 sometimes sends text instead (e.g. "RT" for a
    car that retired in qualifying without setting a time)."""
    pos = r.get("position")
    return pos if isinstance(pos, int) and not isinstance(pos, bool) else None


def _lap(seconds: Optional[float]) -> str:
    if seconds is None:
        return ""
    m, ms = divmod(round(seconds * 1000), 60000)
    return f"{m}:{ms / 1000:06.3f}"


def scheduled(year: int, rnd: int, session: str) -> Optional[Dict[str, Any]]:
    """The Jolpica schedule entry ({date, time}) for one session of a round, if it has one."""
    race = next((r for r in J.schedule(year) if str(r.get("round")) == str(rnd)), None)
    return next((race.get(f) for f in SESSIONS[session][1] if race and race.get(f)), None)


def _session_key(year: int, rnd: int, session: str = "sprint_qualifying") -> Optional[int]:
    """OpenF1 session for this round's session, matched on the Jolpica schedule date.
    (Jolpica's session times are sometimes off by up to an hour; a given session type never
    runs twice on the same day.)"""
    when = scheduled(year, rnd, session)
    if not when:
        return None
    name = SESSIONS[session][0]
    if (year, name) not in _sessions:
        found = _http(f"sessions?year={year}&session_name={urllib.parse.quote(name)}")
        if found is None:
            return None
        _sessions[(year, name)] = found
    hits = [s for s in _sessions[(year, name)] if s["date_start"][:10] == when["date"] and not s.get("is_cancelled")]
    return hits[0]["session_key"] if len(hits) == 1 else None


def convert(results: List[Dict[str, Any]], drivers: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """OpenF1 session_result + drivers -> cached sprint qualifying rows."""
    rows = []
    for r in sorted(results, key=lambda r: (_position(r) is None, _position(r) or 0)):
        d = drivers.get(r["driver_number"], {})
        seg = [_lap(t) for t in (list(r.get("duration") or []) + [None, None, None])[:3]]
        # Same convention as the published classification: a driver who reached a segment
        # but set no time there shows DNF/DNS in it (OpenF1 carries this as a flag).
        flag = "DNS" if r.get("dns") else "DNF" if r.get("dnf") else ""
        if flag and "" in seg:
            seg[seg.index("")] = flag
        pos = _position(r)
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


def convert_sprint(results: List[Dict[str, Any]], drivers: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """OpenF1 session_result + drivers -> cached sprint rows, in classification order:
    classified drivers by position, then the unclassified by laps completed."""
    def key(r):
        return (_position(r) is None, _position(r) or 0, -(r.get("number_of_laps") or 0))
    rows = []
    for r in sorted(results, key=key):
        d = drivers.get(r["driver_number"], {})
        pos, gap, dur = _position(r), r.get("gap_to_leader"), r.get("duration")
        if r.get("dsq"):
            status, pos_txt = "Disqualified", "D"
        elif r.get("dns"):
            status, pos_txt = "Did not start", "W"
        elif pos is None:
            status, pos_txt = "Retired", "R"
        else:
            pos_txt = str(pos)
            status = "Retired" if r.get("dnf") else ("Lapped" if isinstance(gap, str) and "LAP" in gap.upper() else "Finished")
        if pos == 1 and dur:
            time = _lap(dur)
        elif status == "Finished" and isinstance(gap, (int, float)):
            time = "+" + (_lap(gap) if gap >= 60 else f"{gap:.3f}")  # Jolpica: +12.345 / +1:16.067
        else:
            time = ""
        rows.append({
            "pos": pos_txt,
            "num": str(r["driver_number"]),
            "driver_name": f"{d.get('first_name', '')} {d.get('last_name', '')}".strip(),
            "driver_code": d.get("name_acronym", ""),
            "team": d.get("team_name", ""),
            "laps": r.get("number_of_laps") or 0,
            "points": r.get("points") or 0,
            "status": status,
            "time": time,
            "millis": round(dur * 1000) if (dur and status == "Finished") else None,
        })
    return rows


def _write_json(path: str, doc: Any) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def fetch_session(year: int, rnd: int, session: str, refresh: bool = False) -> Optional[List[Dict[str, Any]]]:
    """Cache (and return) one session's classification ('sprint_qualifying', 'sprint' or
    'qualifying'). Returns None when the round has no such session or OpenF1 has no result
    for it yet (not run, not published, or OpenF1 closed during a live session)."""
    if year < FIRST_YEAR:
        return None
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"{year}_{rnd}_{session}.json")
    if os.path.exists(path) and not refresh:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    key = _session_key(year, rnd, session)
    if key is None:
        return None
    results = _http(f"session_result?session_key={key}")
    drivers = _http(f"drivers?session_key={key}")
    if not results or drivers is None:
        return None  # not run yet, or OpenF1 has not published it
    by_number = {d["driver_number"]: d for d in drivers}
    rows = convert_sprint(results, by_number) if session == "sprint" else convert(results, by_number)
    if session == "sprint":
        # OpenF1 has no sprint starting grid; each car's first entry in the position feed is
        # its grid slot (matches Jolpica's grid, penalties included, on every 2026 sprint).
        positions = _http(f"position?session_key={key}") or []
        first: Dict[int, int] = {}
        for p in sorted(positions, key=lambda x: x.get("date", "")):
            first.setdefault(p["driver_number"], p["position"])
        for row in rows:
            row["grid"] = str(first.get(int(row["num"]), "")) if first else ""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            if json.load(f) == rows:
                return rows
    _write_json(path, rows)
    J._manifest_record(path, f"{BASE}/session_result?session_key={key}")
    return rows


def fetch_sprint_qualifying(year: int, rnd: int, refresh: bool = False) -> Optional[List[Dict[str, Any]]]:
    """Cache (and return) the sprint qualifying classification for one round, plus its
    session label and source in sprint_qualifying_meta.json."""
    path = os.path.join(CACHE, f"{year}_{rnd}_sprint_qualifying.json")
    if os.path.exists(path) and not refresh:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    before = None
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            before = json.load(f)
    rows = fetch_session(year, rnd, "sprint_qualifying", refresh=True)
    if rows is None or rows == before:
        return rows
    key = _session_key(year, rnd, "sprint_qualifying")
    source = f"{BASE}/session_result?session_key={key}"
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
    """Sprint Qualifying for every sprint weekend; Sprint and Qualifying from OpenF1 only for
    rounds Jolpica has not published yet (Jolpica stays the main source for those)."""
    today = datetime.date.today().isoformat()
    for r in J.schedule(year):
        rnd = int(r["round"])
        sq = r.get("SprintQualifying") or r.get("SprintShootout")
        if sq and sq.get("date", "9999") <= today:
            rows = fetch_sprint_qualifying(year, rnd, refresh or _is_recent(sq["date"]))
            print(f"  R{rnd:>2} {r['raceName']}: sprint_qualifying={'yes (' + str(len(rows)) + ' drivers)' if rows else 'not available yet'}")
        for session, jolpica in (("sprint", J.sprint_results), ("qualifying", J.qualifying_results)):
            when = scheduled(year, rnd, session)
            if not when or when.get("date", "9999") > today or year < FIRST_YEAR:
                continue
            if jolpica(year, rnd, net=False):
                continue  # Jolpica has it
            rows = fetch_session(year, rnd, session, refresh=refresh or _is_recent(when["date"]))
            print(f"  R{rnd:>2} {r['raceName']}: {session} (OpenF1, Jolpica not published)="
                  f"{'yes (' + str(len(rows)) + ' drivers)' if rows else 'not available yet'}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    for y in args or [str(datetime.date.today().year)]:
        print(f"[{y}] OpenF1 sprint qualifying")
        sync(int(y), refresh="--refresh" in sys.argv)
