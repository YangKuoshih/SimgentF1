"""Qualifying replays follow the knockout format: each segment's cars run one flying lap at
their real time, knocked-out drivers run no further laps, and the final segment decides the
top of the grid. Offline, cached sessions only."""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tools import jolpica_sync as J  # noqa: E402
from app.tools import race_replay as R  # noqa: E402

_offline = patch.object(J, "_http", lambda url, retries=4: None)


def setUpModule():
    _offline.start()


def tearDownModule():
    _offline.stop()


class KnockoutQualifyingTests(unittest.TestCase):
    def check_knockout(self, model, names):
        segs = model["meta"]["segments"]
        drivers = model["drivers"]
        self.assertEqual([s["name"] for s in segs], names)
        self.assertEqual(model["meta"]["total_laps"], len(segs))
        for k, seg in enumerate(segs):
            runners = [d for d in drivers if len(d["seg_start"]) > k]
            self.assertEqual(seg["cars"], len(runners))
            for d in runners:
                # Each lap starts and ends inside its own segment, at the driver's real time.
                self.assertGreaterEqual(d["seg_start"][k], seg["start"])
                self.assertLessEqual(d["cum"][k], seg["end"])
                if d["lap_times"][k]:
                    self.assertAlmostEqual(d["cum"][k] - d["seg_start"][k], d["lap_times"][k], places=2)
        for d in drivers:
            # Knocked-out drivers stop after their last segment; the rest reach the final one.
            self.assertEqual(len(d["cum"]), d["laps"])
            self.assertEqual(d["eliminated_in"] is None, d["laps"] == len(segs))
        # Everyone knocked out in an earlier segment is classified behind everyone who went on.
        for k in range(len(segs) - 1):
            out = [d["finish"] for d in drivers if d["laps"] == k + 1]
            on = [d["finish"] for d in drivers if d["laps"] > k + 1]
            if out and on:
                self.assertLess(max(on), min(out))

    def test_grand_prix_qualifying(self):
        m = R.build_replay(2026, 16, session_type="qualifying")
        self.check_knockout(m, ["Q1", "Q2", "Q3"])
        self.assertEqual([s["cars"] for s in m["meta"]["segments"]], [22, 16, 10])

    def test_sprint_qualifying(self):
        m = R.build_replay(2026, 17, session_type="sprint_qualifying")
        self.check_knockout(m, ["SQ1", "SQ2", "SQ3"])

    def test_sprint_shootout_2023(self):
        self.check_knockout(R.build_replay(2023, 4, session_type="sprint_qualifying"), ["SQ1", "SQ2", "SQ3"])

    def test_single_session_before_the_knockout_format(self):
        m = R.build_replay(1995, 1, session_type="qualifying")
        self.check_knockout(m, ["Qualifying"])
        self.assertFalse([e for e in m["events"] if "eliminated" in e["message"]])


if __name__ == "__main__":
    unittest.main()
