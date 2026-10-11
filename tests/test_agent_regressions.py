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

    def test_pole_is_answered_when_only_the_race_is_missing(self):
        if J.results(2026, 17, net=False) or not J.qualifying_results(2026, 17, net=False):
            self.skipTest("needs Singapore qualifying cached and its race not yet")
        r = ask("Who took pole?", view(2026, 17, "Singapore Grand Prix", "qualifying"), [])
        self.assertNotEqual(r.get("tool"), "race_not_run")
        self.assertIn("Verstappen", r["text"])

    def test_a_qualifying_question_is_not_blocked_by_the_missing_race(self):
        if J.results(2026, 17, net=False) or not J.qualifying_results(2026, 17, net=False):
            self.skipTest("needs Singapore qualifying cached and its race not yet")
        from app.agent.router import get_router
        if get_router().method != "embedding":
            self.skipTest("the router only re-asks with the embedding model (scripts/fetch_models.py)")
        r = ask("who got bounced in the first session?", view(2026, 17, "Singapore Grand Prix"), [])
        self.assertEqual(r.get("tool"), "qualifying_segment_lookup")
        self.assertIn("Knocked out in **Q1**", r["text"])

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


class DriverExitQuestionsInSessions(unittest.TestCase):
    """'When did Russell leave the qualifying race?' answered the pole sitter, not Russell."""
    def test_leave_qualifying_answers_the_driver(self):
        if not J.qualifying_results(2026, 17, net=False):
            self.skipTest("needs Singapore qualifying cached")
        r = ask("When did George Russell leave the qualifying race", view(2026, 17, "Singapore Grand Prix"), [])
        self.assertEqual(r.get("tool"), "qualifying_driver_lookup")
        self.assertIn("George Russell", r["text"])
        self.assertIn("wasn't knocked out", r["text"])

    def test_sprint_retirement_answers_the_driver(self):
        ctx = view(2026, 17, "Singapore Grand Prix", "sprint_qualifying")
        for q in ("When did George Russell leave the sprint?", "Why did Russell DNF in the sprint?"):
            r = ask(q, ctx, [])
            self.assertEqual(r.get("tool"), "sprint_driver_lookup", q)
            self.assertIn("did not finish the **Sprint**", r["text"])

    def test_who_retired_in_the_sprint(self):
        r = ask("Who retired in the sprint?", view(2026, 17, "Singapore Grand Prix"), [])
        self.assertEqual(r.get("tool"), "sprint_dnf_lookup")
        self.assertIn("George Russell", r["text"])

    def test_exit_this_race_is_not_a_career_profile(self):
        r = ask("When did Max Verstappen exit this race?", view(2026, 16, "Bahrain Grand Prix in Malaysia"), [])
        self.assertNotEqual(r.get("tool"), "driver_career_history_lookup")
        self.assertIn("did not exit or retire", r["text"])
        r = ask("When did Max Verstappen leave Red Bull?", view(2026, 16, "Bahrain Grand Prix in Malaysia"), [])
        self.assertEqual(r.get("tool"), "driver_career_history_lookup")


class DriverWeekendSummary(unittest.TestCase):
    """'What happened to Russell during the sprint weekend' answered the sprint winner."""
    def test_sprint_weekend_lists_each_session(self):
        r = ask("What happened to Russell during the sprint weekend", view(2026, 17, "Singapore Grand Prix"), [])
        self.assertEqual(r.get("tool"), "weekend_driver_summary")
        self.assertIn("**Sprint Qualifying**", r["text"])
        self.assertIn("did not finish the **Sprint**", r["text"])
        self.assertNotIn("Max Verstappen", r["text"])

    def test_weekend_without_a_sprint_lists_no_sprint(self):
        r = ask("What happened to Verstappen this weekend?", view(2026, 16, "Bahrain Grand Prix in Malaysia"), [])
        self.assertEqual(r.get("tool"), "weekend_driver_summary")
        self.assertNotIn("Sprint", r["text"])
        self.assertIn("**Race**", r["text"])


