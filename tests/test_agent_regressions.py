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


class ClassifiedNonFinishers(unittest.TestCase):
    def test_classified_despite_retiring(self):
        r = ask("How did Perez do?", view(2021, 22, "Abu Dhabi Grand Prix"), [])
        self.assertIn("classified **P15**", r["text"])
        self.assertNotIn("finished **DNF", r["text"])

    def test_disqualified(self):
        r = ask("How did Hamilton do?", view(2023, 18, "United States Grand Prix"), [])
        self.assertIn("disqualified", r["text"])


class ConversationRace(unittest.TestCase):
    MIAMI_SQ = {"year": 2026, "round": 4, "session": "sprint_qualifying", "race": "Miami Grand Prix"}

    def _talk(self, questions):
        history = []
        for q in questions:
            history += [{"role": "user", "content": q, "view": "2026-4"},
                        {"role": "assistant", "content": "...", "view": "2026-4"}]
        return history

    def test_follow_ups_keep_the_named_race(self):
        from app.tools.race_agent import race_from_history
        h = self._talk(["Who won the 2021 Abu Dhabi Grand Prix?", "Who finished second?", "And who was third?"])
        self.assertEqual(race_from_history(h, 2026), (2021, 22))

    def test_circuit_takes_the_year_from_an_earlier_question_only(self):
        from app.tools.race_agent import race_from_history
        h = self._talk(["Who won the 2021 Abu Dhabi Grand Prix?", "What about Monaco?"])
        self.assertEqual(race_from_history(h, 2026), (2021, 5))

    def test_no_phantom_race_from_a_later_season_question(self):
        from app.tools.race_agent import race_from_history
        h = self._talk(["Who won the 2021 Abu Dhabi Grand Prix?", "What about Monaco?",
                        "Who won the 2024 world championship?", "What about 2016?"])
        self.assertIsNone(race_from_history(h, 2026))  # a season question ends the race focus

    def test_unspecific_question_returns_to_the_screen_after_season_talk(self):
        h = self._talk(["Who won the 2021 Abu Dhabi Grand Prix?", "Who won the 2024 world championship?"])
        r = ask("How did Piastri do?", self.MIAMI_SQ, h)
        self.assertIn("Sprint Qualifying", r["text"])
        self.assertIn("P3", r["text"])


if __name__ == "__main__":
    unittest.main()
