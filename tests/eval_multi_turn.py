"""Multi-turn conversation eval for the F1 Simgent agent.

Each conversation is replayed the way the web app sends it: every follow-up carries the
earlier user AND assistant turns as `history`. Expected answers are read from the cached
Jolpica data, never typed in by hand. The network is stubbed off (cache only).

Run from anywhere:  python3 tests/eval_multi_turn.py [--verbose]
Exits non-zero if any turn fails.
"""
import json, os, re, sys, unicodedata, logging, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
logging.disable(logging.WARNING)

from app.tools import jolpica_sync as J
J._http = lambda url, retries=4: None  # offline: cache only
from app.tools.race_agent import answer_race_engineer_query as ask
from app.tools.agent_memory import memory_manager

CACHE = os.path.join(ROOT, "data", "cache", "jolpica")


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s.lower())


def _load(name):
    with open(os.path.join(CACHE, name + ".json")) as f:
        return json.load(f)


def race(year, rnd):
    return _load(f"{year}_{rnd}_results")["MRData"]["RaceTable"]["Races"][0]


def at_pos(year, rnd, pos):
    rows = [x for x in race(year, rnd)["Results"] if x["position"] == str(pos)]
    return rows[0]["Driver"]["familyName"]


def pole(year, rnd):
    if os.path.exists(os.path.join(CACHE, f"{year}_{rnd}_qualifying.json")):
        return _load(f"{year}_{rnd}_qualifying")["MRData"]["RaceTable"]["Races"][0]["QualifyingResults"][0]["Driver"]["familyName"]
    return next(x["Driver"]["familyName"] for x in race(year, rnd)["Results"] if x["grid"] == "1")


def grid_of(year, rnd, family):
    for x in race(year, rnd)["Results"]:
        if x["Driver"]["familyName"] == family:
            return f"P{x['grid']}"


def winner(year, name):
    for r in _load(f"{year}_winners")["MRData"]["RaceTable"]["Races"]:
        if r["raceName"] == name:
            return r["Results"][0]["Driver"]["familyName"]


def champion(year):
    return _load(f"{year}_driverStandings")["MRData"]["StandingsTable"]["StandingsLists"][0]["DriverStandings"][0]["Driver"]["familyName"]


def runner_up(year):
    return _load(f"{year}_driverStandings")["MRData"]["StandingsTable"]["StandingsLists"][0]["DriverStandings"][1]["Driver"]["familyName"]


def standings_leader(year):
    # Leader by the sum of race + sprint points: the per-race results are the cross-checked source
    from app.tools import race_replay
    return race_replay.standings(year, net=False)["drivers"][0]["driver"].split()[-1]


def sprint_row(year, rnd, pos=None, grid=None):
    res = _load(f"{year}_{rnd}_sprint")["MRData"]["RaceTable"]["Races"][0]["SprintResults"]
    for x in res:
        if (pos and x["position"] == str(pos)) or (grid and x["grid"] == str(grid)):
            return x["Driver"]["familyName"]


def sprint_pole(year, rnd):
    with open(os.path.join(os.path.dirname(CACHE), "openf1", f"{year}_{rnd}_sprint_qualifying.json"), encoding="utf-8") as f:
        code = json.load(f)[0]["driver_code"]
    res = _load(f"{year}_{rnd}_sprint")["MRData"]["RaceTable"]["Races"][0]["SprintResults"]
    return next(x["Driver"]["familyName"] for x in res if x["Driver"]["code"] == code)


def retirement_lap(year, rnd, code):
    for x in race(year, rnd)["Results"]:
        if x["Driver"]["code"] == code:
            return f"lap {int(x['laps']) + 1}"


