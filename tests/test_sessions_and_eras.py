"""
Comprehensive test suite verifying resilience across all F1 sessions (Grand Prix, Qualifying, Sprint)
and historical eras (1950 to 2026) to guarantee zero 500 errors.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tools import race_replay
from app.tools.race_replay import _safe_int, _safe_float, _secs, _valid_time_str


class TestSessionsAndEras(unittest.TestCase):

    def test_safe_helpers(self):
        """Verifies helper functions handle corrupted or non-numeric data cleanly."""
        self.assertEqual(_safe_int("12"), 12)
        self.assertEqual(_safe_int("NC", fallback=22), 22)
        self.assertEqual(_safe_int("DQ", fallback=99), 99)
        self.assertEqual(_safe_int(None, fallback=1), 1)
        self.assertEqual(_safe_int("", fallback=5), 5)
        self.assertEqual(_safe_int("14.0", fallback=0), 14)

        self.assertEqual(_safe_float("25.5"), 25.5)
        self.assertEqual(_safe_float("NC", fallback=0.0), 0.0)
        self.assertEqual(_safe_float(None, fallback=1.5), 1.5)

        self.assertIsNone(_secs("DNF"))
        self.assertIsNone(_secs("DNS"))
        self.assertIsNone(_secs(""))
        self.assertIsNone(_secs(None))
        self.assertAlmostEqual(_secs("1:14.679"), 74.679, places=3)

        self.assertEqual(_valid_time_str("DNF", "1:15.281", None), "1:15.281")
        self.assertIsNone(_valid_time_str("DNF", "DNS", None))

    def test_barcelona_2026_q3_dnf_resilience(self):
        """Specifically verifies 2026 R7 Barcelona GP Qualifying where Charles Leclerc had a Q3 DNF."""
        rep = race_replay.build_replay(2026, 7, net=False, session_type="qualifying")
        self.assertIsNotNone(rep, "2026 R7 Qualifying replay must build successfully")
        self.assertEqual(rep["meta"]["pole_driver"], "RUS")
        self.assertEqual(len(rep["drivers"]), 22)

        # Charles Leclerc had Q3 DNF
        lec = next((d for d in rep["drivers"] if d["code"] == "LEC"), None)
        self.assertIsNotNone(lec, "Charles Leclerc must be present in classification")
        self.assertIn("Q3", lec["status"])
        self.assertEqual(len(lec["cum"]), 3)
        self.assertTrue(all(isinstance(t, (int, float)) for t in lec["cum"]))
        self.assertGreater(lec["cum"][2], lec["cum"][1])

    def test_sprint_nc_resilience(self):
        """Verifies sprints with unclassified / NC drivers (e.g. 2026 R2, R4, R5, R12) build cleanly."""
        for rnd in [2, 4, 5, 12]:
            rep = race_replay.build_replay(2026, rnd, net=False, session_type="sprint")
            self.assertIsNotNone(rep, f"2026 R{rnd} Sprint replay must build without errors")
            self.assertGreater(len(rep["drivers"]), 0)
            for d in rep["drivers"]:
                self.assertIsInstance(d["finish"], int)
                self.assertIsInstance(d["grid"], int)
                self.assertIsInstance(d["points"], float)

    def test_qualifying_dq_resilience(self):
        """Verifies qualifying with disqualified / DQ drivers (e.g. 2026 R4) builds cleanly."""
        rep = race_replay.build_replay(2026, 4, net=False, session_type="qualifying")
        self.assertIsNotNone(rep, "2026 R4 Qualifying replay must build without errors")
        self.assertGreater(len(rep["drivers"]), 0)

    def test_all_session_types_across_eras(self):
        """Verifies Grand Prix, Qualifying, and Sprint builds cleanly across classic and modern eras."""
        sample_eras = [1950, 1976, 2023, 2024, 2025, 2026]
        for y in sample_eras:
            for session in ["race", "qualifying", "sprint"]:
                rep = race_replay.build_replay(y, 1, net=False, session_type=session)
                self.assertIsNotNone(rep, f"Year {y} R1 {session} must build without errors")
                self.assertGreater(len(rep["drivers"]), 0)
                self.assertGreater(rep["meta"]["total_laps"], 0)


if __name__ == "__main__":
    unittest.main()
