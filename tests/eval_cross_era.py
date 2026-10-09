"""Cross-era eval for the SimGent agent.

Builds questions whose expected answers come straight from the cached Jolpica
data, runs them through answer_race_engineer_query with the network stubbed
off (cache only), and grades by whether the expected name appears in the
answer text (and before any rival, e.g. the runner-up).
Run from the repo root:  python3 tests/eval_cross_era.py [--out results.json]
Exits non-zero if any question fails.
"""
import sys, os, json, random, re, unicodedata, glob, argparse, logging
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.disable(logging.WARNING)

from app.tools import jolpica_sync as J
J._http = lambda url, retries=4: None  # offline: cache only, never write cache
from app.tools.race_agent import answer_race_engineer_query as ask

CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cache", "jolpica")


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s.lower())


def load(name):
    p = os.path.join(CACHE, name + ".json")
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


def era(y):
    if y < 1970: return "1950-69"
    if y < 1990: return "1970-89"
    if y < 2010: return "1990-2009"
    if y < 2023: return "2010-22"
    if y < 2026: return "2023-25"
    return "2026"


FAMOUS = {(1976, "Japanese Grand Prix"), (2021, "Abu Dhabi Grand Prix"), (2008, "Brazilian Grand Prix"),
          (1994, "Australian Grand Prix"), (1989, "Japanese Grand Prix"), (1990, "Japanese Grand Prix"),
          (2010, "Abu Dhabi Grand Prix"), (1997, "European Grand Prix"), (2007, "Brazilian Grand Prix"),
          (2012, "Brazilian Grand Prix"), (1982, "Belgian Grand Prix"), (1994, "San Marino Grand Prix")}


def podium_others(y, rnd, winner):
    d = load(f"{y}_{rnd}_results")
    if not d or not d["MRData"]["RaceTable"]["Races"]:
        return []
    res = d["MRData"]["RaceTable"]["Races"][0]["Results"]
    return [x["Driver"]["familyName"] for x in res[1:3] if norm(x["Driver"]["familyName"]) != norm(winner)]


