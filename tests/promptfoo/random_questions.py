"""Random playground questions: races drawn from every season since 1950, asked in varied
phrasings, each carrying its race and category so tests/promptfoo/checks.py can grade it against
F1DB. Change the mix with PLAYGROUND_N (default 30) and PLAYGROUND_SEED (default: a new sample
every run; the seed is in each description so a run can be repeated).
"""

import json
import os
import random
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PHRASINGS = {
    "winner": ["Who won the {race}?", "winner of the {race}?", "who took the chequered flag at the {race}?",
               "who finished first at the {race}?", "{place} {year} winner?", "who won {short} {year}?"],
    "pole": ["Who was on pole for the {race}?", "who started on pole at the {race}?", "pole sitter at the {race}?",
             "who took pole position at {short} {year}?"],
    "fastest_lap": ["Who set the fastest lap at the {race}?", "fastest lap at the {race}?",
                    "who had the fastest lap in the {race}?"],
    "laps": ["How many laps was the {race}?", "how many laps did the {race} have?", "number of laps in the {race}?"],
    "circuit": ["Which circuit hosted the {race}?", "where was the {race} held?", "what track was the {race} on?"],
}
CHAMPION = ["Who won the {year} drivers' championship?", "{year} world champion?", "who was the F1 champion in {year}?"]


def generate_tests(config=None):
    n = int(os.environ.get("PLAYGROUND_N", "30"))
    seed = int(os.environ.get("PLAYGROUND_SEED", str(int(time.time()))))
    rng = random.Random(seed)
    with open(os.path.join(ROOT, "data", "f1db_facts.json"), encoding="utf-8") as f:
        truth = json.load(f)
    sched = {}
    for name in os.listdir(os.path.join(ROOT, "data", "cache", "jolpica")):
        if name.endswith("_schedule.json"):
            with open(os.path.join(ROOT, "data", "cache", "jolpica", name), encoding="utf-8") as f:
                for r in json.load(f)["MRData"]["RaceTable"]["Races"]:
                    sched[f"{r['season']}_{r['round']}"] = r
    keys = sorted(k for k in truth["races"] if k in sched)
    tests = []
    for i in range(n):
        if rng.random() < 0.08:
            year = rng.choice(sorted(truth["champions"]))
            q = rng.choice(CHAMPION).format(year=year)
            tests.append({"description": f"random #{i + 1} (seed {seed}) - champion {year}",
                          "vars": {"question": q, "year": int(year), "category": "champion"}})
            continue
        key = rng.choice(keys)
        r, t = sched[key], truth["races"][key]
        cats = [c for c in PHRASINGS if (c != "pole" or t["pole"]) and (c != "fastest_lap" or t["fastest_lap"])]
        cat = rng.choice(cats)
        year = int(r["season"])
        q = rng.choice(PHRASINGS[cat]).format(
            race=f"{year} {r['raceName']}", year=year, short=r["raceName"].replace("Grand Prix", "GP"),
            place=r["Circuit"]["Location"]["locality"])
        tests.append({"description": f"random #{i + 1} (seed {seed}) - {cat} {year} {r['raceName']}",
                      "vars": {"question": q, "year": year, "round": int(r["round"]), "category": cat}})
    return tests
