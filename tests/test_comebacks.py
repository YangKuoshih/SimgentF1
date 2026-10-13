"""Comeback questions (f1_history.lookup_comebacks): grid against finish from F1DB, for a driver,
a season, one race or all time. Offline."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tools import jolpica_sync as J  # noqa: E402
from app.tools.race_agent import answer_race_engineer_query as ask  # noqa: E402

_offline = mock.patch.object(J, "_http", lambda url, retries=4: None)
SPAIN_2026 = {"year": 2026, "round": 14, "session": "race"}


def setUpModule():
    _offline.start()


def tearDownModule():
    _offline.stop()


class Comebacks(unittest.TestCase):
    def test_searches_the_drivers_career_not_the_race_on_screen(self):
        # asked on the 2026 Spanish GP replay; it used to describe Spain (started P2)
        r = ask("in what race did Antonelli come back for an incredible win after starting in the back of the grid?",
                SPAIN_2026, [])
        self.assertEqual(r["tool"], "comeback_lookup")
        self.assertIn("**2026 Italian Grand Prix**", r["text"].split("\n")[0])
        self.assertIn("**P19**", r["text"])

    def test_all_time_record_leaves_out_shared_drives(self):
        # 1950s car swaps have no grid slot of their own; they are not pit-lane starts
        r = ask("biggest comeback win ever", {}, [])
        self.assertIn("**John Watson** at the **1983 United States Grand Prix West**, from **P22**", r["text"])
        self.assertNotIn("Fangio", r["text"])

    def test_nobody_has_won_from_the_pit_lane(self):
        self.assertTrue(ask("who won from the pit lane", {}, [])["text"].startswith("Nobody has won from the pit lane"))

    def test_a_season(self):
        r = ask("biggest comeback in 2021", {}, [])
        self.assertIn("**Max Verstappen**, the **2021 Russian Grand Prix**, from **P20** to **P2**", r["text"])

    def test_places_gained_in_the_race_on_screen(self):
        r = ask("who gained the most places?", {"year": 2026, "round": 13, "session": "race"}, [])
        self.assertIn("at the **2026 Italian Grand Prix**: **Kimi Antonelli**, from **P19** to **P1**", r["text"])

    def test_grid_questions_stay_with_the_grid(self):
        self.assertNotEqual(ask("who started from the pit lane", SPAIN_2026, [])["tool"], "comeback_lookup")
        self.assertNotEqual(ask("who started last", SPAIN_2026, [])["tool"], "comeback_lookup")


if __name__ == "__main__":
    unittest.main()
