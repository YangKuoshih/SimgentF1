"""content/ (stories, eras, retirement write-ups, regulations): format, and facts the data can
check (step 2 of docs/AGENT_ARCHITECTURE.md). Offline, cached data only."""
import glob
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agent import content as C  # noqa: E402
from app.agent.embedding import MODEL_DIR  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOLPICA = os.path.join(ROOT, "data", "cache", "jolpica")
REQUIRED = {
    "races": ("id", "year", "round", "circuit_id", "race_name", "title", "keywords", "metrics"),
    "eras": ("id", "title", "years", "engine_type", "total_hp", "key_innovations"),
    "retirements": ("year", "circuit_id", "driver", "exit_lap", "completed_laps", "cause", "action"),
    "regulations": ("id", "title", "intent", "card"),
}


def _races(name):
    path = os.path.join(JOLPICA, f"{name}.json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)["MRData"]["RaceTable"]["Races"]


class FormatTests(unittest.TestCase):
    def test_every_file_parses_with_required_fields_and_sources(self):
        for kind, fields in REQUIRED.items():
            files = glob.glob(os.path.join(C.CONTENT_DIR, kind, "*.md"))
            self.assertTrue(files, kind)
            for path in files:
                meta, body = C.parse(path)
                for field in fields:
                    self.assertIn(field, meta, f"{C.rel(path)}: missing {field}")
                self.assertIsInstance(meta.get("sources"), list, f"{C.rel(path)}: sources must be a list")
                self.assertTrue(body.strip(), f"{C.rel(path)}: empty body")

    def test_loaders(self):
        self.assertEqual(len(C.race_stories()), 9)
        self.assertEqual(len(C.eras()), 10)
        self.assertEqual(len(C.retirements()), 11)
        reg = C.regulation("2026-technical")
        self.assertIn("50/50", reg["text"])
        self.assertEqual(len(reg["card"]["metrics"]), 4)

    def test_ids_are_unique(self):
        for kind in ("races", "eras", "regulations"):
            ids = [d["id"] for d in C.documents(kind)]
            self.assertEqual(len(ids), len(set(ids)), kind)


class FactsAgainstDataTests(unittest.TestCase):
    def test_retirement_laps_match_the_race_result(self):
        checked = 0
        for (year, circuit_id, driver), r in C.retirements().items():
            # exit_lap is the race (leader's) lap of the incident: it can be more than
            # completed_laps + 1 for a car running behind (Stroll, Baku 2026: race lap 9 after 7
            # laps), or equal when the car limped back and completed that lap (Schumacher, Spa 1998)
            self.assertGreaterEqual(r["exit_lap"], r["completed_laps"], (year, circuit_id, driver))
            for race in _races(f"{year}_schedule"):
                if race["Circuit"]["circuitId"] != circuit_id:
                    continue
                for res in _races(f"{year}_{race['round']}_results"):
                    row = next((x for x in res["Results"] if driver in (x["Driver"].get("code"), x["Driver"]["driverId"])), None)
                    if row:
                        self.assertEqual(int(row["laps"]), r["completed_laps"],
                                         f"{year} {circuit_id} {driver}: content says {r['completed_laps']} laps, data {row['laps']}")
                        checked += 1
        self.assertGreaterEqual(checked, 8, "most write-ups should be checkable against cached results")

    def test_race_stories_match_the_schedule(self):
        for s in C.race_stories():
            sched = {int(r["round"]): r for r in _races(f"{s['year']}_schedule")}
            if not sched:
                continue
            race = sched.get(s["round"])
            self.assertIsNotNone(race, f"{s['id']}: no round {s['round']} in {s['year']}")
            self.assertEqual(race["Circuit"]["circuitId"], s["circuit_id"], s["id"])
            self.assertTrue(s["race_name"].startswith(race["raceName"].replace(f"{s['year']} ", "").split(" (")[0]),
                            f"{s['id']}: {s['race_name']} vs {race['raceName']}")

    def test_era_power_adds_up(self):
        for era in C.eras().values():
            self.assertEqual(era["total_hp"], era["ice_power_hp"] + era["electric_power_hp"], era["id"])


@unittest.skipUnless(os.path.exists(os.path.join(MODEL_DIR, "model.safetensors")), "run scripts/fetch_models.py")
class SearchTests(unittest.TestCase):
    def test_semantic_search_finds_the_right_document(self):
        cases = {("races", "the season finale safety car controversy"): "2021_abu_dhabi",
                 ("races", "crashgate"): "2008_singapore",
                 ("races", "the longest race ever"): "2011_canada",
                 ("eras", "front engined cars in the fifties"): "1950s",
                 ("eras", "what were the cars like in the turbo years"): "1980s"}
        for (kind, q), want in cases.items():
            self.assertEqual(C.search(q, kind, 1)[0][0]["id"], want, q)


if __name__ == "__main__":
    unittest.main()
