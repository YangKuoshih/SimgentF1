"""Scope rules: the race and session on screen are the default; the question overrides them."""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tools import jolpica_sync as J  # noqa: E402
from app.tools.session_scope import explicit_session, resolve_scope  # noqa: E402

# Offline only while these tests run (a module-level replacement would leak into other
# test modules in the same `unittest discover` process).
_offline = patch.object(J, "_http", lambda url, retries=4: None)


def setUpModule():
    _offline.start()


def tearDownModule():
    _offline.stop()

MIAMI_SQ = {"year": 2026, "round": 4, "session": "sprint_qualifying", "race": "Miami Grand Prix"}


class ExplicitSessionTests(unittest.TestCase):
    def test_named_sessions(self):
        cases = {
            "who took sprint pole?": "sprint_qualifying",
            "how did he do in the sprint shootout?": "sprint_qualifying",
            "who won the sprint?": "sprint",
            "who was on pole?": "qualifying",
            "where did hamilton qualify?": "qualifying",
            "who won the grand prix?": "race",
            "who won?": None,
            "how did hamilton do?": None,
        }
        for q, want in cases.items():
            with self.subTest(q=q):
                self.assertEqual(explicit_session(q), want)


class ResolveScopeTests(unittest.TestCase):
    def test_unspecific_question_uses_the_screen(self):
        s = resolve_scope("Who won?", MIAMI_SQ)
        self.assertEqual((s["year"], s["round"], s["session"]), (2026, 4, "sprint_qualifying"))
        self.assertTrue(s["from_screen"] and s["session_from_screen"])

    def test_question_naming_a_session_overrides_the_screen_session(self):
        s = resolve_scope("Who won the grand prix?", MIAMI_SQ)
        self.assertEqual(s["session"], "race")
        self.assertTrue(s["from_screen"])
        self.assertFalse(s["session_from_screen"])

    def test_generic_qualifying_words_follow_the_sprint_qualifying_screen(self):
        self.assertEqual(resolve_scope("Who was on pole?", MIAMI_SQ)["session"], "sprint_qualifying")
        self.assertEqual(resolve_scope("Who took grand prix pole?", MIAMI_SQ)["session"], "qualifying")
        on_race = dict(MIAMI_SQ, session="race")
        self.assertEqual(resolve_scope("Who was on pole?", on_race)["session"], "qualifying")

    def test_question_naming_another_race_leaves_the_screen(self):
        s = resolve_scope("Who won the 2021 Abu Dhabi Grand Prix?", MIAMI_SQ)
        self.assertFalse(s["from_screen"])
        self.assertEqual(s["session"], "race")

    def test_conversation_about_another_race_leaves_the_screen(self):
        history = [{"role": "user", "content": "Who won the 2021 Abu Dhabi Grand Prix?"}]
        self.assertFalse(resolve_scope("Who finished second?", MIAMI_SQ, history)["from_screen"])

    def test_no_screen_context(self):
        self.assertIsNone(resolve_scope("Who won?", None))
        self.assertIsNone(resolve_scope("Who won?", {"session": "sprint"}))


if __name__ == "__main__":
    unittest.main()
