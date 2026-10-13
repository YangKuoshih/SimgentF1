"""Golden eval: the pit wall agent against F1DB, for every Grand Prix since 1950.

The answers come from data/f1db_facts.json (scripts/build_golden_set.py), built from
F1DB: a different source from the one the agent answers from (Jolpica-F1). The network is
stubbed off, as in CI, so the agent answers from the cached data only.

Graded strictly:
- winner, pole, fastest lap, champion: the driver must be the answer's lead (its first bold
  name); first names count only where two drivers in the race share the last name.
- fastest lap: the lap time must be quoted too.
- circuit: the circuit's name; laps: the lap count in the answer's first sentence.
- declines: a race not run yet, or a Sprint before 2021, must be declined, not answered.
- invented lap times: any lap time quoted in any answer must exist in F1DB or in the race's
  cached Jolpica data.

    python tests/eval_golden.py [--out scorecard.json] [--markdown summary.md] [--gate] [--verbose] [--with-gate]
    --gate      exit non-zero if a category falls below tests/golden/baseline.json
"""

import collections
import glob
import json
import os
import re
import sys
import time
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# The engine is measured on its own: the answer gate corrects facts against the same F1DB key,
# so grading with it on would be circular. --with-gate measures what visitors get.
if "--with-gate" not in sys.argv:
    os.environ["SIMGENT_GATE"] = "off"

from app.tools import jolpica_sync as J  # noqa: E402

J._http = lambda url, retries=4: None  # cache only, as in CI
from app.tools.race_agent import answer_race_engineer_query as ask  # noqa: E402

GOLDEN = os.path.join(ROOT, "tests", "golden")
CURRENT_SEASON = 2026


def norm(text):
    text = unicodedata.normalize("NFD", text or "")
    return re.sub(r"[^a-z0-9 ]", " ", "".join(c for c in text if unicodedata.category(c) != "Mn").lower())


def tokens(text):
    return norm(text).split()


NOT_A_NAME = set("fastest lap laps pole position grand prix championship champion champions summary world "
                 "drivers driver constructors record victories victory points team race sprint qualifying fia "
                 "formula round circuit session result results classification winner".split())


def lead_name(answer):
    """The first bold text that reads as a person's name (skips headings such as "**Fastest Lap**"
    or "**1950 FIA Formula 1 World Championship Summary**")."""
    for m in re.finditer(r"\*\*(.+?)\*\*", answer):
        words = tokens(m.group(1))
        if words and not re.search(r"\d", m.group(1)) and not (set(words) & NOT_A_NAME):
            return m.group(1)
    return answer.split(".")[0]


def same_driver(name, person, shared_last):
    """name (from the answer) is this driver: last name, and first name where the race had two
    drivers with that last name. Multi-word last names (de Cesaris, von Trips) match as a run."""
    have = " " + " ".join(tokens(name)) + " "
    # F1DB writes "Sainz Jr."; answers say "Carlos Sainz"
    last = " ".join(w for w in tokens(person["last"]) if w not in ("jr", "sr", "ii", "iii"))
    if f" {last} " not in have:
        return False
    if person["last"] in shared_last:
        first = tokens(person["first"])
        return bool(first) and f" {first[0]} " in have
    return True


def ms(t):
    parts = t.split(":")
    try:
        sec = float(parts[-1]) + 60 * int(parts[-2]) + (3600 * int(parts[-3]) if len(parts) > 2 else 0)
    except (ValueError, IndexError):
        return None
    return round(sec * 1000)


LAP_TIME = re.compile(r"(?<![\d:])(\d{1,2}:\d{2}\.\d{1,3})(?!\d|\.\d)")  # a full stop may follow


def known_times(year, rnd, truth):
    """Every lap time the data has for this race: F1DB, and the cached Jolpica files."""
    out = {ms(t) for t in truth.get("lap_times", [])}
    for f in glob.glob(os.path.join(ROOT, "data", "cache", "jolpica", f"{year}_{rnd}_*.json")) + \
            glob.glob(os.path.join(ROOT, "data", "cache", "openf1", f"{year}_{rnd}_*.json")):
        try:
            text = open(f, encoding="utf-8").read()
        except OSError:
            continue
        out |= {ms(t) for t in LAP_TIME.findall(text)}
    return out


