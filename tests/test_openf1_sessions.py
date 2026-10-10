"""OpenF1 fills in Sprint and Qualifying until Jolpica publishes them (hours after the
session). Offline: fixtures follow OpenF1's real field shapes (checked against the 2026
sprints and qualifying sessions, which match Jolpica position for position)."""
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tools import jolpica_sync as J  # noqa: E402
from app.tools import openf1_sync as O  # noqa: E402

DRIVERS = {n: {"driver_number": n, "first_name": f, "last_name": l, "name_acronym": c, "team_name": t}
           for n, f, l, c, t in [(3, "Max", "Verstappen", "VER", "Red Bull Racing"),
                                 (63, "George", "Russell", "RUS", "Mercedes"),
                                 (16, "Charles", "Leclerc", "LEC", "Ferrari"),
                                 (18, "Lance", "Stroll", "STR", "Aston Martin"),
                                 (27, "Nico", "Hulkenberg", "HUL", "Audi"),
                                 (5, "Gabriel", "Bortoleto", "BOR", "Audi"),
                                 (44, "Lewis", "Hamilton", "HAM", "Ferrari")]}
SPRINT = [
    {"position": 1, "driver_number": 3, "number_of_laps": 19, "points": 8.0, "duration": 1825.318, "gap_to_leader": 0},
    {"position": 2, "driver_number": 63, "number_of_laps": 19, "points": 7.0, "duration": 1830.0, "gap_to_leader": 4.682},
    {"position": 3, "driver_number": 16, "number_of_laps": 19, "points": 6.0, "duration": 1901.385, "gap_to_leader": 76.067},
    {"position": 4, "driver_number": 18, "number_of_laps": 18, "points": 5.0, "gap_to_leader": "+1 LAP"},
    {"position": None, "driver_number": 27, "number_of_laps": 7, "points": 0.0, "gap_to_leader": "+12 LAPS"},
    {"position": None, "driver_number": 5, "number_of_laps": None, "points": 0.0, "dsq": True},
    {"position": None, "driver_number": 44, "number_of_laps": 0, "points": 0.0, "dns": True},
]


class ConvertSprintTests(unittest.TestCase):
    def test_rows_follow_jolpica_conventions(self):
        rows = O.convert_sprint(SPRINT, DRIVERS)
        got = [(r["driver_code"], r["pos"], r["status"], r["time"]) for r in rows]
        self.assertEqual(got, [
            ("VER", "1", "Finished", "30:25.318"),
            ("RUS", "2", "Finished", "+4.682"),
            ("LEC", "3", "Finished", "+1:16.067"),  # Jolpica writes gaps over a minute as m:ss.sss
            ("STR", "4", "Lapped", ""),             # OpenF1 gives no time for lapped cars
            ("HUL", "R", "Retired", ""),            # unclassified: retired
            ("BOR", "D", "Disqualified", ""),
            ("HAM", "W", "Did not start", ""),
        ])
        self.assertEqual(rows[0]["millis"], 1825318)
        self.assertIsNone(rows[3]["millis"])


class TextPositions(unittest.TestCase):
    def test_text_position_is_unclassified_and_last(self):
        # 2026 Singapore qualifying: OpenF1 sent position "RT" for a car with no time
        results = [{"position": "RT", "driver_number": 18, "duration": [None, None, None], "number_of_laps": 1},
                   {"position": 1, "driver_number": 3, "duration": [91.9, 91.5, 91.1], "number_of_laps": 18}]
        rows = O.convert(results, DRIVERS)
        self.assertEqual([(r["driver_code"], r["pos"]) for r in rows], [("VER", "1"), ("STR", "NC")])
        sprint = O.convert_sprint([dict(SPRINT[0]), {"position": "RT", "driver_number": 18, "number_of_laps": 3}], DRIVERS)
        self.assertEqual([(r["driver_code"], r["pos"], r["status"]) for r in sprint], [("VER", "1", "Finished"), ("STR", "R", "Retired")])


class FallbackUntilJolpicaPublishes(unittest.TestCase):
    """2026 R17 (Singapore) has no Jolpica sprint or qualifying in the cache."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        rows = O.convert_sprint(SPRINT, DRIVERS)
        for r, g in zip(rows, ["2", "1", "4", "3", "5", "6", "0"]):
            r["grid"] = g
        quali = [{"pos": "1", "num": "3", "driver_name": "Max Verstappen", "driver_code": "VER", "team": "Red Bull Racing",
                  "q1": "1:31.900", "q2": "1:31.500", "q3": "1:31.100", "laps": 18},
                 {"pos": "2", "num": "63", "driver_name": "George Russell", "driver_code": "RUS", "team": "Mercedes",
                  "q1": "1:32.000", "q2": "DNF", "q3": "", "laps": 9}]
        for name, doc in (("2026_17_sprint", rows), ("2026_17_qualifying", quali)):
            with open(os.path.join(self.tmp.name, f"{name}.json"), "w") as f:
                json.dump(doc, f)
        self.patches = [patch.object(J, "OPENF1_CACHE", self.tmp.name),
                        patch.object(J, "_http", lambda url, retries=4: None)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def test_sprint_result_from_openf1(self):
        sp = J.sprint_results(2026, 17, net=False)
        self.assertEqual(sp["source"], "OpenF1 (Jolpica not published yet)")
        self.assertEqual(sp["raceName"], "Singapore Grand Prix")
        first = sp["SprintResults"][0]
        self.assertEqual((first["position"], first["grid"], first["status"]), ("1", "2", "Finished"))
        self.assertEqual(first["Time"], {"time": "30:25.318", "millis": "1825318"})
        # Driver records come from this season's Jolpica data (matched on car number)
        self.assertEqual(first["Driver"], J._season_people(2026, 17)["3"][0])
        self.assertEqual([x["positionText"] for x in sp["SprintResults"]], ["1", "2", "3", "4", "R", "D", "W"])

    def test_qualifying_from_openf1(self):
        q = J.qualifying_results(2026, 17, net=False)
        self.assertEqual(q["source"], "OpenF1 (Jolpica not published yet)")
        rus = q["QualifyingResults"][1]
        self.assertEqual(rus["Driver"]["code"], "RUS")
        self.assertEqual(rus["Q2"], "")  # reached Q2, no time: empty as in Jolpica
        self.assertNotIn("Q3", rus)


if __name__ == "__main__":
    unittest.main()
