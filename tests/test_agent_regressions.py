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


class SprintQualifyingBeforeTheSprint(unittest.TestCase):
    """Sprint Qualifying is cached before the sprint has a result (Friday/Saturday)."""

    def test_race_name_comes_from_the_schedule(self):
        if J.sprint_results(2026, 17, net=False):
            self.skipTest("the 2026 Singapore sprint result is cached now")
        r = ask("Who was fastest?", view(2026, 17, "Singapore Grand Prix", "sprint_qualifying"), [])
        self.assertIn("Verstappen", r["text"])
        self.assertIn("2026 Singapore Grand Prix · Sprint Qualifying", r["text"])
        self.assertNotIn("Round 17", r["text"])


class QualifyingSegmentQuestions(unittest.TestCase):
    Q = view(2026, 16, "Bahrain Grand Prix in Malaysia", "qualifying")

    def test_knocked_out_in_q1(self):
        r = ask("Who was knocked out in Q1?", self.Q, [])
        self.assertIn("Knocked out in **Q1** (6)", r["text"])
        self.assertIn("Sergio Pérez (P22)", r["text"])
        self.assertNotIn("retirement", r["text"])

    def test_made_it_to_q3(self):
        self.assertIn("**10 drivers** made it to **Q3**", ask("Who made it to Q3?", self.Q, [])["text"])

    def test_fastest_in_a_segment_is_not_the_pole_lap(self):
        r = ask("Who was fastest in Q2?", self.Q, [])
        self.assertIn("fastest in **Q2** with **1:35.696**", r["text"])

    def test_driver_without_a_time_in_a_segment(self):
        self.assertIn("set no time", ask("Did Colapinto set a time in Q2?", self.Q, [])["text"])

    def test_didnt_make_q3_means_out_in_q2(self):
        self.assertIn("Knocked out in **Q2**", ask("Who didn't make Q3?", self.Q, [])["text"])

    def test_sprint_qualifying_segments(self):
        sq = view(2026, 17, "Singapore Grand Prix", "sprint_qualifying")
        self.assertIn("Knocked out in **SQ1**", ask("Who was eliminated in SQ1?", sq, [])["text"])
        self.assertIn("best lap of **1:31.399**", ask("What was Leclerc's best lap?", sq, [])["text"])


class NoAnswerFromAnotherRace(unittest.TestCase):
    def test_grand_prix_not_run_yet(self):
        if J.results(2026, 17, net=False):
            self.skipTest("the 2026 Singapore Grand Prix result is cached now")
        r = ask("Who won the grand prix?", view(2026, 17, "Singapore Grand Prix", "sprint_qualifying"), [])
        self.assertEqual(r.get("tool"), "race_not_run")
        self.assertIn("no race result for the **2026 Singapore Grand Prix** yet", r["text"])
        self.assertNotIn("Australian", r["text"])

    def test_general_questions_still_answered_when_the_race_has_no_result(self):
        if J.results(2026, 17, net=False):
            self.skipTest("the 2026 Singapore Grand Prix result is cached now")
        r = ask("How can I simulate an undercut strategy?", view(2026, 17, "Singapore Grand Prix", "sprint_qualifying"), [])
        self.assertEqual(r.get("tool"), "pit_strategy_explanation")
        self.assertTrue(r.get("a2ui_card"))


class EstimatedQualifyingQuotesNoTimes(unittest.TestCase):
    def test_grid_estimate_has_no_lap_times(self):
        if J.qualifying_results(2021, 22, net=False):
            self.skipTest("2021 Abu Dhabi qualifying is cached now")
        ctx = view(2021, 22, "Abu Dhabi Grand Prix", "qualifying")
        r = ask("Where did Hamilton qualify?", ctx, [])
        self.assertIn("P2", r["text"])
        self.assertNotRegex(r["text"], r"\d:\d\d\.\d{3}")
        self.assertIn("isn't in the data", ask("Who was knocked out in Q1?", ctx, [])["text"])


if __name__ == "__main__":
    unittest.main()
