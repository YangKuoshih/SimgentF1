"""Router (step 1 of docs/AGENT_ARCHITECTURE.md): tokenizer, masking, slots, intents file."""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agent.embedding import MODEL_DIR, StaticEmbedder, WordPiece  # noqa: E402
from app.agent.router import Router, load_intents, mask, slots  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HAVE_MODEL = os.path.exists(os.path.join(MODEL_DIR, "model.safetensors"))

# Token ids from the reference `tokenizers` library (potion-base-8M tokenizer.json), so the
# pure-Python WordPiece must agree id for id without depending on that library.
REFERENCE_IDS = {
    "Who was knocked out in Q1?": [1046, 1007, 5579, 1047, 1005, 59, 1493, 35],
    "How did Pérez do?": [1135, 1112, 9736, 1085, 35],
    "Hülkenberg's best lap: 1:31.399": [15015, 10035, 11, 61, 1196, 4007, 30, 21, 30, 1867, 18, 3470, 1689],
    "Senna’s 1988 crash — why?": [11417, 1538, 527, 61, 2003, 4829, 523, 1345, 35],
    "VER pitted on L33!!": [1316, 1105, 24901, 1012, 54, 21400, 5, 5],
    "日本 GP 🏁": [870, 882, 13252, 1],
}


@unittest.skipUnless(HAVE_MODEL, "run scripts/fetch_models.py")
class TokenizerTests(unittest.TestCase):
    def test_matches_reference_tokenizer(self):
        wp = WordPiece.from_tokenizer_json(os.path.join(MODEL_DIR, "tokenizer.json"))
        for text, ids in REFERENCE_IDS.items():
            self.assertEqual(wp.encode(text), ids, text)

    def test_vectors_are_unit_length(self):
        v = StaticEmbedder.load().embed(["who won the race", ""])
        self.assertAlmostEqual(float((v[0] ** 2).sum()), 1.0, places=5)
        self.assertEqual(float(abs(v[1]).sum()), 0.0)


class MaskAndSlotTests(unittest.TestCase):
    def test_names_and_years_are_masked(self):
        self.assertEqual(mask("Who won the 2026 Bahrain Grand Prix?"), "who won the grand prix ?")
        self.assertEqual(mask("How did Verstappen do?"), "how did do ?")
        self.assertEqual(mask("Who was second in the 2023 Mexico City Grand Prix?"), "who was second in the grand prix ?")

    def test_slots(self):
        self.assertTrue(slots("How did Hamilton do?")["driver"])
        self.assertTrue(slots("how did he do")["driver"])
        self.assertFalse(slots("Who won the 2026 Bahrain Grand Prix?")["driver"])  # a place, not a driver
        self.assertTrue(slots("who was the runner up")["position"])
        self.assertTrue(slots("who was P3")["position"])
        self.assertTrue(slots("who went out in SQ2")["segment"])


class IntentsFileTests(unittest.TestCase):
    def test_every_tool_exists_in_the_engine(self):
        src = ""
        for f in ("app/tools/race_agent.py", "app/tools/session_scope.py", "app/tools/f1_history.py"):
            with open(os.path.join(ROOT, f), encoding="utf-8") as fh:
                src += fh.read()
        literal = set(re.findall(r'"tool": "([a-z0-9_]+)"', src))
        per_session = re.findall(r'"tool": f"\{session\}_([a-z0-9_{}]+)"', src)
        tools = set(literal)
        for suffix in per_session + ["segment_lookup", "segment_driver_lookup"]:
            for session in ("sprint", "qualifying", "sprint_qualifying"):
                tools.add(f"{session}_{suffix}")
        for intent in load_intents():
            for tool in intent.tools:
                self.assertIn(tool, tools, f"{intent.name}: unknown tool {tool}")

    def test_intents_are_well_formed(self):
        intents = load_intents()
        self.assertGreaterEqual(len(intents), 20)
        for i in intents:
            self.assertGreaterEqual(len(i.examples), 4, i.name)
            for slot in i.requires + i.excludes:
                self.assertIn(slot, ("driver", "position", "year", "segment"), i.name)


class RoutingTests(unittest.TestCase):
    CASES = {
        "who was knocked out in Q1": "qualifying_segments",
        "who won the race": "session_result",
        "how did Leclerc do": "driver_result",
        "who was on pole": "pole_position",
        "when did Verstappen pit": "pit_strategy",
    }

    def test_lexical_fallback_without_a_model(self):
        router = Router(load_intents(), None)
        self.assertEqual(router.method, "lexical")
        for q, intent in self.CASES.items():
            self.assertEqual(router.route(q).best, intent, q)

    @unittest.skipUnless(HAVE_MODEL, "run scripts/fetch_models.py")
    def test_embedding_router(self):
        router = Router(load_intents(), StaticEmbedder.load())
        for q, intent in self.CASES.items():
            self.assertEqual(router.route(q).intent, intent, q)
        # a segment named in the question rules out the race-level fastest lap
        self.assertNotEqual(router.route("fastest lap of Q1").intent, "fastest_lap")


class CanonicalPhrasingTests(unittest.TestCase):
    """Every intent's canonical phrasing (what the router asks the engine, step 3a) must be
    answered by one of that intent's own tools, in a context where the answer exists."""
    RACE = {"year": 2026, "round": 16, "session": "race", "race": "Bahrain Grand Prix in Malaysia"}
    CONTEXT = {"qualifying_segments": dict(RACE, session="qualifying"),
               "pole_position": dict(RACE, session="qualifying"),
               "race_story": {"year": 2021, "round": 22, "session": "race", "race": "Abu Dhabi Grand Prix"}}
    SLOTS = {"driver": "Albon", "driver_poss": "Hamilton's", "driver2": "Leclerc", "position": "P4",
             "segment": "Q1", "year": "2008", "race": "", "race_name": "this race"}
    # a driver with a career profile; Albon retired in this race (for driver_retirement)
    SLOTS_FOR = {"driver_career": {"driver": "Hamilton"}, "head_to_head": {"driver": "Hamilton"}}

    def test_canonical_phrasings_are_answered_by_their_intent(self):
        from app.tools import jolpica_sync as J
        from app.tools import race_agent as A
        from unittest.mock import patch
        with patch.object(J, "_http", lambda url, retries=4: None):
            for intent in load_intents():
                if not intent.canonical:
                    continue
                q = intent.canonical
                for k, v in {**self.SLOTS, **self.SLOTS_FOR.get(intent.name, {})}.items():
                    q = q.replace("{" + k + "}", v)
                q = " ".join(q.split())
                tool = A._answer_once(q, self.CONTEXT.get(intent.name, self.RACE), []).get("tool")
                self.assertIn(tool, intent.tools, f"{intent.name}: {q!r} answered by {tool}")


class ShadowLoggingTests(unittest.TestCase):
    def test_logs_names_and_scores_never_the_question(self):
        from frontend import main as M
        with self.assertLogs("simgent.api", level="INFO") as logs:
            M._router_shadow("How did Hamilton do in the secret test question?", "driver_performance_lookup")
        line = "\n".join(logs.output)
        self.assertIn("router_shadow", line)
        self.assertIn("driver_performance_lookup", line)
        self.assertNotIn("secret test question", line)


if __name__ == "__main__":
    unittest.main()
