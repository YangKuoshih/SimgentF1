"""The answer gate (app/agent/gate.py): clarifying questions, replies to them, F1DB fact checks,
lap-time checks. Offline."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agent import gate  # noqa: E402
from app.tools import jolpica_sync as J  # noqa: E402
from app.tools.race_agent import answer_race_engineer_query as ask  # noqa: E402

_offline = mock.patch.object(J, "_http", lambda url, retries=4: None)


def setUpModule():
    _offline.start()


def tearDownModule():
    _offline.stop()


def never(q, ctx):
    raise AssertionError(f"the gate should not re-ask: {q}")


class FactChecks(unittest.TestCase):
    def test_a_wrong_winner_is_replaced_by_f1dbs(self):
        wrong = {"tool": "race_classification_lookup", "text": "**Jacky Ickx** took victory at the 1957 French Grand Prix."}
        out = gate.check("Who won the 1957 French Grand Prix?", {}, [], wrong, never)
        self.assertEqual(out["gate"]["verdict"], "corrected")
        self.assertTrue(out["text"].startswith("**Juan Manuel Fangio** won the **1957 French Grand Prix**"))
        self.assertIn("Checked against F1DB", out["text"])

    def test_a_right_answer_passes_untouched(self):
        right = {"tool": "race_classification_lookup", "text": "**Juan Fangio** took victory for Maserati at the 1957 French Grand Prix."}
        out = gate.check("Who won the 1957 French Grand Prix?", {}, [], dict(right), never)
        self.assertEqual(out["text"], right["text"])
        self.assertEqual(out["gate"]["verdict"], "passed")

    def test_wrong_fastest_lap_time_and_laps(self):
        out = gate.check("Who set the fastest lap at the 1957 French Grand Prix?", {}, [],
                         {"tool": "fastest_lap_lookup", "text": "**Luigi Musso** set the fastest lap: **2:20.000**."}, never)
        self.assertIn("2:22.400", out["text"])
        out = gate.check("How many laps was the 1957 French Grand Prix?", {}, [],
                         {"tool": "race_length_lookup", "text": "The race ran **70 laps**."}, never)
        self.assertIn("**77 laps**", out["text"])

    def test_sprint_answers_are_not_checked_against_the_grand_prix(self):
        sprint = {"tool": "sprint_classification_lookup", "text": "**Lando Norris** won the 2026 Miami Sprint."}
        out = gate.check("Who won the sprint at the 2026 Miami Grand Prix?", {}, [], dict(sprint), never)
        self.assertEqual(out["text"], sprint["text"])

    def test_a_lap_time_not_in_the_data_is_removed(self):
        resp = {"tool": "driver_performance_lookup",
                "text": "**Juan Fangio** won the 1957 French Grand Prix. His best lap was 2:01.234. He started on pole."}
        out = gate.check("How did Fangio do at the 1957 French Grand Prix?", {}, [], resp, never)
        self.assertNotIn("2:01.234", out["text"])
        self.assertIn("started on pole", out["text"])

    def test_refusals_are_left_alone(self):
        resp = {"tool": "season_out_of_range", "text": "The Formula 1 World Championship began in 1950."}
        self.assertIs(gate.check("Who won the 1949 British Grand Prix?", {}, [], resp, never), resp)

    def test_switch_off(self):
        resp = {"tool": "race_classification_lookup", "text": "**Jacky Ickx** won the 1957 French Grand Prix."}
        with mock.patch.dict(os.environ, {"SIMGENT_GATE": "off"}):
            self.assertIs(gate.check("Who won the 1957 French Grand Prix?", {}, [], resp, never), resp)


class Clarifications(unittest.TestCase):
    def test_two_races_fit(self):
        r = ask("Who won at Silverstone in 2020?", {}, [])
        self.assertEqual(r["tool"], "clarify")
        labels = [o["label"] for o in r["clarify"]["options"]]
        self.assertTrue(any("British" in l for l in labels) and any("70th Anniversary" in l for l in labels))

    def test_reply_picks_the_option(self):
        r = ask("Who won at Silverstone in 2020?", {}, [])
        history = [{"role": "user", "content": "Who won at Silverstone in 2020?"},
                   {"role": "assistant", "content": r["text"], "options": r["clarify"]["options"]}]
        self.assertIn("Max Verstappen", ask("the anniversary one", {}, history)["text"])
        self.assertIn("Lewis Hamilton", ask("1", {}, history)["text"])

    def test_a_new_question_is_not_taken_as_a_reply(self):
        opts = [{"label": "British Grand Prix (2 Aug)", "query": "Who won the 2020 British Grand Prix?"}]
        self.assertIsNone(gate.match_clarification("who won the 2019 british gp?", [{"role": "assistant", "options": opts}]))

    def test_two_drivers_of_a_season_but_not_a_far_better_known_one(self):
        self.assertEqual(ask("How did Schumacher do in 2001?", {}, [])["tool"], "clarify")
        self.assertEqual(ask("How many wins does Hill have?", {}, [])["tool"], "clarify")
        self.assertIn("Ayrton Senna", ask("How many poles did Senna get?", {}, [])["text"])

    def test_asks_only_once(self):
        history = [{"role": "user", "content": "Who won at Silverstone in 2020?"},
                   {"role": "assistant", "content": "Which one do you mean?",
                    "options": [{"label": "x", "query": "Who won the 2020 British Grand Prix?"}]}]
        r = ask("Who won at Silverstone in 2020?", {}, history)
        self.assertNotEqual(r["tool"], "clarify")
        self.assertIn("Assuming", r["text"])

    def test_live_score_counts_verdicts(self):
        before = gate.stats()["answers"]
        ask("Who won the 2019 British Grand Prix?", {}, [])
        self.assertEqual(gate.stats()["answers"], before + 1)


class CareerTotals(unittest.TestCase):
    def test_any_driver_from_f1db_not_the_hand_written_roster(self):
        self.assertIn("**Graham Hill** has **14 Grand Prix wins**", ask("How many wins did Graham Hill have?", {}, [])["text"])
        self.assertNotIn("Damon", ask("How many wins did Graham Hill have?", {}, [])["text"])


if __name__ == "__main__":
    unittest.main()