def build(seed=7, races_per_year=2):
    rnd = random.Random(seed)
    qs = []
    for y in range(1950, 2027):
        w = load(f"{y}_winners")
        if w:
            races = w["MRData"]["RaceTable"]["Races"]
            for r in rnd.sample(races, min(races_per_year, len(races))):
                d = r["Results"][0]["Driver"]
                qs.append(dict(kind="race_winner", year=y,
                               q=f"Who won the {y} {r['raceName']}?",
                               expect=[d["familyName"]],
                               distract=podium_others(y, r["round"], d["familyName"])))
            for r in races:
                if (y, r["raceName"]) in FAMOUS:
                    d = r["Results"][0]["Driver"]
                    qs.append(dict(kind="famous_race_winner", year=y,
                                   q=f"Who won the {y} {r['raceName']}?",
                                   expect=[d["familyName"]],
                                   distract=podium_others(y, r["round"], d["familyName"])))
        ds = load(f"{y}_driverStandings")
        if ds and y < 2026:
            lst = ds["MRData"]["StandingsTable"]["StandingsLists"]
            if lst:
                d = lst[0]["DriverStandings"][0]["Driver"]
                ru = lst[0]["DriverStandings"][1]["Driver"]["familyName"]
                qs.append(dict(kind="drivers_champion", year=y,
                               q=f"Who won the {y} Formula 1 drivers' world championship?",
                               expect=[d["familyName"]], distract=[ru]))
        cs = load(f"{y}_constructorStandings")
        if cs and 1958 <= y < 2026:
            lst = cs["MRData"]["StandingsTable"]["StandingsLists"]
            if lst and lst[0].get("ConstructorStandings"):
                c = lst[0]["ConstructorStandings"][0]["Constructor"]
                c2 = [lst[0]["ConstructorStandings"][1]["Constructor"]["name"]] if len(lst[0]["ConstructorStandings"]) > 1 else []
                qs.append(dict(kind="constructors_champion", year=y,
                               q=f"Which team won the {y} constructors' championship?",
                               expect=[c["name"]], distract=c2))
    # Sprints: winner of every cached sprint (Jolpica) and sprint pole from the official
    # Sprint Qualifying / Shootout classification (OpenF1)
    off_dir = os.path.join(os.path.dirname(CACHE), "openf1")
    for p in sorted(glob.glob(os.path.join(CACHE, "*_sprint.json"))):
        m = re.match(r"(\d{4})_(\d+)_sprint\.json", os.path.basename(p))
        if not m:
            continue
        y, rnd = int(m.group(1)), m.group(2)
        with open(p) as f:
            races = json.load(f)["MRData"]["RaceTable"]["Races"]
        if not races or not races[0].get("SprintResults"):
            continue
        r = races[0]
        res = r["SprintResults"]
        w = [x for x in res if x.get("position") == "1"][0]["Driver"]["familyName"]
        p2 = [x["Driver"]["familyName"] for x in res if x.get("position") == "2"]
        qs.append(dict(kind="sprint_winner", year=y, q=f"Who won the sprint at the {y} {r['raceName']}?",
                       expect=[w], distract=p2))
        sq = os.path.join(off_dir, f"{y}_{rnd}_sprint_qualifying.json")
        if os.path.exists(sq):
            with open(sq, encoding="utf-8") as f:
                rows = json.load(f)
            code_to_family = {x["Driver"]["code"]: x["Driver"]["familyName"] for x in res}
            pole = code_to_family.get(rows[0]["driver_code"], rows[0]["driver_name"].split()[-1])
            second = [code_to_family.get(rows[1]["driver_code"], "")] if len(rows) > 1 else []
            qs.append(dict(kind="sprint_pole", year=y, q=f"Who took sprint pole at the {y} {r['raceName']}?",
                           expect=[pole], distract=[d for d in second if d]))

    # Podium P2 and pole where full results / qualifying are cached
    for p in sorted(glob.glob(os.path.join(CACHE, "*_results.json"))):
        m = re.match(r"(\d{4})_(\d+)_results\.json", os.path.basename(p))
        if not m:
            continue
        y = int(m.group(1))
        with open(p) as f:
            races = json.load(f)["MRData"]["RaceTable"]["Races"]
        if not races or len(races[0]["Results"]) < 2:
            continue
        r = races[0]
        p2_rows = [x for x in r["Results"] if x.get("position") == "2"]  # shared drives: two rows can be P1
        if not p2_rows:
            continue
        d2 = p2_rows[0]["Driver"]
        qs.append(dict(kind="p2_finisher", year=y,
                       q=f"Who finished second in the {y} {r['raceName']}?",
                       expect=[d2["familyName"]],
                       distract=[r["Results"][0]["Driver"]["familyName"]]))
        qp = os.path.join(CACHE, f"{y}_{m.group(2)}_qualifying.json")
        if os.path.exists(qp):
            with open(qp) as f:
                qr = json.load(f)["MRData"]["RaceTable"]["Races"]
            if qr and qr[0].get("QualifyingResults"):
                dp = qr[0]["QualifyingResults"][0]["Driver"]
                q2 = [qr[0]["QualifyingResults"][1]["Driver"]["familyName"]] if len(qr[0]["QualifyingResults"]) > 1 else []
                qs.append(dict(kind="pole", year=y,
                               q=f"Who was on pole for the {y} {r['raceName']}?",
                               expect=[dp["familyName"]], distract=q2))
    return qs


def grade(answer_text, expect, distract=()):
    """Pass only if every expected name appears, and before any distractor
    (e.g. the runner-up), so 'Runner-Up: Norris' does not count as naming Norris champion."""
    t = norm(answer_text)
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    qs = build()
    by = defaultdict(lambda: [0, 0])
    by_kind = defaultdict(lambda: [0, 0])
    rows = []
    for item in qs:
        try:
            r = ask(item["q"], None)
            text = r.get("text") or ""
            intent = r.get("intent")
            err = None
        except Exception as e:  # count crashes as failures
            text, intent, err = "", None, f"{type(e).__name__}: {e}"
        ok = grade(text, item["expect"], item.get("distract", []))
        for key, bucket in ((era(item["year"]), by), (item["kind"], by_kind)):
            bucket[key][1] += 1
            bucket[key][0] += int(ok)
        rows.append(dict(item, ok=ok, intent=intent, error=err, answer=text[:400]))
    total_ok = sum(r["ok"] for r in rows)
    print(f"TOTAL {total_ok}/{len(rows)} = {100*total_ok/len(rows):.1f}%")
    print("By era:")
    for k in ["1950-69", "1970-89", "1990-2009", "2010-22", "2023-25", "2026"]:
        if k in by:
            a, n = by[k]; print(f"  {k:10s} {a:3d}/{n:<3d} {100*a/n:5.1f}%")
    print("By question type:")
    for k, (a, n) in sorted(by_kind.items()):
        print(f"  {k:22s} {a:3d}/{n:<3d} {100*a/n:5.1f}%")
    if args.out:
        with open(args.out, "w") as f:
            json.dump(rows, f, indent=1, ensure_ascii=False)
    for r in rows:
        if not r["ok"]:
            print(f"FAIL [{r['kind']}] expected {r['expect']}")
    return 0 if total_ok == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
