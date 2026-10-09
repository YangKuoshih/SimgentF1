"""
F1 Simgent - F1 History, Driver Career & Research Intelligence Test Suite
Tests fuzzy driver resolution, historical research queries, career timelines,
technical eras, all-time records, and guarantees zero session hijacking.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import asyncio

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from app.tools.f1_history import (
    resolve_historical_driver,
    lookup_driver_career,
    lookup_f1_era,
    lookup_all_time_records,
    lookup_season_champion,
    HISTORICAL_DRIVERS
)
from app.tools.race_agent import answer_race_engineer_query
from app.tools.guardrails import evaluate_all_guardrails
from frontend.main import api_chat, ChatMessage


class TestF1HistoryAgent(unittest.TestCase):

    # =========================================================================
    # SUITE 1: FUZZY DRIVER RESOLUTION & TYPO RESILIENCE
    # =========================================================================
    def test_fuzzy_driver_resolution_with_typos(self):
        cases = [
            ("when did michael schmacur race in what era?", "michael_schumacher", "Michael Schumacher"),
            ("what era did shumacher drive in?", "michael_schumacher", "Michael Schumacher"),
            ("how many titles does schumi have?", "michael_schumacher", "Michael Schumacher"),
            ("ayrton sena qualifying record", "ayrton_senna", "Ayrton Senna"),
            ("how many championships does versappen have?", "max_verstappen", "Max Verstappen"),
            ("tell me about niki louda", "lauda", "Niki Lauda"),
            ("what teams did allonso drive for?", "alonso", "Fernando Alonso"),
            ("how many wins did vetel have?", "vettel", "Sebastian Vettel"),
            ("tell me about the flying finn hakinen", "hakkinen", "Mika Häkkinen"),
            ("lewis hamiltonn titles", "hamilton", "Lewis Hamilton"),
        ]
        for query, expected_id, expected_name in cases:
            driver = resolve_historical_driver(query)
            self.assertIsNotNone(driver, f"Failed to resolve driver for query: '{query}'")
            self.assertEqual(driver["id"], expected_id)
            self.assertEqual(driver["name"], expected_name)

    # =========================================================================
    # SUITE 2: NO ACCIDENTAL HIJACKING OF SESSIONS OR DRIVERS
    # =========================================================================
    def test_no_session_winner_hijacking_on_historical_query(self):
        """
        Critical regression test:
        When viewing an unrelated session (e.g. 1988 race with Senna P1),
        asking about Michael Schumacher ('schmacur') must NEVER hallucinate
        about Ayrton Senna or the session winner.
        """
        senna_ctx = {
            "year": 1988,
            "round": 8,
            "session": "race",
            "selected": "SEN",
            "driver": "SEN"
        }
        query = "when did michael schmacur race in what era?"
        res = answer_race_engineer_query(query, context=senna_ctx)

        self.assertIsNotNone(res)
        self.assertEqual(res.get("tool"), "driver_career_history_lookup")
        self.assertEqual(res.get("intent"), "F1 Historical Career & Era Research Analysis")

        text = res.get("text", "")
        self.assertIn("Michael Schumacher", text)
        self.assertIn("1991–2006", text)
        self.assertIn("7 Championships", text)
        self.assertIn("V10", text)
        # Verify Senna is NOT mentioned as the answer
        self.assertNotIn("Ayrton Senna finished P1", text)

        # Verify A2UI card
        card = res.get("a2ui_card")
        self.assertIsNotNone(card)
        self.assertEqual(card.get("type"), "driver_career_card")
        self.assertIn("Michael Schumacher", card.get("title", ""))
        self.assertEqual(card.get("target", {}).get("year"), 1998)
        self.assertEqual(card.get("target", {}).get("driver"), "MSC")

    # =========================================================================
    # SUITE 3: ALL-TIME RECORDS LEADERBOARDS
    # =========================================================================
    def test_all_time_records_queries(self):
        queries = [
            ("who has the most race wins in f1 history?", "Most Formula 1 Grand Prix Victories"),
            ("who has the most pole positions in f1?", "Most Formula 1 Pole Positions"),
            ("most championships in f1", "Most Formula 1 World Drivers' Championships"),
            ("who is the youngest f1 world champion?", "Youngest Formula 1 World Champions"),
        ]
        for query, expected_title in queries:
            res = answer_race_engineer_query(query)
            self.assertIsNotNone(res)
            self.assertEqual(res.get("tool"), "f1_all_time_records_lookup")
            self.assertIn(expected_title, res.get("text", ""))
            card = res.get("a2ui_card")
            self.assertIsNotNone(card)
            self.assertEqual(card.get("type"), "records_card")

    # =========================================================================
    # SUITE 4: HISTORICAL TECHNICAL ERAS (1950–2026+)
    # =========================================================================
    def test_historical_eras_queries(self):
        res_v10 = answer_race_engineer_query("what was the v10 era in f1?")
        self.assertIsNotNone(res_v10)
        self.assertEqual(res_v10.get("tool"), "f1_era_regulations_lookup")
        self.assertIn("1995–2005 3.0L V10 Golden Era", res_v10.get("text", ""))
        self.assertIn("950 HP", res_v10.get("text", ""))

        res_turbo = answer_race_engineer_query("tell me about the 1980s turbo monster era")
        self.assertIsNotNone(res_turbo)
        self.assertEqual(res_turbo.get("tool"), "f1_era_regulations_lookup")
        self.assertIn("1400", res_turbo.get("text", ""))

    # =========================================================================
    # SUITE 5: HISTORICAL CHAMPIONSHIP ROSTER (1950–2025)
    # =========================================================================
    def test_historical_season_championship_queries(self):
        cases = [
            ("who won the championship in 1988?", "senna", "Ayrton Senna", "McLaren-Honda"),
            ("who won the 1976 world championship?", "hunt", "James Hunt", "McLaren-Ford"),
            ("who won the 2004 world championship?", "michael_schumacher", "Michael Schumacher", "Ferrari"),
            ("who won the 1950 championship?", "farina", "Giuseppe Farina", "Alfa Romeo"),
        ]
        for query, expected_id, expected_champion, expected_team in cases:
            res = answer_race_engineer_query(query)
            self.assertIsNotNone(res)
            self.assertEqual(res.get("tool"), "historical_championship_lookup")
            if res.get("driver_id") is not None:
                self.assertEqual(res["driver_id"], expected_id)
            else:
                # Curated fallback has no provider ID; validate its displayed name.
                self.assertIn(expected_champion, res.get("text", ""))
            self.assertIn(expected_team, res.get("text", ""))

    def test_farina_aliases_keep_the_same_champion_identity(self):
        for given_name in ("Giuseppe", "Nino"):
            with self.subTest(given_name=given_name):
                standings = [
                    {"Driver": {"driverId": "farina", "givenName": given_name,
                                "familyName": "Farina"}, "points": "30", "wins": "3",
                     "Constructors": [{"name": "Alfa Romeo"}]},
                    {"Driver": {"driverId": "fangio", "givenName": "Juan",
                                "familyName": "Fangio"}, "points": "27", "wins": "3"},
                ]
                with patch("app.tools.jolpica_sync.driver_standings", return_value=standings):
                    result = answer_race_engineer_query("who won the 1950 championship?")
                self.assertEqual(result["driver_id"], "farina")
                self.assertIn(f"**{given_name} Farina**", result["text"])
                self.assertIn("Alfa Romeo", result["text"])

    # =========================================================================
    # SUITE 6: GUARDRAILS & FULL CHAT API INTEGRATION
    # =========================================================================
    def test_guardrails_pass_and_api_chat_flow(self):
        query = "when did michael schmacur race in what era?"
        blocked, guardrail_resp = evaluate_all_guardrails(query)
        self.assertFalse(blocked, "Historical query should not be blocked by guardrails")
        self.assertIsNone(guardrail_resp)

        # Full API chat simulation
        msg = ChatMessage(
            query=query,
            context={"year": 1988, "round": 8, "session": "race", "selected": "SEN", "driver": "SEN"}
        )
        req = MagicMock()
        req.headers.get.return_value = "127.0.0.1"
        req.client.host = "127.0.0.1"

        chat_resp = asyncio.run(api_chat(msg, req))
        self.assertIsNotNone(chat_resp)
        self.assertEqual(chat_resp.get("tool"), "driver_career_history_lookup")
        self.assertIn("Michael Schumacher", chat_resp.get("text", ""))
        self.assertEqual(chat_resp.get("a2ui_card", {}).get("type"), "driver_career_card")

    # =========================================================================
    # SUITE 7: HEAD-TO-HEAD DRIVER COMPARISONS
    # =========================================================================
    def test_head_to_head_driver_comparisons(self):
        cases = [
            ("Compare Senna vs Prost", "Ayrton Senna", "Alain Prost", "3", "4"),
            ("Compare Lewis Hamilton and Michael Schumacher", "Michael Schumacher", "Lewis Hamilton", "7", "7"),
            ("Hamilton vs Verstappen stats", "Lewis Hamilton", "Max Verstappen", "105", "Max Verstappen")
        ]
        for query, d1_name, d2_name, d1_val, d2_val in cases:
            res = answer_race_engineer_query(query)
            self.assertIsNotNone(res)
            self.assertEqual(res.get("tool"), "driver_head_to_head_comparison")
            text = res.get("text", "")
            self.assertIn(d1_name, text)
            self.assertIn(d2_name, text)
            card = res.get("a2ui_card")
            self.assertIsNotNone(card)
            self.assertEqual(card.get("type"), "driver_comparison_card")

    # =========================================================================
    # SUITE 8: DRIVER CAREER MILESTONES & SPECIFIC METRICS
    # =========================================================================
    def test_driver_career_metric_queries(self):
        cases = [
            ("How many podiums does Fernando Alonso have?", "Fernando Alonso", "106 Podiums"),
            ("How many wins does Max Verstappen have?", "Max Verstappen", "Wins"),
            ("How many championships does Lewis Hamilton have?", "Lewis Hamilton", "7 Titles"),
        ]
        for query, expected_driver, expected_stat in cases:
            res = answer_race_engineer_query(query)
            self.assertIsNotNone(res)
            self.assertEqual(res.get("tool"), "driver_career_milestone_lookup")
            text = res.get("text", "")
            self.assertIn(expected_driver, text)
            self.assertIn(expected_stat, text)
            card = res.get("a2ui_card")
            self.assertIsNotNone(card)
            self.assertEqual(card.get("type"), "driver_performance_card")

    # =========================================================================
    # SUITE 9: ICONIC HISTORIC RACE TURNING POINTS & CONTROVERSIES
    # =========================================================================
    def test_iconic_historic_race_stories(self):
        cases = [
            ("What was the longest F1 race in history?", "2011 Canadian Grand Prix", "Jenson Button"),
            ("Why was Senna disqualified in 1989 Japan?", "1989 Japanese Grand Prix", "Casio Triangle"),
            ("Tell me about the 1976 Japanese Grand Prix", "1976 Japanese Grand Prix", "James Hunt"),
            ("What happened in 2008 Singapore?", "2008 Singapore Grand Prix", "Crashgate"),
        ]
        for query, expected_event, expected_keyword in cases:
            res = answer_race_engineer_query(query)
            self.assertIsNotNone(res)
            self.assertEqual(res.get("tool"), "historic_race_moment_lookup")
            text = res.get("text", "")
            self.assertIn(expected_keyword, text)
            card = res.get("a2ui_card")
            self.assertIsNotNone(card)
            self.assertEqual(card.get("type"), "historic_race_card")
            self.assertIn(expected_event, card.get("title", ""))

    # =========================================================================
    # SUITE 10: QUALIFYING, POLE POSITION & SPRINTS
    # =========================================================================
    def test_qualifying_and_pole_queries(self):
        res = answer_race_engineer_query("Who was on pole for 2024 British Grand Prix?")
        self.assertIsNotNone(res)
        self.assertEqual(res.get("tool"), "qualifying_pole_lookup")
        self.assertIn("George Russell", res.get("text", ""))
        self.assertEqual(res.get("a2ui_card", {}).get("type"), "qualifying_card")

    def test_sprint_race_queries(self):
        res = answer_race_engineer_query("Who won the 2024 Austrian GP Sprint?")
        self.assertIsNotNone(res)
        self.assertEqual(res.get("tool"), "sprint_classification_lookup")
        self.assertEqual(res.get("a2ui_card", {}).get("type"), "race_summary_card")

    # =========================================================================
    # SUITE 11: SPECIFIC FINISH POSITIONS & PODIUM CHECKS
    # =========================================================================
    def test_driver_podium_verification(self):
        res = answer_race_engineer_query("Did Fernando Alonso get a podium in the 2023 Bahrain Grand Prix?")
        self.assertIsNotNone(res)
        self.assertEqual(res.get("tool"), "driver_podium_verification")
        self.assertIn("Yes! Fernando Alonso", res.get("text", ""))
        self.assertIn("P3", res.get("text", ""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