def build_cases(truth):
    sched = {}
    for f in sorted(glob.glob(os.path.join(ROOT, "data", "cache", "jolpica", "*_schedule.json"))):
        year = int(os.path.basename(f)[:4])
        for r in json.load(open(f, encoding="utf-8"))["MRData"]["RaceTable"]["Races"]:
            sched[(year, int(r["round"]))] = r
    cases = []
    for key, t in sorted(truth["races"].items(), key=lambda kv: tuple(map(int, kv[0].split("_")))):
        year, rnd = map(int, key.split("_"))
        race = sched.get((year, rnd))
        if not race:
            continue
        name = f"{year} {race['raceName']}"
        base = {"year": year, "round": rnd, "race": name, "truth": t, "circuit": race["Circuit"]["circuitName"]}
        cases.append(dict(base, category="winner", q=f"Who won the {name}?"))
        if t["pole"]:
            cases.append(dict(base, category="pole", q=f"Who was on pole for the {name}?"))
        if t["fastest_lap"]:
            cases.append(dict(base, category="fastest_lap", q=f"Who set the fastest lap at the {name}?"))
        cases.append(dict(base, category="circuit", q=f"Which circuit hosted the {name}?"))
        if t["laps"]:
            cases.append(dict(base, category="laps", q=f"How many laps was the {name}?"))
    for year, champ in sorted(truth["champions"].items()):
        if int(year) < CURRENT_SEASON:
            cases.append({"category": "champion", "year": int(year), "q": f"Who won the {year} drivers' championship?",
                          "truth": champ})
    run = {k for k in truth["races"]}
    for (year, rnd), race in sorted(sched.items()):
        if year == CURRENT_SEASON and f"{year}_{rnd}" not in run:
            cases.append({"category": "decline", "year": year, "round": rnd, "expect": "race_not_run",
                          "q": f"Who won the {year} {race['raceName']}?"})
    for year in (1950, 1961, 1976, 1988, 1999, 2010, 2020):
        race = sched.get((year, 1))
        if race:
            cases.append({"category": "decline", "year": year, "round": 1, "expect": "no_sprint_weekend",
                          "q": f"Who won the sprint at the {year} {race['raceName']}?"})
    return cases


def grade(case, resp):
    text, cat = resp.get("text", ""), case["category"]
    t = case.get("truth") or {}
    shared = t.get("shared_last_names", []) if isinstance(t, dict) else []
    lead = lead_name(text)
    if cat == "winner":
        return any(same_driver(lead, w, shared) for w in t["winners"])
    if cat == "pole":
        return any(same_driver(lead, p, shared) for p in t["pole"])
    if cat == "fastest_lap":
        fl = t["fastest_lap"]
        quoted = {ms(x) for x in LAP_TIME.findall(text)}
        # sub-minute laps (2020 Sakhir outer loop: 55.404) are quoted without minutes
        return same_driver(lead, fl, shared) and (ms(fl["time"]) in quoted or fl["time"] in text)
    if cat == "circuit":
        have = set(tokens(text))
        return any(set(tokens(n)) <= have for n in t["circuit_names"] + [case["circuit"]])
    if cat == "laps":
        first = re.split(r"(?<=[.!?])\s|\n", text.strip(), maxsplit=1)[0]
        return re.search(rf"\b{t['laps']}\b", first) is not None and "lap" in first.lower()
    if cat == "champion":
        return same_driver(lead, case["truth"], [])
    if cat == "decline":
        return resp.get("tool") == case["expect"]
    raise ValueError(cat)


DECLINED = re.compile(r"\b(i don't have|i do not have|isn't in the data|aren't in the data|not in the data|"
                      r"can't say|cannot say|no race result)\b", re.I)


def outcome(case, resp):
    """correct, declined (said it doesn't have that data) or wrong."""
    if grade(case, resp):
        return "correct"
    if case["category"] != "decline" and DECLINED.search(resp.get("text", "")):
        return "declined"
    return "wrong"


def era(year):
    return f"{year // 10 * 10}s"


