"""
Jolpica-F1 (Ergast successor) sync + cache layer.

Fetches REAL data and stores it under data/cache/jolpica so the app works offline:
  - season schedule            /{year}.json
  - full race classification   /{year}/{round}/results.json
  - pit stops                  /{year}/{round}/pitstops.json
  - lap-by-lap timing          /{year}/{round}/laps.json   (paginated)
  - driver / constructor standings

Usage:
  .venv/bin/python -m app.tools.jolpica_sync 2026 2025 2024 [--laps]
"""

import datetime
import glob
import json
import logging
import os
import re
import urllib.parse
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("simgent.jolpica")

BASE = "https://api.jolpi.ca/ergast/f1"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE = os.path.join(ROOT, "data", "cache", "jolpica")
os.makedirs(CACHE, exist_ok=True)

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_HTTP_OPENER = urllib.request.build_opener(_NoRedirect)
_last_call = 0.0


def _path(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_]+", name):
        raise ValueError("Invalid cache key")
    return os.path.join(CACHE, name.replace("/", "_") + ".json")


def _http(url: str, retries: int = 4) -> Optional[Dict[str, Any]]:
    """Polite GET (Jolpica allows ~4 req/s burst, 500/h)."""
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc != "api.jolpi.ca" or not parsed.path.startswith("/ergast/f1/"):
        raise ValueError("Untrusted data URL")
    global _last_call
    for attempt in range(retries):
        wait = 0.3 - (time.time() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "F1-Simgent/1.0"})
            with _HTTP_OPENER.open(req, timeout=12) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            # HTTPError owns a response stream too; release it before retrying.
            e.close()
            if e.code == 429:
                logger.warning(f"⚠️ [JOLPICA 429 RATE LIMIT] Rate limited on {url}. Backing off {5 * (attempt + 1)}s (attempt {attempt + 1}/{retries})")
                time.sleep(5 * (attempt + 1))
                continue
            logger.error(f"❌ [JOLPICA HTTP ERROR {e.code}] Request failed for {url}: {e.reason}")
            return None
        except Exception as e:
            logger.warning(f"⚠️ [JOLPICA RETRY] Attempt {attempt + 1}/{retries} failed for {url}: {e}")
            time.sleep(1.5)
    logger.error(f"❌ [JOLPICA EXHAUSTED] All {retries} retry attempts failed for {url}")
    return None


def _manifest_record(path: str, source: str, note: Optional[str] = None) -> None:
    try:
        from app.tools import data_manifest
        data_manifest.record(path, source, note)
    except Exception as e:  # provenance must never break serving
        logger.warning(f"⚠️ [MANIFEST] could not record {path}: {e}")


def _manifest_forget(path: str) -> None:
    try:
        from app.tools import data_manifest
        data_manifest.forget(path)
    except Exception:
        pass


# Re-fetch window for recent events: Jolpica and the FIA correct classifications after a
# race (penalties, disqualifications, appeals), so recent files must not be cached forever.
RECENT_DAYS = 21
RECENT_MAX_AGE_S = 6 * 3600


def _recent_max_age(year: int, rnd: int) -> Optional[float]:
    """6 hours for events in the last RECENT_DAYS days, else cache forever (older data is
    re-checked by revalidate())."""
    import datetime as _dt
    p = _path(f"{year}_schedule")
    if not os.path.exists(p):
        return None
    try:
        with open(p) as f:
            races = json.load(f)["MRData"]["RaceTable"]["Races"]
        r = next((x for x in races if int(x["round"]) == rnd), None)
        if not r:
            return None
        age_days = (_dt.date.today() - _dt.date.fromisoformat(r["date"])).days
        return RECENT_MAX_AGE_S if 0 <= age_days <= RECENT_DAYS else None
    except Exception:
        return None