class NoSprintWeekend(unittest.TestCase):
    """A weekend without a Sprint once got a Sprint made up from the Grand Prix result."""
    def test_sprint_question_on_a_weekend_without_one(self):
        for q in ("Who won the sprint?", "When did Russell leave the sprint?", "Who took sprint pole?"):
            r = ask(q, view(2026, 16, "Bahrain Grand Prix in Malaysia"), [])
            self.assertEqual(r.get("tool"), "no_sprint_weekend", q)
            self.assertIn("had **no Sprint**", r["text"])
            self.assertIn("R17 Singapore", r["text"])

    def test_no_sprint_is_built_from_the_grand_prix(self):
        from app.tools import race_replay
        rep = race_replay.build_replay(2026, 16, net=False, session_type="sprint")
        self.assertNotEqual((rep or {}).get("meta", {}).get("session_type"), "sprint")

    def test_which_sprint_when_none_is_named(self):
        r = ask("Who won the sprint in 2024?", None, [])
        self.assertEqual(r.get("tool"), "no_sprint_weekend")
        self.assertIn("Which Sprint do you mean?", r["text"])
        r = ask("Who won the sprint in 1995?", None, [])
        self.assertIn("introduced Sprint races in **2021**", r["text"])

    def test_real_sprints_still_answered(self):
        r = ask("Who won the sprint?", view(2026, 17, "Singapore Grand Prix"), [])
        self.assertEqual(r.get("tool"), "sprint_classification_lookup")
        self.assertIn("Max Verstappen", r["text"])


class LiveRunFindings(unittest.TestCase):
    """Found by the 373-question Playwright run against the live site (October 2026)."""
    def test_who_won_the_race_on_a_qualifying_screen_means_the_grand_prix(self):
        if J.results(2026, 17, net=False):
            self.skipTest("the 2026 Singapore Grand Prix result is cached now")
        r = ask("Who won the race?", view(2026, 17, "Singapore Grand Prix", "qualifying"), [])
        self.assertEqual(r.get("tool"), "race_not_run")
        r = ask("Who won the race?", view(2026, 16, "Bahrain Grand Prix in Malaysia", "qualifying"), [])
        self.assertIn("Max Verstappen", r["text"])
        self.assertNotIn("pole", r["text"].lower().split("fastest lap")[0])

    def test_another_season_named_ignores_the_round_on_screen(self):
        r = ask("Who won the sprint in 2024?", view(2026, 16, "Bahrain Grand Prix in Malaysia"), [])
        self.assertIn("Which Sprint do you mean?", r["text"])
        self.assertNotIn("Italian", r["text"])

    def test_estimated_qualifying_uses_the_real_qualifying_order(self):
        from app.tools import race_replay
        if J.qualifying_results(2021, 10, net=False):
            self.skipTest("2021 British GP qualifying is cached now")
        rep = race_replay.build_replay(2021, 10, net=False, session_type="qualifying")
        self.assertTrue(rep["meta"]["times_estimated"])
        codes = [d["code"] for d in rep["drivers"]]
        self.assertEqual(codes[0], "HAM")  # 2021 sprint weekend: qualifying set the Sprint grid
        self.assertNotEqual(codes[0], "PER")  # grid 0 (his pit-lane start in the GP) is not pole


class GridQuestions(unittest.TestCase):
    RACE = view(2026, 16, "Bahrain Grand Prix in Malaysia")

    def test_who_started_is_not_a_misspelled_driver(self):
        # "started" fuzzy-matched "Stewart" and returned Jackie Stewart's career profile
        r = ask("who started P3", self.RACE, [])
        self.assertEqual(r.get("tool"), "starting_grid_lookup")
        self.assertNotIn("Stewart", r["text"])

    def test_whole_grid_and_front_row(self):
        for q in ("what was the starting grid", "who was on the front row"):
            r = ask(q, self.RACE, [])
            self.assertEqual(r.get("tool"), "starting_grid_lookup", q)
            self.assertIn("Front row", r["text"])

    def test_misspelled_names_still_resolve(self):
        from app.tools import f1_history as H
        self.assertEqual(H.resolve_historical_driver("tell me about schmacur")["name"], "Michael Schumacher")
        self.assertEqual(H.resolve_historical_driver("versappen career")["name"], "Max Verstappen")


class PracticeBeforeResults(unittest.TestCase):
    def test_fp1_is_not_answered_with_race_results(self):
        r = ask("FP1 lap times", view(2026, 16, "Bahrain Grand Prix in Malaysia"), [])
        self.assertEqual(r.get("tool"), "free_practice_telemetry_lookup")


if __name__ == "__main__":
    unittest.main()
