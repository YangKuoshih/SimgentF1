"""Chat history must not override the race on screen.

Regression: after talking about the 2026 Australian GP and switching the replay to R16,
"Explain VER's pit strategy" was answered for Australia, and "Where did the race
change?" became a driver card for a driver named earlier.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tools.race_agent import answer_race_engineer_query as ask, scope_history_to_view  # noqa: E402

R16 = {"year": 2026, "round": 16, "session": "race", "race": "Bahrain Grand Prix in Malaysia"}
AUSTRALIA_TALK = [
    {"role": "user", "content": "Who won the 2026 Australian Grand Prix?", "view": "2026-1"},
    {"role": "assistant", "content": "Max Verstappen won the 2026 Australian Grand Prix. Lindblad was P8.", "view": "2026-1"},
]


class ChatViewScopeTests(unittest.TestCase):
    def test_turns_from_another_race_are_dropped(self):
        same = [{"role": "user", "content": "Who won?", "view": "2026-16"}]
        self.assertEqual(scope_history_to_view(AUSTRALIA_TALK + same, R16), same)

    def test_untagged_history_is_kept(self):
        untagged = [{"role": "user", "content": "Who won the 2021 Abu Dhabi Grand Prix?"}]
        self.assertEqual(scope_history_to_view(untagged, R16), untagged)

    def test_untagged_turns_before_tagged_ones_count_as_another_view(self):
        old = [{"role": "user", "content": "Who won the 2026 Australian Grand Prix?"}]
        same = [{"role": "user", "content": "Who won?", "view": "2026-16"}]
        self.assertEqual(scope_history_to_view(old + same, R16), same)

    def test_pit_strategy_follows_race_on_screen_after_switch(self):
        r = ask("Explain VER's pit strategy", R16, AUSTRALIA_TALK)
        self.assertIn("3-stop", r["text"])
        self.assertIn("Lap 9, Lap 33, Lap 43", r["text"])

    def test_race_level_question_is_not_hijacked_by_earlier_driver(self):
        history = [{"role": "user", "content": "Explain VER's pit strategy", "view": "2026-16"},
                   {"role": "assistant", "content": "Max Verstappen ran a 3-stop strategy.", "view": "2026-16"}]
        r = ask("Where did the race change?", R16, history)
        self.assertEqual(r.get("tool"), "safety_car_analysis")

    def test_pronoun_follow_up_still_uses_earlier_driver(self):
        history = [{"role": "user", "content": "How did Lindblad do?", "view": "2026-16"},
                   {"role": "assistant", "content": "Arvid Lindblad finished P10 for RB F1 Team.", "view": "2026-16"}]
        r = ask("Where did he start?", R16, history)
        self.assertIn("Lindblad", r["text"])
        self.assertRegex(r["text"], r"P22|22")

    def test_same_view_follow_up_about_named_race_still_works(self):
        history = [{"role": "user", "content": "Who won the 2021 Abu Dhabi Grand Prix?", "view": "2026-16"},
                   {"role": "assistant", "content": "Max Verstappen won the 2021 Abu Dhabi Grand Prix.", "view": "2026-16"}]
        r = ask("Who finished second?", R16, history)
        self.assertIn("Hamilton", r["text"])


class DriverPhrasingTests(unittest.TestCase):
    def test_how_did_driver_do_answers_about_that_driver(self):
        for q in ["How did Lindblad do?", "How did Arvid Lindblad perform?"]:
            with self.subTest(q=q):
                r = ask(q, R16, [])
                self.assertTrue(r["text"].lstrip("*").startswith("Arvid Lindblad"), r["text"][:80])
                self.assertIn("P10", r["text"])

    def test_how_did_the_race_go_is_still_a_race_summary(self):
        r = ask("How did the race go?", R16, [])
        self.assertEqual(r.get("tool"), "race_classification_lookup")


if __name__ == "__main__":
    unittest.main()
