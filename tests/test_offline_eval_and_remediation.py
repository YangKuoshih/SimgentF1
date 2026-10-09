import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
"""
Automated Test Suite for Offline Data Evaluation & Autonomous Remediation Agent
Compatible with python -m unittest discover tests.

Verifies all 7 pillars of data integrity:
1. Static cache integrity
2. Timing tower monotonicity & lap length
3. Starting grid uniqueness and FIA alignment
4. Replay physics & normalized track coordinates
5. Circuit closed loop geometry & sectors
6. Driver registry styling & fields
7. Pit Wall Agent factuality & accuracy against ground truth
"""

import json
import os
import shutil
import tempfile
import unittest

from app.tools.offline_eval import OfflineDataEval
from app.tools.remediation_agent import RemediationAgent
from app.tools.race_agent import answer_race_engineer_query
from app.tools.agent_memory import memory_manager


class TestOfflineEvalAndRemediation(unittest.TestCase):

    def test_all_7_eval_pillars_pass(self):
        """Validates that all 7 pillars pass with 100% integrity score."""
        eval_suite = OfflineDataEval(offline=True, remediate_on_failure=False)
        report = eval_suite.run_full_eval(year=2026, round_num=16, circuit_id="bahrain")

        self.assertEqual(report["status"], "PASSED (100% INTEGRITY)", f"Eval failed: {report.get('discrepancies')}")
        self.assertEqual(report["score_pct"], 100.0)
        self.assertGreaterEqual(report["total_checks"], 140)
        self.assertEqual(report["discrepancies_count"], 0)

        pillars = report["pillars"]
        self.assertTrue(pillars["static_cache"]["passed"])
        self.assertTrue(pillars["timing_tower"]["passed"])
        self.assertTrue(pillars["starting_grids"]["passed"])
        self.assertTrue(pillars["replay_physics"]["passed"])
        self.assertTrue(pillars["circuit_geometry"]["passed"])
        self.assertTrue(pillars["driver_registry"]["passed"])
        self.assertTrue(pillars["pit_wall_agent"]["passed"])

    def test_pit_wall_agent_starting_grid_accuracy(self):
        """Asserts Pit Wall Agent answers starting grid queries accurately without hallucination."""
        # 1. Russell starting grid inquiry
        r1 = answer_race_engineer_query(
            "Where did George Russell start in the 2026 Bahrain Grand Prix?",
            {"year": 2026, "round": 16}
        )
        text1 = r1["text"]
        self.assertIn("P7", text1, f"Russell starting position was not identified as P7: {text1}")
        self.assertNotIn("started P20", text1, f"Russell incorrectly reported starting P20: {text1}")
        self.assertIsNotNone(r1.get("a2ui_card"))
        self.assertEqual(r1["a2ui_card"]["type"], "starting_grid_card")

        # 2. Antonelli P3 starting grid inquiry
        r2 = answer_race_engineer_query(
            "Who started P3 on the grid in Bahrain 2026?",
            {"year": 2026, "round": 16}
        )
        text2 = r2["text"]
        self.assertTrue("Antonelli" in text2 or "ANT" in text2)
        self.assertIn("P3", text2)

        # 3. Undercut tactical strategy explanation
        r3 = answer_race_engineer_query("What is an undercut strategy in F1?")
        text3 = r3["text"]
        self.assertIn("undercut", text3.lower())
        self.assertTrue("fresh" in text3.lower() or "tyre" in text3.lower() or "pit" in text3.lower())

    def test_remediation_heals_simulated_starting_grid_corruption(self):
        """
        Simulates a data corruption where starting grid has duplicate slots,
        and tests that RemediationAgent detects and restores authentic unique grids.
        """
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        target_res = os.path.join(root, "data", "cache", "jolpica", "2026_16_results.json")

        with tempfile.TemporaryDirectory() as tmp_dir:
            backup_res = os.path.join(tmp_dir, "2026_16_results_backup.json")
            shutil.copyfile(target_res, backup_res)

            try:
                # Corrupt the cache: give driver 0 and driver 1 duplicate grid: 3
                with open(target_res, "r") as f:
                    data = json.load(f)
                results = data["MRData"]["RaceTable"]["Races"][0]["Results"]
                results[0]["grid"] = "3"
                results[1]["grid"] = "3"
                with open(target_res, "w") as f:
                    json.dump(data, f, indent=2)

                # Eval without remediation should flag the discrepancy
                eval_suite_strict = OfflineDataEval(offline=True, remediate_on_failure=False)
                rep_fail = eval_suite_strict.eval_starting_grids(2026, 16)
                self.assertFalse(rep_fail["passed"])
                self.assertTrue(any("Duplicate starting grid slots" in d for d in rep_fail["discrepancies"]))

                # Run RemediationAgent
                remediator = RemediationAgent(offline=True)
                healed = remediator.remediate_starting_grid(2026, 16)
                self.assertTrue(healed)

                # Re-eval after remediation should pass 100%
                rep_pass = eval_suite_strict.eval_starting_grids(2026, 16)
                self.assertTrue(rep_pass["passed"])
                self.assertEqual(len(rep_pass["discrepancies"]), 0)
            finally:
                # Restore original authentic cache
                shutil.copyfile(backup_res, target_res)

    def test_remediation_heals_pit_wall_memory(self):
        """Tests injecting verified facts into AgentMemory for instant 0-cost retrieval.

        Writes go to the private runtime memory file, so the original file is restored
        afterwards to keep test fixtures out of the live app's memory.
        """
        from app.tools.agent_memory import MEMORY_FILE
        with open(MEMORY_FILE, encoding="utf-8") as fh:
            original_memory = fh.read()
        try:
            remediator = RemediationAgent(offline=True)
            test_q = "What is the secret test telemetry metric for Bahrain 2026?"
            test_ans = "The secret telemetry metric is ApexSpeed_312kmh."

            ok = remediator.remediate_pit_wall_memory(test_q, test_ans)
            self.assertTrue(ok)

            retrieved = memory_manager.retrieve(test_q)
            self.assertIsNotNone(retrieved)
            self.assertIn("ApexSpeed_312kmh", retrieved["text"])
        finally:
            with open(MEMORY_FILE, "w", encoding="utf-8") as fh:
                fh.write(original_memory)


if __name__ == "__main__":
    unittest.main()
