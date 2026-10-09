"""Session-scope eval: questions that don't name a session are answered for the session on
screen (Race, Sprint, Qualifying, Sprint Qualifying), and explicit mentions override it.

Expected answers come straight from the cached source files (Jolpica, OpenF1), not from the
replay code the agent uses. Covers every cached sprint weekend.

  python tests/eval_session_scope.py
"""
import glob
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app.tools import jolpica_sync as J, openf1_sync as O  # noqa: E402
from app.tools.race_agent import answer_race_engineer_query as ask  # noqa: E402

J._http = lambda url, retries=4: None  # offline: cache only, never write cache
O._http = lambda path, retries=4: None

JOLPICA = os.path.join(ROOT, "data", "cache", "jolpica")
OPENF1 = os.path.join(ROOT, "data", "cache", "openf1")


def _races(path, key):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        races = json.load(f)["MRData"]["RaceTable"]["Races"]
    return races[0] if races and races[0].get(key) else None


def _name_in_question(drv):
    """Surname if plain ASCII (so the question reads naturally), else the three-letter code."""
    fam = drv["familyName"]
    return fam if fam.isascii() else drv.get("code", fam)


def cases():
    out = []
    for p in sorted(glob.glob(os.path.join(JOLPICA, "*_sprint.json"))):
        m = re.match(r"(\d{4})_(\d+)_sprint\.json", os.path.basename(p))
        if not m:
            continue
        y, rnd = int(m.group(1)), int(m.group(2))
        sprint = _races(p, "SprintResults")
        race = _races(os.path.join(JOLPICA, f"{y}_{rnd}_results.json"), "Results")
        quali = _races(os.path.join(JOLPICA, f"{y}_{rnd}_qualifying.json"), "QualifyingResults")
        if not sprint:
            continue
        name = sprint["raceName"]
        by_pos = lambda rows, n: next((x for x in rows if x.get("position") == str(n)), None)
        view = lambda s: {"year": y, "round": rnd, "session": s, "race": name}

        s1, s3 = by_pos(sprint["SprintResults"], 1), by_pos(sprint["SprintResults"], 3)
        out.append(("sprint: who won", view("sprint"), "Who won?", [s1["Driver"]["familyName"], "Sprint"]))
        if s3:
            out.append(("sprint: driver result", view("sprint"), f"How did {_name_in_question(s3['Driver'])} do?",
                        [s3["Driver"]["familyName"], "P3", "Sprint"]))
        if race:
            out.append(("sprint: GP override", view("sprint"), "Who won the grand prix?",
                        [by_pos(race["Results"], 1)["Driver"]["familyName"]]))

        sq_path = os.path.join(OPENF1, f"{y}_{rnd}_sprint_qualifying.json")
        if os.path.exists(sq_path):
            with open(sq_path, encoding="utf-8") as f:
                sq = json.load(f)
            code_to_drv = {x["Driver"]["code"]: x["Driver"] for x in sprint["SprintResults"]}
            pole = code_to_drv.get(sq[0]["driver_code"])
            label = "Sprint Shootout" if y == 2023 else "Sprint Qualifying"
            if pole:
                out.append(("sprint qualifying: fastest", view("sprint_qualifying"), "Who was fastest?",
                            [pole["familyName"], "sprint pole", label]))
            second = code_to_drv.get(sq[1]["driver_code"]) if len(sq) > 1 else None
            if second:
                out.append(("sprint qualifying: driver result", view("sprint_qualifying"),
                            f"How did {_name_in_question(second)} do?", [second["familyName"], "P2", label]))

        if quali:
            q1 = by_pos(quali["QualifyingResults"], 1)
            out.append(("qualifying: who won (pole)", view("qualifying"), "Who won?",
                        [q1["Driver"]["familyName"], "pole", "doesn't have a winner"]))

        if race:
            out.append(("race: who won", view("race"), "Who won?", [by_pos(race["Results"], 1)["Driver"]["familyName"]]))
    # Naming another race overrides the screen entirely
    out.append(("other race named", {"year": 2026, "round": 4, "session": "sprint_qualifying", "race": "Miami Grand Prix"},
                "Who won the 2021 Abu Dhabi Grand Prix?", ["Verstappen"]))
    return out


def main():
    stats = defaultdict(lambda: [0, 0])
    failures = []
    for kind, ctx, q, expect in cases():
        resp = ask(q, ctx, [])
        text = resp.get("text", "")
        ok = all(e.lower() in text.lower() for e in expect)
        stats[kind][0] += ok
        stats[kind][1] += 1
        if not ok:
            # Like the other evals, report the case and what was expected, not the response text.
            failures.append(f"{kind} | {ctx['year']} R{ctx['round']} {ctx['session']} | {q!r} "
                            f"expected {expect} (answered by {resp.get('tool')})")
    for f in failures:
        print("FAIL", f)
    total = [sum(v[0] for v in stats.values()), sum(v[1] for v in stats.values())]
    for kind, (ok, n) in sorted(stats.items()):
        print(f"  {kind:34} {ok:>3}/{n:<3} {100 * ok / n:5.1f}%")
    print(f"TOTAL {total[0]}/{total[1]} = {100 * total[0] / total[1]:.1f}%")
    sys.exit(0 if total[0] == total[1] else 1)


if __name__ == "__main__":
    main()