def cached(name: str, url: str, allow_network: bool = True, max_age_s: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """Read from cache, else fetch & store. max_age_s=None means cache forever."""
    p = _path(name)
    if os.path.exists(p):
        fresh = max_age_s is None or (time.time() - os.path.getmtime(p)) < max_age_s
        if fresh or not allow_network:
            logger.debug(f"⚡ [CACHE HIT] {name} from {p}")
            with open(p) as f:
                return json.load(f)
    if not allow_network:
        logger.debug(f"🛑 [CACHE MISS (NO NET)] {name} not in cache and network disabled.")
        return None
    logger.info(f"🌐 [CACHE MISS] Fetching '{name}' upstream: {url}")
    data = _http(url)
    if data is not None:
        try:
            with open(p, "w") as f:
                json.dump(data, f)
            _manifest_record(p, url)
            logger.info(f"💾 [CACHE WRITE] Saved '{name}' to {p}")
        except Exception as e:
            logger.warning(f"⚠️ [CACHE WRITE ERROR] Could not persist {p}: {e}")
        return data
    if os.path.exists(p):  # stale fallback
        logger.warning(f"⚠️ [CACHE STALE FALLBACK] Serving stale cache for '{name}'")
        with open(p) as f:
            return json.load(f)
    return None


# ---------------------------------------------------------------- accessors
def schedule(year: int, net: bool = True) -> List[Dict[str, Any]]:
    # Refresh daily for every season. (A former rule froze the 2026 schedule against the API,
    # which is how a hand-edited calendar was kept out of reach of corrections.)
    d = cached(f"{year}_schedule", f"{BASE}/{year}.json?limit=40", net, max_age_s=86400)
    return d["MRData"]["RaceTable"]["Races"] if d else []


def _had_recent_race(year: int) -> bool:
    """True when a round of this season ran in the last RECENT_DAYS days."""
    import datetime as _dt
    p = _path(f"{year}_schedule")
    if not os.path.exists(p):
        return False
    try:
        with open(p) as f:
            races = json.load(f)["MRData"]["RaceTable"]["Races"]
        today = _dt.date.today()
        return any(0 <= (today - _dt.date.fromisoformat(r["date"])).days <= RECENT_DAYS for r in races)
    except Exception:
        return False


def season_winners(year: int, net: bool = True) -> Dict[int, Dict[str, Any]]:
    """Fetches P1 winners for all rounds of a season in ONE request. Refreshed every
    RECENT_MAX_AGE_S while the season has recent races, so a restarted server (which only
    has the data baked into its image) still picks up races run since the last deploy."""
    d = cached(f"{year}_winners", f"{BASE}/{year}/results/1.json?limit=100", net,
               max_age_s=RECENT_MAX_AGE_S if _had_recent_race(year) else None)
    if not d:
        return {}
    races = d.get("MRData", {}).get("RaceTable", {}).get("Races", [])
    out = {}
    for r in races:
        if r.get("Results"):
            out[int(r["round"])] = r["Results"][0]
    return out


def _heal_race_circuit(name: str, doc: Optional[Dict[str, Any]], year: int, rnd: int) -> None:
    """Auto-heals inconsistent circuit IDs or race names directly in cached Jolpica structures."""
    if not doc:
        return
    races = doc.get("MRData", {}).get("RaceTable", {}).get("Races", [])
    if not races:
        return
    race = races[0]
    rn = race.get("raceName", "").lower()
    circ = race.get("Circuit")
    if not circ:
        return
    changed = False
    # The 2026 "Bahrain Grand Prix in Malaysia" really was run at Sepang (relocated by the
    # 2026 Iran war) and Jolpica now lists it there. Rewriting it to Sakhir corrupted the
    # official record, so leave the relocated event exactly as Jolpica publishes it.
    if "malaysia" in rn or circ.get("circuitId") == "sepang":
        return
    if ("bahrain" in rn or "sakhir" in rn) and circ.get("circuitId") != "bahrain":
        circ["circuitId"] = "bahrain"
        circ["circuitName"] = "Bahrain International Circuit"
        circ["url"] = "https://en.wikipedia.org/wiki/Bahrain_International_Circuit"
        circ["Location"] = {
            "lat": "26.0325",
            "long": "50.5106",
            "locality": "Sakhir",
            "country": "Bahrain"
        }
        if "malaysia" in rn:
            race["raceName"] = f"{year} Bahrain Grand Prix"
        changed = True

    if changed:
        p = _path(name)
        try:
            with open(p, "w") as f:
                json.dump(doc, f, indent=2)
            _manifest_record(p, doc.get("MRData", {}).get("url", "jolpica"), note="circuit id normalised by _heal_race_circuit")
        except OSError:
            pass


def results(year: int, rnd: int, net: bool = True) -> Optional[Dict[str, Any]]:
    name = f"{year}_{rnd}_results"
    d = cached(name, f"{BASE}/{year}/{rnd}/results.json?limit=40", net, max_age_s=_recent_max_age(year, rnd))
    _heal_race_circuit(name, d, year, rnd)
    races = d["MRData"]["RaceTable"]["Races"] if d else []
    if not races:
        # Do not cache "not yet raced" forever
        p = _path(name)
        if os.path.exists(p):
            os.remove(p)
            _manifest_forget(p)
        return None
    return races[0]


def sprint_results(year: int, rnd: int, net: bool = True) -> Optional[Dict[str, Any]]:
    """Fetches official FIA Sprint Race results if the weekend had a Sprint."""
    name = f"{year}_{rnd}_sprint"
    d = cached(name, f"{BASE}/{year}/{rnd}/sprint.json?limit=40", net, max_age_s=_recent_max_age(year, rnd))
    _heal_race_circuit(name, d, year, rnd)
    races = d["MRData"]["RaceTable"]["Races"] if d else []
    if not races or "SprintResults" not in races[0]:
        p = _path(name)
        if os.path.exists(p):
            try:
                os.remove(p)
                _manifest_forget(p)
            except OSError:
                pass
        return _sprint_from_openf1(year, rnd, net)
    return races[0]


OPENF1_CACHE = os.path.join(os.path.dirname(CACHE), "openf1")
_OPENF1_TRIED: Dict[Tuple[int, int, str], float] = {}


def _openf1_rows(year: int, rnd: int, session: str, net: bool) -> Optional[List[Dict[str, Any]]]:
    """OpenF1 rows for a session Jolpica hasn't published, fetched on demand at most every
    10 minutes per session (OpenF1 closes during live sessions; don't hammer it)."""
    path = os.path.join(OPENF1_CACHE, f"{year}_{rnd}_{session}.json")
    if not os.path.exists(path) and net and year >= 2023:
        last = _OPENF1_TRIED.get((year, rnd, session), 0.0)
        if time.time() - last > 600:
            _OPENF1_TRIED[(year, rnd, session)] = time.time()
            try:
                from app.tools import openf1_sync
                when = openf1_sync.scheduled(year, rnd, session)
                if when and when.get("date", "9999") <= datetime.date.today().isoformat():
                    openf1_sync.fetch_session(year, rnd, session)
            except Exception as e:
                logger.warning(f"⚠️ [OPENF1] {session} fetch failed for {year} R{rnd}: {e}")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _season_people(year: int, rnd: int) -> Dict[str, Tuple[Dict[str, Any], Dict[str, Any]]]:
    """Car number -> (Jolpica Driver, Constructor) from this season's cached results, the
    nearest earlier round winning (seat changes), later rounds only as a fallback."""
    found = []
    for f in glob.glob(os.path.join(CACHE, f"{year}_*_*.json")):
        m = re.match(rf"{year}_(\d+)_(results|sprint|qualifying)\.json$", os.path.basename(f))
        if m:
            found.append((int(m.group(1)), f))
    order = sorted((x for x in found if x[0] <= rnd), reverse=True) + sorted(x for x in found if x[0] > rnd)
    people: Dict[str, Tuple[Dict[str, Any], Dict[str, Any]]] = {}
    for _, f in order:
        try:
            with open(f, encoding="utf-8") as fh:
                races = json.load(fh)["MRData"]["RaceTable"]["Races"]
        except (OSError, ValueError, KeyError):
            continue
        for race in races:
            for row in race.get("Results", []) + race.get("SprintResults", []) + race.get("QualifyingResults", []):
                num = str(row.get("number") or row["Driver"].get("permanentNumber") or "")
                if num and num not in people:
                    people[num] = (row["Driver"], row["Constructor"])
    return people


def _person(r: Dict[str, Any], people) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Jolpica-style Driver/Constructor for an OpenF1 row (minimal record if unknown)."""
    if r.get("num") in people:
        driver, constructor = people[r["num"]]
        if not r.get("driver_code") or driver.get("code") == r.get("driver_code"):
            return driver, constructor
    given, _, family = (r.get("driver_name") or r.get("driver_code", "")).partition(" ")
    return ({"driverId": (r.get("driver_code") or "").lower(), "code": r.get("driver_code", ""),
             "permanentNumber": r.get("num", ""), "givenName": given.title(), "familyName": (family or given).title()},
            {"constructorId": (r.get("team") or "").lower().replace(" ", "_"), "name": r.get("team", "")})


def _event(year: int, rnd: int, net: bool) -> Dict[str, Any]:
    return next((r for r in schedule(year, net) if str(r.get("round")) == str(rnd)), {})


def _sprint_from_openf1(year: int, rnd: int, net: bool) -> Optional[Dict[str, Any]]:
    """Sprint result from OpenF1 while Jolpica hasn't published it, in Jolpica's format.
    The grid comes from OpenF1's position feed (see openf1_sync.fetch_session); if that is
    missing, the Sprint Qualifying order is used."""
    rows = _openf1_rows(year, rnd, "sprint", net)
    if not rows:
        return None
    people = _season_people(year, rnd)
    sq = _openf1_rows(year, rnd, "sprint_qualifying", False) or []
    grid = {x.get("num"): str(i + 1) for i, x in enumerate(sq)}
    out = []
    for i, r in enumerate(rows):
        driver, constructor = _person(r, people)
        row = {"number": r["num"], "position": str(i + 1), "positionText": r["pos"],
               "points": str(r.get("points") or 0).removesuffix(".0"), "Driver": driver, "Constructor": constructor,
               "grid": r.get("grid") or grid.get(r["num"], "0"), "laps": str(r.get("laps", 0)), "status": r["status"]}
        if r.get("time"):
            row["Time"] = {"time": r["time"], **({"millis": str(r["millis"])} if r.get("millis") else {})}
        out.append(row)
    ev = _event(year, rnd, net)
    return {"season": str(year), "round": str(rnd), "raceName": ev.get("raceName", f"Round {rnd}"),
            "date": (ev.get("Sprint") or {}).get("date", ev.get("date", "")), "Circuit": ev.get("Circuit", {}),
            "source": "OpenF1 (Jolpica not published yet)", "SprintResults": out}


def _quali_rows(rows: List[Dict[str, Any]], people) -> List[Dict[str, Any]]:
    """OpenF1 qualifying-type rows -> Jolpica QualifyingResults rows."""
    out = []
    for i, r in enumerate(rows):
        driver, constructor = _person(r, people)
        pos = r.get("pos", "")
        row = {"number": r.get("num", ""), "position": pos if pos.isdigit() else str(i + 1), "positionText": pos,
               "Driver": driver, "Constructor": constructor, "Q1": r.get("q1", ""), "laps": r.get("laps", 0)}
        # Same convention as Jolpica: a Q2/Q3 field exists only if the driver reached that
        # segment ("DNF"/"DNS" there when they reached it but set no time).
        if r.get("q2"):
            row["Q2"] = r["q2"]
        if r.get("q3"):
            row["Q3"] = r["q3"]
        out.append(row)
    return out


def _qualifying_from_openf1(year: int, rnd: int, net: bool) -> Optional[Dict[str, Any]]:
    """Grand Prix qualifying from OpenF1 while Jolpica hasn't published it, in Jolpica's format."""
    rows = _openf1_rows(year, rnd, "qualifying", net)
    if not rows:
        return None
    ev = _event(year, rnd, net)
    out = _quali_rows(rows, _season_people(year, rnd))
    for row in out:  # Jolpica's Grand Prix qualifying leaves a reached-but-no-time segment empty
        for seg in ("Q1", "Q2", "Q3"):
            if row.get(seg) in ("DNF", "DNS"):
                row[seg] = ""
    return {"season": str(year), "round": str(rnd), "raceName": ev.get("raceName", f"Round {rnd}"),
            "date": (ev.get("Qualifying") or {}).get("date", ev.get("date", "")), "Circuit": ev.get("Circuit", {}),
            "source": "OpenF1 (Jolpica not published yet)", "QualifyingResults": out}


def sprint_qualifying(year: int, rnd: int, net: bool = True) -> Optional[Dict[str, Any]]:
    """Sprint Qualifying (2024+) / Sprint Shootout (2023) classification.

    Jolpica does not publish this session, so it comes from the free OpenF1 API
    (cached as openf1/{year}_{rnd}_sprint_qualifying.json by app.tools.openf1_sync).
    Driver and constructor records are joined from the Jolpica sprint result for the same
    weekend, so the rows look like Jolpica QualifyingResults (Q1/Q2/Q3 = SQ1/SQ2/SQ3).
    Returns None when the weekend had no such session (pre-2023, or not a sprint weekend).
    """
    path = os.path.join(OPENF1_CACHE, f"{year}_{rnd}_sprint_qualifying.json")
    if not os.path.exists(path) and net and year >= 2023:
        try:  # not cached yet (e.g. the session ran since the last scheduled sync)
            from app.tools import openf1_sync
            openf1_sync.fetch_sprint_qualifying(year, rnd)
        except Exception as e:
            logger.warning(f"⚠️ [OPENF1] sprint qualifying fetch failed for {year} R{rnd}: {e}")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        rows = json.load(f)
    meta = {}
    meta_path = os.path.join(OPENF1_CACHE, "sprint_qualifying_meta.json")
    if os.path.exists(meta_path):
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f).get(f"{year}_{rnd}", {})
    sprint = sprint_results(year, rnd, net) or {}
    out_rows = _quali_rows(rows, _season_people(year, rnd))
    # Sprint Qualifying runs before the sprint, so on Friday/Saturday the sprint result (and
    # its race name, date and circuit) may not exist yet; the season schedule always has them.
    event = sprint or next((r for r in schedule(year, net) if str(r.get("round")) == str(rnd)), {})
    return {
        "season": str(year), "round": str(rnd),
        "raceName": event.get("raceName", f"Round {rnd}"),
        "date": event.get("date", ""), "Circuit": event.get("Circuit", {}),
        "session": meta.get("session") or ("Sprint Shootout" if year == 2023 else "Sprint Qualifying"),
        "notes": meta.get("notes", []),
        "source_url": meta.get("source_url", ""),
        "QualifyingResults": out_rows,
    }


def qualifying_results(year: int, rnd: int, net: bool = True) -> Optional[Dict[str, Any]]:
    """Fetches official FIA Qualifying results (Q1, Q2, Q3 lap times and grid)."""
    name = f"{year}_{rnd}_qualifying"
    d = cached(name, f"{BASE}/{year}/{rnd}/qualifying.json?limit=40", net, max_age_s=_recent_max_age(year, rnd))
    _heal_race_circuit(name, d, year, rnd)
    races = d["MRData"]["RaceTable"]["Races"] if d else []
    if not races or "QualifyingResults" not in races[0]:
        p = _path(name)
        if os.path.exists(p):
            try:
                os.remove(p)
                _manifest_forget(p)
            except OSError:
                pass
        return _qualifying_from_openf1(year, rnd, net)
    return races[0]


def pitstops(year: int, rnd: int, net: bool = True) -> List[Dict[str, Any]]:
    d = cached(f"{year}_{rnd}_pitstops", f"{BASE}/{year}/{rnd}/pitstops.json?limit=100", net, max_age_s=_recent_max_age(year, rnd))
    races = d["MRData"]["RaceTable"]["Races"] if d else []
    return races[0].get("PitStops", []) if races else []


def laps(year: int, rnd: int, net: bool = True) -> List[Dict[str, Any]]:
    """Full lap-by-lap timing; merged across pages and cached as one file."""
    name = f"{year}_{rnd}_laps_all"
    p = _path(name)
    max_age = _recent_max_age(year, rnd)
    stale = net and max_age is not None and os.path.exists(p) and (time.time() - os.path.getmtime(p)) > max_age
    if os.path.exists(p) and not stale:
        with open(p) as f:
            data = json.load(f)
            if isinstance(data, dict):
                races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
                return races[0].get("Laps", []) if races else []
            return data
    if not net:
        return []
    merged: Dict[str, Dict[str, Any]] = {}
    offset, total = 0, 1
    while offset < total:
        d = _http(f"{BASE}/{year}/{rnd}/laps.json?limit=100&offset={offset}")
        if not d:
            return []
        total = int(d["MRData"]["total"])
        races = d["MRData"]["RaceTable"]["Races"]
        if not races:
            break
        for lap in races[0].get("Laps", []):
            merged.setdefault(lap["number"], {"number": lap["number"], "Timings": []})
            merged[lap["number"]]["Timings"].extend(lap["Timings"])
        offset += 100
    out = sorted(merged.values(), key=lambda l: int(l["number"]))
    if out:
        with open(p, "w") as f:
            json.dump(out, f)
        _manifest_record(p, f"{BASE}/{year}/{rnd}/laps.json (all pages merged)")
    return out


def driver_standings(year: int, net: bool = True) -> List[Dict[str, Any]]:
    d = cached(f"{year}_driverStandings", f"{BASE}/{year}/driverStandings.json?limit=40", net, max_age_s=3600)
    lists = d["MRData"]["StandingsTable"]["StandingsLists"] if d else []
    return lists[0]["DriverStandings"] if lists else []


def constructor_standings(year: int, net: bool = True) -> List[Dict[str, Any]]:
    d = cached(f"{year}_constructorStandings", f"{BASE}/{year}/constructorStandings.json?limit=40", net, max_age_s=3600)
    lists = d["MRData"]["StandingsTable"]["StandingsLists"] if d else []
    return lists[0]["ConstructorStandings"] if lists else []


def sync(year: int, with_laps: bool) -> None:
    races = schedule(year)
    print(f"[{year}] {len(races)} rounds on calendar")
    driver_standings(year)
    constructor_standings(year)
    for r in races:
        rnd = int(r["round"])
        res = results(year, rnd)
        if not res:
            print(f"  R{rnd:>2} {r['raceName']}: not raced yet")
            continue
        pitstops(year, rnd)
        n_laps = len(laps(year, rnd)) if with_laps else 0
        sprint_txt = ""
        if "Sprint" in r:
            # Sprint result (incl. the official sprint grid) from Jolpica, plus the Sprint
            # Qualifying / Shootout session from OpenF1 (Jolpica does not publish it).
            spr = sprint_results(year, rnd)
            sprint_txt = f", sprint={'yes' if spr else 'missing'}"
            if year >= 2023:
                try:
                    from app.tools import openf1_sync
                    sq = openf1_sync.fetch_sprint_qualifying(year, rnd)
                    sprint_txt += f", sprint_qualifying={'yes' if sq else 'missing'}"
                except Exception as e:  # never let the optional OpenF1 fetch break the sync
                    sprint_txt += f", sprint_qualifying=error ({e})"
        print(f"  R{rnd:>2} {r['raceName']}: {len(res['Results'])} classified, laps={n_laps}{sprint_txt}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    for y in args or ["2026"]:
        sync(int(y), with_laps="--laps" in sys.argv)
