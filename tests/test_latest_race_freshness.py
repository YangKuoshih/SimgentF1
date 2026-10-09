"""A race that finishes after the container image was built must still become the
latest race (Cloud Run restarts with only the data baked into the image)."""
import asyncio
import datetime as dt
import json
import os
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app.tools import jolpica_sync as J  # noqa: E402
from app.tools import race_replay as R  # noqa: E402


def _race(rnd, date, winner=None):
    r = {"season": str(YEAR), "round": str(rnd), "raceName": f"Test Grand Prix {rnd}", "date": date,
         "Circuit": {"circuitId": "monza", "circuitName": "Monza",
                     "Location": {"locality": "Monza", "country": "Italy"}}}
    if winner:
        r["Results"] = [{"position": "1", "Driver": {"code": winner, "givenName": "Test", "familyName": winner.title()},
                         "Constructor": {"constructorId": "ferrari", "name": "Ferrari"}}]
    return r


def _doc(races):
    return {"MRData": {"RaceTable": {"Races": races}}}


TODAY = dt.date.today()
YEAR = TODAY.year
OLD = (TODAY - dt.timedelta(days=10)).isoformat()      # finished before the image was built
NEW = (TODAY - dt.timedelta(days=1)).isoformat()       # finished after the image was built
FUTURE = (TODAY + dt.timedelta(days=6)).isoformat()


class LatestRaceFreshnessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        cache = self.tmp.name
        image_built = time.time() - 3 * 86400  # files in the image are 3 days old
        files = {
            f"{YEAR}_schedule": _doc([_race(1, OLD), _race(2, NEW), _race(3, FUTURE)]),
            f"{YEAR}_winners": _doc([_race(1, OLD, "AAA")]),
            f"{YEAR}_1_results": _doc([_race(1, OLD, "AAA")]),
        }
        for name, doc in files.items():
            p = os.path.join(cache, f"{name}.json")
            with open(p, "w") as f:
                json.dump(doc, f)
            os.utime(p, (image_built, image_built))
        # Jolpica now has round 2's result
        upstream = {
            "/results/1.json": _doc([_race(1, OLD, "AAA"), _race(2, NEW, "BBB")]),
            f"/{YEAR}/2/results.json": _doc([_race(2, NEW, "BBB")]),
            f"/{YEAR}/3/results.json": _doc([]),
            f"/{YEAR}.json": files[f"{YEAR}_schedule"],
        }

        def fake_http(url, retries=4):
            return next((doc for key, doc in upstream.items() if key in url), None)

        self.patches = [patch.object(J, "CACHE", cache), patch.object(J, "_http", side_effect=fake_http),
                        patch.object(J, "_manifest_record"), patch.object(J, "_manifest_forget")]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def test_race_finished_after_build_is_completed(self):
        races = {r["round"]: r for r in R.season_races(YEAR)}
        self.assertTrue(races[2]["completed"])
        self.assertEqual(races[2]["winner"]["code"], "BBB")
        self.assertFalse(races[3]["completed"])

    def test_latest_race_endpoint_returns_newest_finished_race(self):
        from frontend import main as M
        with patch.object(M.race_replay, "season_races", R.season_races):
            latest = asyncio.run(M.api_latest_race())
        self.assertEqual((latest["year"], latest["round"]), (YEAR, 2))


if __name__ == "__main__":
    unittest.main()
