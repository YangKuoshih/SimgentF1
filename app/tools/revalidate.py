"""Re-check cached seasons against Jolpica and replace any file that no longer matches.

Recent races are re-fetched automatically (jolpica_sync.RECENT_DAYS); this covers older
data, where Jolpica can still publish corrections (and where a bad file would otherwise
sit in the cache forever). Each cached file is compared by a normalised fingerprint, so
pure formatting differences do not trigger a rewrite. Corrections are written exactly as
Jolpica serves them and recorded in data/cache/MANIFEST.json.

  python -m app.tools.revalidate 2026 2025 [--laps] [--budget 400] [--dry-run]

Jolpica allows roughly 500 requests per hour; --budget caps the requests used per run.
Exit code 0 = everything matches or was corrected; 2 = budget ran out before finishing.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import sys

from app.tools import jolpica_sync as J

TIME = re.compile(r"^\+?\d+(:\d{2})*(\.\d+)?s?$")


def _nz(v):
    v = (v or "").strip()
    return v.rstrip("s") if v and TIME.match(v) else None


def _fp(rows):
    return hashlib.sha256(json.dumps(rows, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def fingerprint(kind: str, doc) -> str:
    """Same normalisation as the audit run in October 2026."""
    if kind == "laps_all":
        return _fp([[l["number"], t["driverId"], t["position"], t["time"]] for l in doc for t in l["Timings"]])
    if kind in ("driverStandings", "constructorStandings"):
        lists = doc["MRData"]["StandingsTable"]["StandingsLists"]
        key = "DriverStandings" if kind == "driverStandings" else "ConstructorStandings"
        who = (lambda x: x["Driver"]["driverId"]) if kind == "driverStandings" else (lambda x: x["Constructor"]["constructorId"])
        return _fp([lists[0]["round"]] + [[who(x), x["points"], x["wins"]] for x in lists[0][key]] if lists else [])
    races = doc["MRData"]["RaceTable"]["Races"]
    if kind in ("schedule", "winners"):
        if kind == "schedule":
            return _fp([[r["round"], r["raceName"], r["date"], r["Circuit"]["circuitId"], "Sprint" in r] for r in races])
        return _fp([[r["round"], r["Results"][0]["Driver"]["driverId"]] for r in races])
    if not races:
        return _fp([])
    r = races[0]
    if kind == "results":
        rows = [[x["Driver"]["driverId"], x["position"], x["laps"], x["status"], _nz((x.get("Time") or {}).get("time")), x["points"], x["grid"]] for x in r["Results"]]
    elif kind == "sprint":
        rows = [[x["Driver"]["driverId"], x["position"], x["laps"], x["status"], _nz((x.get("Time") or {}).get("time")), x["points"], x["grid"]] for x in r["SprintResults"]]
    elif kind == "qualifying":
        rows = [[x["Driver"]["driverId"], x["position"], _nz(x.get("Q1")), _nz(x.get("Q2")), _nz(x.get("Q3"))] for x in r["QualifyingResults"]]
    elif kind == "pitstops":
        rows = [[x["driverId"], x["lap"], x["stop"], x["duration"]] for x in r.get("PitStops", [])]
    else:
        rows = []
    return _fp(rows)


URLS = {
    "results": "{y}/{r}/results.json?limit=40", "sprint": "{y}/{r}/sprint.json?limit=40",
    "qualifying": "{y}/{r}/qualifying.json?limit=40", "pitstops": "{y}/{r}/pitstops.json?limit=100",
    "schedule": "{y}.json?limit=40", "winners": "{y}/results/1.json?limit=100",
    "driverStandings": "{y}/driverStandings.json?limit=40", "constructorStandings": "{y}/constructorStandings.json?limit=40",
}


def _fetch_laps(y, r, budget):
    merged, offset, total, used = {}, 0, 1, 0
    while offset < total:
        if used >= budget:
            return None, used
        d = J._http(f"{J.BASE}/{y}/{r}/laps.json?limit=100&offset={offset}")
        used += 1
        if not d:
            return None, used
        total = int(d["MRData"]["total"])
        races = d["MRData"]["RaceTable"]["Races"]
        if not races:
            break
        for lap in races[0].get("Laps", []):
            merged.setdefault(lap["number"], {"number": lap["number"], "Timings": []})["Timings"].extend(lap["Timings"])
        offset += 100
    return sorted(merged.values(), key=lambda l: int(l["number"])), used


def revalidate(years, with_laps=False, budget=400, dry_run=False):
    used, corrected, checked, skipped = 0, [], 0, []
    for y in years:
        files = sorted(glob.glob(os.path.join(J.CACHE, f"{y}_*.json")))
        for path in files:
            name = os.path.basename(path)[:-5]
            m = re.match(r"(\d{4})_(?:(\d+)_)?(.+)$", name)
            yr, rnd, kind = m.group(1), m.group(2), m.group(3)
            if kind == "laps_all" and not with_laps:
                continue
            if kind not in URLS and kind != "laps_all":
                continue
            with open(path, encoding="utf-8") as f:
                local = json.load(f)
            if kind == "laps_all":
                remote, n = _fetch_laps(yr, rnd, budget - used)
                used += n
                url = f"{J.BASE}/{yr}/{rnd}/laps.json (all pages merged)"
            else:
                if used >= budget:
                    remote = None
                else:
                    url = f"{J.BASE}/" + URLS[kind].format(y=yr, r=rnd)
                    remote = J._http(url)
                    used += 1
            if remote is None:
                skipped.append(name)
                continue
            checked += 1
            if kind != "laps_all" and kind not in ("schedule", "winners", "driverStandings", "constructorStandings") \
                    and not remote["MRData"]["RaceTable"]["Races"]:
                continue  # Jolpica has nothing (yet) for this file; keep what we have
            if fingerprint(kind, local) != fingerprint(kind, remote):
                corrected.append(name)
                print(f"CORRECTED {name}: cached copy differed from Jolpica")
                if not dry_run:
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(remote, f, indent=None if kind == "laps_all" else 2)
                    J._manifest_record(path, url, note="corrected by revalidate")
    print(f"checked {checked} file(s), corrected {len(corrected)}, skipped {len(skipped)} (budget {used}/{budget})")
    return corrected, skipped


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("years", nargs="+", type=int)
    ap.add_argument("--laps", action="store_true", help="also re-check lap timing (many requests per race)")
    ap.add_argument("--budget", type=int, default=400)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    _, skipped = revalidate(a.years, a.laps, a.budget, a.dry_run)
    sys.exit(2 if skipped else 0)
