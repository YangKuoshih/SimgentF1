"""promptfoo assertion for the playground: checks an answer against F1DB where a question has a
known answer (winner, pole, fastest lap, laps, circuit, champion), with the same grading as
tests/eval_golden.py, and flags lap times that aren't in the data.

Random questions carry their race and category; for your own questions the race and the kind of
question are worked out here, independently of the agent (a shared matcher would share its
mistakes). Questions it can't place pass with "not auto-checked": judge those yourself in the
dashboard (thumbs up/down).
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))

import eval_golden as G  # noqa: E402

_TRUTH = None
_SCHED = None


def _data():
    global _TRUTH, _SCHED
    if _TRUTH is None:
        with open(os.path.join(ROOT, "data", "f1db_facts.json"), encoding="utf-8") as f:
            _TRUTH = json.load(f)
        _SCHED = {}
        import glob
        for path in glob.glob(os.path.join(ROOT, "data", "cache", "jolpica", "*_schedule.json")):
            year = int(os.path.basename(path)[:4])
            with open(path, encoding="utf-8") as f:
                for r in json.load(f)["MRData"]["RaceTable"]["Races"]:
                    _SCHED[(year, int(r["round"]))] = r
    return _TRUTH, _SCHED


STOP = set("the grand prix gp who won win winner was what which where how many laps lap pole fastest set "
           "at in of for on did race circuit track hosted held f1 formula".split())


def place_race(question, year):
    """(round, schedule entry) the question names, by the words it shares with each race's name,
    circuit and place; None when no race or more than one fits equally."""
    _, sched = _data()
    words = set(G.tokens(question)) - STOP - {str(year)}
    best, score, tie = None, 0, False
    for (y, rnd), r in sched.items():
        if y != year:
            continue
        loc = r["Circuit"]["Location"]
        names = set(G.tokens(" ".join([r["raceName"], r["Circuit"]["circuitName"], loc["locality"], loc["country"]]))) - STOP
        s = len(words & names) * 10 - len(set(G.tokens(r["raceName"])) - STOP - words)  # prefer the exact name
        if s > score:
            best, score, tie = (rnd, r), s, False
        elif s == score and s > 0:
            tie = True
    return None if tie or score <= 0 else best


def category_of(q):
    q = q.lower()
    if "fastest lap" in q or "quickest" in q:
        return "fastest_lap"
    if "pole" in q:
        return "pole"
    if re.search(r"how many laps|number of laps|in laps", q):
        return "laps"
    if re.search(r"which circuit|what track|which track|where was|held|hosted|venue", q):
        return "circuit"
    if re.search(r"champion|championship|title", q) and not re.search(r"grand prix|\bgp\b", q):
        return "champion"
    if re.search(r"\bwon\b|\bwin\b|winner|victor|chequered|checkered|finished first", q):
        return "winner"
    return None


def get_assert(output, context):
    v = (context or {}).get("vars") or {}
    q = v.get("question", "")
    truth, _ = _data()
    lazy = "made up" if re.search(r"live timing|live telemetry|degradation rate of|speed trap of \d", output, re.I) else ""
    if lazy:
        return {"pass": False, "score": 0, "reason": f"claims data SimGent doesn't have ({lazy})"}
    category = v.get("category") or category_of(q)
    m = re.search(r"\b(19[5-9]\d|20[0-2]\d)\b", q)
    year = int(v["year"]) if v.get("year") else (int(m.group(1)) if m else None)
    if "Which one do you mean" in output or re.match(r"(Which .+ do you mean|Do you mean)", output):
        return {"pass": True, "score": 1, "reason": "asked a clarifying question"}
    if not category or not year:
        return {"pass": True, "score": 1, "reason": "not auto-checked (no known answer for this kind of question)"}
    if category == "champion":
        champ = truth["champions"].get(str(year))
        if not champ:
            return {"pass": True, "score": 1, "reason": f"not auto-checked (no {year} champion in F1DB)"}
        case = {"category": "champion", "truth": champ, "year": year}
    else:
        placed = (int(v["round"]), _data()[1].get((year, int(v["round"])))) if v.get("round") else place_race(q, year)
        if not placed or not placed[1]:
            return {"pass": True, "score": 1, "reason": "not auto-checked (couldn't tell which race)"}
        rnd, race = placed
        t = truth["races"].get(f"{year}_{rnd}")
        if not t:
            return {"pass": True, "score": 1, "reason": f"not auto-checked ({year} R{rnd} has no result yet)"}
        case = {"category": category, "truth": t, "year": year, "round": rnd, "circuit": race["Circuit"]["circuitName"]}
        quoted = {G.ms(x) for x in G.LAP_TIME.findall(output)} - {None}
        unknown = quoted - G.known_times(year, rnd, t)
        if unknown:
            return {"pass": False, "score": 0, "reason": f"quotes a lap time that isn't in the data for {year} R{rnd}"}
    resp = {"text": output, "tool": ""}
    gate = (((context or {}).get("providerResponse") or {}).get("metadata") or {}).get("gate") or {}
    if G.grade(case, resp):
        if gate.get("verdict") == "corrected":
            # the visitor got the right answer, but only because the gate fixed the engine's: an
            # engine bug to fix
            return {"pass": True, "score": 0.75, "reason": f"correct after the answer gate corrected the engine ({category})"}
        return {"pass": True, "score": 1, "reason": f"correct ({category}, checked against F1DB)"}
    if G.DECLINED.search(output):
        return {"pass": True, "score": 0.5, "reason": f"declined: said it doesn't have the data ({category})"}
    expected = _expected(case)
    return {"pass": False, "score": 0, "reason": f"WRONG ({category}): F1DB says {expected}"}


def _expected(case):
    t, c = case["truth"], case["category"]
    who = lambda p: f"{p['first']} {p['last']}"
    if c == "winner":
        return " / ".join(who(w) for w in t["winners"])
    if c == "pole":
        return " or ".join(who(p) for p in t["pole"])
    if c == "fastest_lap":
        return f"{who(t['fastest_lap'])} {t['fastest_lap']['time']}"
    if c == "laps":
        return f"{t['laps']} laps"
    if c == "circuit":
        return case.get("circuit") or ", ".join(t["circuit_names"])
    if c == "champion":
        return who(t)
    return "?"
