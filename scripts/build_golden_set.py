"""Build data/f1db_facts.json: the answer key for tests/eval_golden.py, which the answer gate
(app/agent/gate.py) also checks answers against at run time.

The answers come from F1DB (https://github.com/f1db/f1db, CC BY 4.0), a source the agent does
not read (it answers from Jolpica-F1), so the eval checks the agent against independent data.
Release pinned and checked by SHA-256, the same one scripts/build_circuit_layouts.py uses.

    python scripts/build_golden_set.py
"""

import collections
import csv
import hashlib
import io
import json
import os
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "f1db_facts.json")
F1DB_TAG = "v2026.17.0"
F1DB_URL = f"https://github.com/f1db/f1db/releases/download/{F1DB_TAG}/f1db-csv.zip"
F1DB_SHA256 = "1c5c07d064e2988cb31a44206cc679662e0523a9bde0c191eed8ffc22831eec6"


def main():
    with urllib.request.urlopen(urllib.request.Request(F1DB_URL, headers={"User-Agent": "simgent-build"}), timeout=120) as r:
        data = r.read()
    if hashlib.sha256(data).hexdigest() != F1DB_SHA256:
        raise SystemExit("F1DB checksum mismatch")
    z = zipfile.ZipFile(io.BytesIO(data))
    read = lambda name: list(csv.DictReader(io.TextIOWrapper(z.open(f"f1db-{name}.csv"), encoding="utf-8")))

    drivers = {d["id"]: d for d in read("drivers")}
    circuits = {c["id"]: c for c in read("circuits")}
    person = lambda did: {"first": drivers[did]["firstName"], "last": drivers[did]["lastName"]}

    results = collections.defaultdict(list)
    for r in read("races-race-results"):
        results[(r["year"], r["round"])].append(r)
    grid = collections.defaultdict(list)
    for g in read("races-starting-grid-positions"):
        grid[(g["year"], g["round"])].append(g)
    fastest = {(f["year"], f["round"]): f for f in read("races-fastest-laps") if f["positionNumber"] == "1"}

    races = {}
    for race in read("races"):
        key = (race["year"], race["round"])
        rows = results.get(key)
        if not rows:
            continue  # not run yet
        winner = next((r for r in rows if r["positionNumber"] == "1"), None)
        if not winner:
            continue
        g = grid.get(key, [])
        poles = []
        for row in sorted(g, key=lambda x: int(x["qualificationPositionNumber"] or 99)):
            if row["qualificationPositionNumber"] == "1":
                poles.append(row["driverId"])
        poles += [row["driverId"] for row in g if row["positionNumber"] == "1" and row["driverId"] not in poles]
        lasts = collections.Counter(drivers[r["driverId"]]["lastName"] for r in rows)
        fl = fastest.get(key)
        c = circuits[race["circuitId"]]
        races[f"{race['year']}_{race['round']}"] = {
            # every driver classified P1 (shared drives in the 1950s: Fangio and Musso, 1956 Argentina)
            "winners": [person(r["driverId"]) for r in rows if r["positionNumber"] == "1"],
            "pole": [person(p) for p in poles],
            "fastest_lap": dict(person(fl["driverId"]), time=fl["time"], lap=int(fl["lap"]) if fl["lap"] else None) if fl else None,
            "laps": int(race["laps"]) if race["laps"] else None,
            "circuit_names": sorted({c["name"], c["fullName"], *filter(None, (c["previousNames"] or "").split(","))}),
            # last names more than one driver in this race had (Hill, Schumacher, Fittipaldi...)
            "shared_last_names": sorted(n for n, k in lasts.items() if k > 1),
            # every lap time F1DB has for the race (qualifying/grid times, fastest lap): an answer
            # quoting any other lap time has invented it
            "lap_times": sorted({t for t in [row["time"] for row in g] + [fl["time"] if fl else ""] if t}),
            # comeback answers: the podium and every finisher who gained 5+ places, with grid slot
            # (None = started from the pit lane). Shared drives (1950s car swaps) have no grid slot
            # of their own and are left out.
            "comebacks": [dict(person(r["driverId"]), grid=int(r["gridPositionNumber"]) if r["gridPositionNumber"] else None,
                               finish=int(r["positionNumber"]))
                          for r in rows if r["positionNumber"] and r["sharedCar"] != "true"
                          and (int(r["positionNumber"]) <= 3
                               or not r["gridPositionNumber"]
                               or int(r["gridPositionNumber"]) - int(r["positionNumber"]) >= 5)],
        }

    # Drivers entered each season, and all-time drivers with 20+ starts: the answer gate asks which
    # driver is meant when a bare last name fits more than one (Michael or Ralf Schumacher)
    season_drivers = collections.defaultdict(set)
    for e in read("seasons-entrants-drivers"):
        if e["testDriver"] != "true":
            d = drivers[e["driverId"]]
            season_drivers[e["year"]].add((d["firstName"], d["lastName"]))
    notable = sorted({(d["firstName"], d["lastName"]) for d in drivers.values() if int(d["totalRaceStarts"] or 0) >= 20})

    # Career totals for every driver who started a Grand Prix (career-metric answers)
    driver_totals = sorted(({"first": d["firstName"], "last": d["lastName"], "starts": int(d["totalRaceStarts"] or 0),
                             "wins": int(d["totalRaceWins"] or 0), "poles": int(d["totalPolePositions"] or 0),
                             "podiums": int(d["totalPodiums"] or 0), "titles": int(d["totalChampionshipWins"] or 0),
                             "fastest_laps": int(d["totalFastestLaps"] or 0),
                             "seasons": sorted(int(y) for y, v in season_drivers.items() if (d["firstName"], d["lastName"]) in v)}
                            for d in drivers.values() if int(d["totalRaceStarts"] or 0) > 0),
                           key=lambda x: (x["last"], x["first"]))
    for t in driver_totals:
        t["seasons"] = [t["seasons"][0], t["seasons"][-1]] if t["seasons"] else []
    last_race = max(races, key=lambda k: tuple(map(int, k.split("_"))))
    last_name = next(r["officialName"] for r in read("races") if f"{r['year']}_{r['round']}" == last_race)

    champions = {}
    for s in read("seasons-driver-standings"):
        if s["championshipWon"] == "true":
            champions[s["year"]] = person(s["driverId"])

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"source": {"f1db": F1DB_TAG, "license": "CC-BY-4.0", "url": "https://github.com/f1db/f1db"},
                   "races": races, "champions": champions,
                   "season_drivers": {y: sorted(v) for y, v in season_drivers.items()},
                   "drivers": driver_totals, "facts_through": {"race": last_race, "name": last_name},
                   "notable_drivers": notable}, f, ensure_ascii=False, indent=0, sort_keys=True)
        f.write("\n")
    print(f"wrote {os.path.relpath(OUT, ROOT)}: {len(races)} races, {len(champions)} champions")


if __name__ == "__main__":
    main()