def main():
    truth = json.load(open(os.path.join(ROOT, "data", "f1db_facts.json"), encoding="utf-8"))
    cases = build_cases(truth)
    started = time.time()
    by_cat = collections.defaultdict(collections.Counter)
    by_era = collections.defaultdict(collections.Counter)
    failures, invented = [], []
    for case in cases:
        try:
            resp = ask(case["q"], {}, [])
        except Exception as e:  # an exception is a failed answer, not a crashed eval
            resp = {"text": f"(error: {type(e).__name__}: {e})", "tool": "error"}
        result = outcome(case, resp)
        by_cat[case["category"]][result] += 1
        by_era[era(case["year"])][result] += 1
        if result != "correct":
            failures.append({"category": case["category"], "outcome": result, "q": case["q"],
                             "tool": resp.get("tool"), "answer": resp.get("text", "")[:300]})
        if case.get("round") and case.get("truth"):
            quoted = {ms(x) for x in LAP_TIME.findall(resp.get("text", ""))} - {None}
            unknown = quoted - known_times(case["year"], case["round"], case["truth"])
            if unknown:
                invented.append({"q": case["q"], "times": sorted(unknown), "answer": resp.get("text", "")[:300]})

    def summary(c):
        total = sum(c.values())
        answered = c["correct"] + c["wrong"]
        return {"correct": c["correct"], "declined": c["declined"], "wrong": c["wrong"], "total": total,
                "pct": round(100 * c["correct"] / total, 1) if total else None,
                "accuracy_when_answered": round(100 * c["correct"] / answered, 1) if answered else None}
    totals = sum(by_cat.values(), collections.Counter())
    card = {
        "generated_in_s": round(time.time() - started, 1),
        "source": truth["source"],
        "questions": len(cases),
        "overall": summary(totals),
        "by_category": {k: summary(v) for k, v in sorted(by_cat.items())},
        "by_era": {k: summary(v) for k, v in sorted(by_era.items())},
        "invented_lap_times": len(invented),
        "failures": failures,
        "invented": invented,
    }

    o = card["overall"]
    print(f"golden eval: {o['correct']}/{o['total']} correct ({o['pct']}%), {o['declined']} declined (no data), "
          f"{o['wrong']} wrong; accuracy when it answers {o['accuracy_when_answered']}%  ({card['generated_in_s']}s)")
    for k, v in card["by_category"].items():
        print(f"  {k:12} correct {v['correct']:5}/{v['total']:<5} {v['pct']:>5}%   declined {v['declined']:4}   wrong {v['wrong']:3}")
    print("  by era: " + "  ".join(f"{k} {v['pct']}%" for k, v in card["by_era"].items()))
    print(f"  answers quoting a lap time that isn't in the data: {card['invented_lap_times']}")
    if "--verbose" in sys.argv:
        for f in failures[:60]:
            print(f"  {f['outcome'].upper()} [{f['category']}] {f['q']}\n       [{f['tool']}] {f['answer'][:160]}")
        for f in invented[:20]:
            print(f"  INVENTED {f['times']} {f['q']}\n       {f['answer'][:160]}")
    if "--markdown" in sys.argv:
        rows = "\n".join(f"| {k} | {v['correct']}/{v['total']} | {v['pct']}% | {v['declined']} | {v['wrong']} |"
                         for k, v in card["by_category"].items())
        md = (f"### Pit wall agent: golden eval (F1DB {truth['source']['f1db']})\n\n"
              f"**{o['correct']}/{o['total']} correct ({o['pct']}%)**, {o['declined']} declined for lack of data, "
              f"**{o['wrong']} wrong**, {card['invented_lap_times']} invented lap times.\n\n"
              f"| Category | Correct | % | Declined | Wrong |\n|---|---|---|---|---|\n{rows}\n")
        with open(sys.argv[sys.argv.index("--markdown") + 1], "a", encoding="utf-8") as f:
            f.write(md)
    if "--out" in sys.argv:
        with open(sys.argv[sys.argv.index("--out") + 1], "w", encoding="utf-8") as f:
            json.dump(card, f, ensure_ascii=False, indent=1)
    if "--gate" in sys.argv:
        base = json.load(open(os.path.join(GOLDEN, "baseline.json"), encoding="utf-8"))
        cats = card["by_category"]
        low = [f"{k}: {cats.get(k, {}).get('pct')}% correct < {v}%" for k, v in base["min_pct"].items()
               if (cats.get(k, {}).get("pct") or 0) < v]
        low += [f"{k}: {cats.get(k, {}).get('wrong')} wrong > {v}" for k, v in base.get("max_wrong", {}).items()
                if (cats.get(k, {}).get("wrong") or 0) > v]
        if card["invented_lap_times"] > base.get("max_invented_lap_times", 0):
            low.append(f"invented lap times: {card['invented_lap_times']} > {base.get('max_invented_lap_times', 0)}")
        if low:
            print("GATE FAILED: " + "; ".join(low))
            sys.exit(1)
        print("gate passed")


if __name__ == "__main__":
    main()
