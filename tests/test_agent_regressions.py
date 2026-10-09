"""Regressions found by the live multi-turn accuracy run (October 2026). Offline, cached races only."""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tools import jolpica_sync as J  # noqa: E402
from app.tools.race_agent import answer_race_engineer_query as ask  # noqa: E402

_offline = patch.object(J, "_http", lambda url, retries=4: None)


def setUpModule():
    _offline.start()


def tearDownModule():
    _offline.stop()


def view(year, rnd, race, session="race"):
    return {"year": year, "round": rnd, "session": session, "race": race}


class StoryPagesDoNotTakeDriverQuestions(unittest.TestCase):
    def test_driver_result_on_an_iconic_race(self):
        r = ask("How did Tsunoda do?", view(2021, 22, "Abu Dhabi Grand Prix"), [])
        self.assertIn("Tsunoda", r["text"])
        self.assertIn("P4", r["text"])

    def test_pit_strategy_on_an_iconic_race(self):
        r = ask("Explain VER's pit strategy", view(2021, 22, "Abu Dhabi Grand Prix"), [])
        self.assertIn("Lap 13, Lap 36, Lap 53", r["text"])

    def test_story_still_answers_story_questions(self):
        r = ask("What happened in this race?", view(2021, 22, "Abu Dhabi Grand Prix"), [])
        self.assertEqual(r.get("tool"), "historic_race_moment_lookup")


class RetirementMeansTheRaceInRaceContext(unittest.TestCase):
    def test_senna_monza_1988(self):
        r = ask("When did Senna retire?", view(1988, 12, "Italian Grand Prix"), [])
        self.assertIn("Lap 49", r["text"])

    def test_retire_from_f1_is_a_career_question(self):
        r = ask("When did Hamilton retire from F1?", view(2021, 22, "Abu Dhabi Grand Prix"), [])
        self.assertIn("Career Profile", r["text"])

    def test_cause_wording_has_no_ticker_label(self):
        r = ask("When did Moss retire?", view(1956, 1, "Argentine Grand Prix"), [])
        self.assertIn("Lap 82", r["text"])
        self.assertIn("engine failure", r["text"])
        self.assertNotIn("OUT —", r["text"].upper().replace("**", ""))


class DriversInTheRaceBeatFuzzyNameMatches(unittest.TestCase):
    def test_landi_is_chico_landi_not_lando_norris(self):
        r = ask("How did Landi do?", view(1956, 1, "Argentine Grand Prix"), [])
        self.assertIn("Chico Landi", r["text"])
        self.assertNotIn("Norris", r["text"])


class HistoryRaceComesFromTheUsersQuestions(unittest.TestCase):
    def test_assistant_mentions_of_other_races_do_not_move_the_conversation(self):
        history = [
            {"role": "user", "content": "Tell me about the V10 era", "view": "1956-1"},
            {"role": "assistant", "content": "The 1995-2005 V10 era peaked at the 1999 Canadian Grand Prix ...", "view": "1956-1"},
        ]
        r = ask("When did Moss retire?", view(1956, 1, "Argentine Grand Prix"), history)
        self.assertIn("Argentine", r["text"])
        self.assertNotIn("Canadian", r["text"])


if __name__ == "__main__":
    unittest.main()