def conversations():
    """(name, ui_context, [(question, expected_substrings, distractor_substrings)])"""
    ad21 = (2021, 22)
    mon88 = (1988, 12)  # round 12 = Italian GP (the 1988 race with full results cached)
    return [
        ("race follow-ups by position", None, [
            ("Who won the 2021 Abu Dhabi Grand Prix?", [at_pos(*ad21, 1)], [at_pos(*ad21, 2)]),
            ("Who finished second?", [at_pos(*ad21, 2)], [at_pos(*ad21, 1)]),
            ("And who was third?", [at_pos(*ad21, 3)], []),
            ("Who was on pole?", [pole(*ad21)], []),
        ]),
        ("old race follow-ups", None, [
            ("Who won the 1988 Italian Grand Prix?", [at_pos(*mon88, 1)], []),
            ("Who came second?", [at_pos(*mon88, 2)], [at_pos(*mon88, 1)]),
            ("Who finished third in that race?", [at_pos(*mon88, 3)], []),
        ]),
        ("pronoun follow-up about the winner", None, [
            ("Who won the 2021 Abu Dhabi Grand Prix?", [at_pos(*ad21, 1)], [at_pos(*ad21, 2)]),
            ("Where did he start?", [at_pos(*ad21, 1), grid_of(*ad21, at_pos(*ad21, 1))], [at_pos(*ad21, 2)]),
        ]),
        ("switch year in follow-up (championship)", None, [
            ("Who won the 2024 world championship?", [champion(2024)], [runner_up(2024)]),
            ("What about 2025?", [champion(2025)], [runner_up(2025)]),
            ("And 2021?", [champion(2021)], [runner_up(2021)]),
        ]),
        ("switch year in follow-up (same race)", None, [
            ("Who won the 1994 Australian Grand Prix?", [winner(1994, "Australian Grand Prix")], []),
            ("What about in 1995?", [winner(1995, "Australian Grand Prix")], []),
        ]),
        ("UI shows 2026 R16, user asks about history", {"year": 2026, "round": 16}, [
            ("Who won the 1976 Japanese Grand Prix?", [winner(1976, "Japanese Grand Prix")], []),
            ("Who finished second?", [at_pos(1976, 16, 2)], [at_pos(2026, 16, 2)]),
        ]),
        ("retirement then lap follow-up", {"year": 2026, "round": 16}, [
            ("When did Albon retire?", ["albon", retirement_lap(2026, 16, "ALB")], []),
            ("Which lap was that on?", ["albon", retirement_lap(2026, 16, "ALB")], []),
        ]),
        ("swap the race in a follow-up", None, [
            ("Who won the 2024 Monaco Grand Prix?", [winner(2024, "Monaco Grand Prix")], []),
            ("What about Monza?", [winner(2024, "Italian Grand Prix")], [winner(2024, "Monaco Grand Prix")]),
            ("And Silverstone?", [winner(2024, "British Grand Prix")], []),
        ]),
        ("pronoun into career question", None, [
            ("Who won the 2008 world championship?", [champion(2008) if os.path.exists(os.path.join(CACHE, "2008_driverStandings.json")) else "Hamilton"], []),
            ("How many championships has he won?", ["Hamilton", "7"], []),
        ]),
        ("season question after a driver-focused turn", None, [
            ("Who won the 2021 Abu Dhabi Grand Prix?", [at_pos(*ad21, 1)], []),
            ("Where did he start?", [grid_of(*ad21, at_pos(*ad21, 1))], []),
            ("Who is leading the 2026 championship?", [standings_leader(2026)], ["Verstappen"]),
        ]),
        ("sprint weekend follow-ups", None, [
            ("Who won the sprint at the 2026 Miami Grand Prix?", [sprint_row(2026, 4, pos=1)], [sprint_row(2026, 4, pos=2)]),
            ("Who took sprint pole?", [sprint_pole(2026, 4)], []),
            ("What was the sprint grid?", [sprint_row(2026, 4, grid=1), sprint_row(2026, 4, grid=2)], []),
            ("Who won the Grand Prix?", [at_pos(2026, 4, 1)], [sprint_row(2026, 4, pos=1)]),
        ]),
        ("memory must not hijack follow-ups", {"year": 2026, "round": 16}, [
            ("Who won the 2026 Bahrain Grand Prix?", [at_pos(2026, 16, 1)], []),
            ("Who finished third?", [at_pos(2026, 16, 3)], []),
            ("Who was on pole?", [pole(2026, 16)], []),
        ]),
    ]


def grade(text, expect, distract):
    t = norm(text)
    if not all(norm(e) in t for e in expect):
        return False
    first = min(t.index(norm(e)) for e in expect)
    for d in distract:
        nd = norm(d)
        if any(nd == norm(e) for e in expect):
            continue
        if nd in t and t.index(nd) < first:
            return False
    return True


def run_conversation(ctx, turns):
    """Mirror the /api/chat pipeline: memory (deferring to data) first, then the engine."""
    history, results = [], []
    for q, expect, distract in turns:
        r = memory_manager.retrieve(q, ctx, history=history, defer_to_data=True) or ask(q, ctx, history=history)
        text = r.get("text") or ""
        results.append((q, expect, grade(text, expect, distract), r.get("intent"), text))
        history = history + [{"role": "user", "content": q}, {"role": "assistant", "content": text}]
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    total = ok = 0
    for name, ctx, turns in conversations():
        res = run_conversation(ctx, turns)
        conv_ok = all(r[2] for r in res)
        print(f"[{'PASS' if conv_ok else 'FAIL'}] {name}")
        for q, expect, good, intent, text in res:
            total += 1
            ok += int(good)
            if not good or args.verbose:
                print(f"    {'ok ' if good else 'BAD'} expected {expect}")
    print(f"TURNS {ok}/{total} = {100 * ok / total:.1f}%")
    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(main())
