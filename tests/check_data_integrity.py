"""Data integrity gate for the cached F1 data (runs offline, no network).

Catches the classes of error found in October 2026: hand-edited or generated files,
standings that disagree with race results, invented sprint grids, synthetic lap timing,
lap/retirement data that contradicts the classification, and files changed outside the
fetcher (manifest check).

Run from anywhere:  python3 tests/check_data_integrity.py [--no-manifest]
Exits non-zero on any failure. Warnings are printed but do not fail the run.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data", "cache", "jolpica")
OPENF1 = os.path.join(ROOT, "data", "cache", "openf1")
MANIFEST = os.path.join(ROOT, "data", "cache", "MANIFEST.json")

failures, warnings = [], []

# Disagreements that exist in the upstream source itself (verified against Jolpica on
# 2026-10-08). The cache keeps an exact copy of the source, so these are reported as
# warnings rather than failures. Add an entry only after checking the live source.
KNOWN_UPSTREAM = {
    ("laps", 2026, 9, "sainz"): "Jolpica lap timing runs to lap 52 but its classification says 51 laps",
}


def fail(msg):
    failures.append(msg)


def warn(msg):
    warnings.append(msg)


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def race(path):
    races = load(path)["MRData"]["RaceTable"]["Races"]
    return races[0] if races else None


def secs(t):
    if not t:
        return None
    m = re.match(r"^(?:(\d+):)?(\d+(?:\.\d+)?)$", t.strip())
    return (int(m.group(1) or 0) * 60 + float(m.group(2))) if m else None


def file_key(path):
    m = re.match(r"(\d{4})_(\d+)_", os.path.basename(path))
    return (int(m.group(1)), int(m.group(2))) if m else None


# ---------------------------------------------------------------- grids & positions
def check_grid(label, rows, year, allow_shared_p1=False):
    grids = [int(r["grid"]) for r in rows if str(r.get("grid", "")).isdigit()]
    positive = [g for g in grids if g > 0]
    dups = sorted({g for g in positive if positive.count(g) > 1})
    # Pre-1970 classifications list shared drives and non-qualifiers with repeated or
    # out-of-range grid slots in the source data itself, so those are warnings, not failures.
    report = warn if year < 1970 else fail
    if dups:
        report(f"{label}: duplicate grid slots {dups}")
    if positive and max(positive) > len(rows):
        report(f"{label}: grid slot {max(positive)} exceeds field size {len(rows)}")
    pos = [int(r["position"]) for r in rows if str(r.get("position", "")).isdigit()]
    pdups = sorted({p for p in pos if pos.count(p) > 1})
    if pdups and not (allow_shared_p1 and year < 1960):
        fail(f"{label}: duplicate finishing positions {pdups}")


def check_results():
    for p in sorted(glob.glob(os.path.join(CACHE, "*_results.json"))):
        y, rnd = file_key(p)
        r = race(p)
        if not r:
            continue
        check_grid(f"{y} R{rnd} race", r["Results"], y, allow_shared_p1=True)


def check_sprints():
    for p in sorted(glob.glob(os.path.join(CACHE, "*_sprint.json"))):
        y, rnd = file_key(p)
        r = race(p)
        if not r:
            continue
        rows = r["SprintResults"]
        check_grid(f"{y} R{rnd} sprint", rows, y)
        same = sum(1 for x in rows if x.get("grid") == x.get("position"))
        if rows and same == len(rows):
            fail(f"{y} R{rnd} sprint: every grid slot equals the finishing position (grid looks invented)")
        if any(not str(x.get("position", "")).isdigit() for x in rows):
            fail(f"{y} R{rnd} sprint: non-numeric 'position' values (not Jolpica format)")
        if any(str((x.get("Time") or {}).get("time", "")).endswith("s") for x in rows):
            fail(f"{y} R{rnd} sprint: gap strings end in 's' (not Jolpica format)")
        sq = os.path.join(OPENF1, f"{y}_{rnd}_sprint_qualifying.json")
        if y >= 2023 and not os.path.exists(sq):
            fail(f"{y} R{rnd}: sprint weekend from 2023 on but no Sprint Qualifying/Shootout file")
        if os.path.exists(sq):
            codes = {x["Driver"].get("code") for x in rows}
            missing = [x["driver_code"] for x in load(sq) if x["driver_code"] not in codes]
            if missing:
                fail(f"{y} R{rnd} sprint qualifying: drivers not in the sprint classification {missing}")


# ---------------------------------------------------------------- laps & pit stops
def check_laps_and_stops():
    for p in sorted(glob.glob(os.path.join(CACHE, "*_laps_all.json"))):
        y, rnd = file_key(p)
        laps = load(p)
        timings = [t for lap in laps for t in lap["Timings"]]
        whole = sum(1 for t in timings if t["time"].endswith(".000"))
        if timings and whole / len(timings) > 0.2:
            fail(f"{y} R{rnd} laps: {whole}/{len(timings)} lap times are whole seconds (synthetic timing)")
        res_path = os.path.join(CACHE, f"{y}_{rnd}_results.json")
        if os.path.exists(res_path):
            r = race(res_path)
            last_lap = defaultdict(int)
            for lap in laps:
                for t in lap["Timings"]:
                    last_lap[t["driverId"]] = max(last_lap[t["driverId"]], int(lap["number"]))
            for x in r["Results"]:
                did, n = x["Driver"]["driverId"], int(x["laps"])
                if did in last_lap and last_lap[did] != n:
                    if ("laps", y, rnd, did) in KNOWN_UPSTREAM:
                        warn(f"{y} R{rnd} laps: {did}: {KNOWN_UPSTREAM[('laps', y, rnd, did)]} (upstream)")
                        continue
                    fail(f"{y} R{rnd} laps: {did} has timing to lap {last_lap[did]} but classification says {n} laps")
    for p in sorted(glob.glob(os.path.join(CACHE, "*_pitstops.json"))):
        y, rnd = file_key(p)
        r = race(p)
        res_path = os.path.join(CACHE, f"{y}_{rnd}_results.json")
        if not r or not os.path.exists(res_path):
            continue
        # Disqualified drivers are recorded with 0 laps although they raced, so skip them
        laps_by = {x["Driver"]["driverId"]: int(x["laps"]) for x in race(res_path)["Results"]
                   if "disqualif" not in x.get("status", "").lower()}
        dsq = {x["Driver"]["driverId"] for x in race(res_path)["Results"] if "disqualif" in x.get("status", "").lower()}
        for s in r.get("PitStops", []):
            if s["driverId"] in dsq:
                continue
            if s["driverId"] not in laps_by:
                fail(f"{y} R{rnd} pit stops: unknown driver {s['driverId']}")
            elif int(s["lap"]) > laps_by[s["driverId"]] + 1:
                fail(f"{y} R{rnd} pit stops: {s['driverId']} stops on lap {s['lap']} after completing {laps_by[s['driverId']]} laps")


# ---------------------------------------------------------------- standings vs results
def check_standings():
    for p in sorted(glob.glob(os.path.join(CACHE, "*_driverStandings.json"))):
        y = int(os.path.basename(p)[:4])
        lst = load(p)["MRData"]["StandingsTable"]["StandingsLists"]
        if not lst or y < 1991:
            continue
        upto = int(lst[0]["round"])
        pts, wins = defaultdict(float), defaultdict(int)
        complete = True
        for rnd in range(1, upto + 1):
            rp = os.path.join(CACHE, f"{y}_{rnd}_results.json")
            if not os.path.exists(rp):
                complete = False
                break
            for x in race(rp)["Results"]:
                pts[x["Driver"]["driverId"]] += float(x["points"])
                if x["position"] == "1":
                    wins[x["Driver"]["driverId"]] += 1
            sp = os.path.join(CACHE, f"{y}_{rnd}_sprint.json")
            if os.path.exists(sp) and race(sp):
                for x in race(sp)["SprintResults"]:
                    pts[x["Driver"]["driverId"]] += float(x["points"])
        if not complete:
            continue
        for s in lst[0]["DriverStandings"]:
            did = s["Driver"]["driverId"]
            if abs(float(s["points"]) - pts[did]) > 0.01 or int(s["wins"]) != wins[did]:
                fail(f"{y} standings: {did} file says {s['points']} pts / {s['wins']} wins, results add up to {pts[did]:g} / {wins[did]}")


def check_winners():
    for p in sorted(glob.glob(os.path.join(CACHE, "*_winners.json"))):
        y = int(os.path.basename(p)[:4])
        for r in load(p)["MRData"]["RaceTable"]["Races"]:
            rp = os.path.join(CACHE, f"{y}_{r['round']}_results.json")
            if os.path.exists(rp) and race(rp):
                w_file = r["Results"][0]["Driver"]["driverId"]
                w_res = [x["Driver"]["driverId"] for x in race(rp)["Results"] if x["position"] == "1"]
                if w_res and w_file not in w_res:
                    fail(f"{y} R{r['round']}: winners file says {w_file}, results say {w_res}")


# ---------------------------------------------------------------- manifest
def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def check_manifest():
    if not os.path.exists(MANIFEST):
        fail("data/cache/MANIFEST.json is missing (run: python -m app.tools.data_manifest --rebuild)")
        return
    man = load(MANIFEST)["files"]
    on_disk = {os.path.relpath(p, os.path.dirname(MANIFEST)).replace(os.sep, "/")
               for p in glob.glob(os.path.join(CACHE, "*.json")) + glob.glob(os.path.join(OPENF1, "*.json"))}
    for rel in sorted(on_disk - set(man)):
        fail(f"{rel}: not in MANIFEST (file added outside the fetcher)")
    for rel, entry in sorted(man.items()):
        path = os.path.join(os.path.dirname(MANIFEST), rel)
        if not os.path.exists(path):
            fail(f"{rel}: in MANIFEST but missing on disk")
        elif sha256(path) != entry["sha256"]:
            fail(f"{rel}: content changed outside the fetcher (sha256 differs from MANIFEST)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-manifest", action="store_true", help="skip the manifest check")
    args = ap.parse_args()
    check_results()
    check_sprints()
    check_laps_and_stops()
    check_standings()
    check_winners()
    if not args.no_manifest:
        check_manifest()
    for w in warnings:
        print("WARN ", w)
    for f in failures:
        print("FAIL ", f)
    print(f"\nData integrity: {len(failures)} failure(s), {len(warnings)} warning(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
