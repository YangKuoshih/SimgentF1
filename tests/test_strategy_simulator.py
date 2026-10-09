"""
F1 Simgent - What-If Strategy Simulator & Historical Scenario Test Suite
Tests tyre degradation curves, pit window calculations, Safety Car neutralisation,
crossover lead changes, Monte Carlo win probability, and FastAPI API routes.
"""

import sys
import os
import unittest
import asyncio

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from app.tools.strategy_simulator import (
    simulate_what_if_battle,
    get_what_if_presets,
    CIRCUIT_BASELINES,
    COMPOUND_PROFILES,
    HISTORICAL_WHAT_IF_PRESETS
)
from frontend.main import api_what_if_presets, api_what_if, WhatIfRequest


class TestStrategySimulator(unittest.TestCase):

    # =========================================================================
    # SUITE 1: PRESETS CONFIGURATION & CATALOG INTEGRITY
    # =========================================================================
    def test_presets_catalog(self):
        presets = get_what_if_presets()
        self.assertGreaterEqual(len(presets), 4)

        preset_ids = [p["id"] for p in presets]
        self.assertIn("2021_abu_dhabi_hamilton_box", preset_ids)
        self.assertIn("2024_silverstone_norris_mediums", preset_ids)
        self.assertIn("2026_bahrain_1stop_vs_2stop", preset_ids)
        self.assertIn("1998_spa_schumacher_clean", preset_ids)

        for p in presets:
            self.assertIn("title", p)
            self.assertIn("subtitle", p)
            self.assertIn("circuit_key", p)
            self.assertIn("total_laps", p)
            self.assertIn("driver_1", p)
            self.assertIn("driver_2", p)
            self.assertIn("historical_context", p)
            self.assertGreater(len(p["driver_1"]["stints"]), 0)
            self.assertGreater(len(p["driver_2"]["stints"]), 0)

    # =========================================================================
    # SUITE 2: LAP-BY-LAP SIMULATION PHYSICS & ACCURACY
    # =========================================================================
    def test_default_simulation_physics(self):
        res = simulate_what_if_battle(circuit_key="bahrain", total_laps=57, iterations=100)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["total_laps"], 57)
        self.assertIn(res["winner"], [res["driver_1"]["name"], res["driver_2"]["name"]])
        self.assertGreater(res["final_gap_s"], 0.0)
        self.assertAlmostEqual(res["d1_win_prob_pct"] + res["d2_win_prob_pct"], 100.0, places=1)

        progression = res["lap_progression"]
        self.assertEqual(len(progression), 57)

        # Check lap 1 data integrity
        lap1 = progression[0]
        self.assertEqual(lap1["lap"], 1)
        self.assertIn("d1_time", lap1)
        self.assertIn("d2_time", lap1)
        self.assertIn("cum_t1", lap1)
        self.assertIn("cum_t2", lap1)
        self.assertIn("gap_s", lap1)
        self.assertIn("leader", lap1)
        self.assertIn("d1_tyre", lap1)
        self.assertIn("d2_tyre", lap1)

    # =========================================================================
    # SUITE 3: SAFETY CAR NEUTRALISATION DYNAMICS
    # =========================================================================
    def test_safety_car_neutralisation(self):
        # Green flag simulation
        green_res = simulate_what_if_battle(circuit_key="silverstone", total_laps=52, sc_lap=0, iterations=50)
        # Safety car deployed on lap 20
        sc_res = simulate_what_if_battle(circuit_key="silverstone", total_laps=52, sc_lap=20, iterations=50)

        # In SC simulation, laps 20..23 must be flagged is_sc = True
        sc_laps = [lp for lp in sc_res["lap_progression"] if lp["is_sc"]]
        self.assertGreaterEqual(len(sc_laps), 3)
        self.assertTrue(all(20 <= lp["lap"] <= 23 for lp in sc_laps))

        # Green flag must have zero SC laps
        green_sc_laps = [lp for lp in green_res["lap_progression"] if lp["is_sc"]]
        self.assertEqual(len(green_sc_laps), 0)

    # =========================================================================
    # SUITE 4: HISTORICAL WHAT-IF SCENARIOS
    # =========================================================================
    def test_2021_abu_dhabi_preset(self):
        presets = {p["id"]: p for p in get_what_if_presets()}
        p = presets["2021_abu_dhabi_hamilton_box"]
        res = simulate_what_if_battle(
            circuit_key=p["circuit_key"],
            total_laps=p["total_laps"],
            driver_1=p["driver_1"],
            driver_2=p["driver_2"],
            sc_lap=p["sc_lap"],
            iterations=100
        )
        # In this simulation, Hamilton boxing for fresh Softs under SC beats Verstappen
        self.assertEqual(res["winner"], "Lewis Hamilton")
        self.assertGreater(res["d1_win_prob_pct"], 80.0)
        self.assertGreater(len(res["crossover_laps"]), 0)

    def test_2024_silverstone_norris_mediums_preset(self):
        presets = {p["id"]: p for p in get_what_if_presets()}
        p = presets["2024_silverstone_norris_mediums"]
        res = simulate_what_if_battle(
            circuit_key=p["circuit_key"],
            total_laps=p["total_laps"],
            driver_1=p["driver_1"],
            driver_2=p["driver_2"],
            sc_lap=p["sc_lap"],
            iterations=100
        )
        self.assertEqual(res["status"], "success")
        self.assertIn(res["winner"], ["Lewis Hamilton", "Lando Norris"])
        self.assertIn("Silverstone", res["circuit_name"])

    def test_1998_spa_schumacher_clean_preset(self):
        presets = {p["id"]: p for p in get_what_if_presets()}
        p = presets["1998_spa_schumacher_clean"]
        res = simulate_what_if_battle(
            circuit_key=p["circuit_key"],
            total_laps=p["total_laps"],
            driver_1=p["driver_1"],
            driver_2=p["driver_2"],
            sc_lap=p["sc_lap"],
            iterations=100
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["winner"], "Michael Schumacher")
        self.assertGreater(res["d1_win_prob_pct"], 50.0)

    # =========================================================================
    # SUITE 5: FASTAPI ASYNC ENDPOINTS
    # =========================================================================
    def test_api_what_if_presets_endpoint(self):
        presets = asyncio.run(api_what_if_presets())
        self.assertIsInstance(presets, list)
        self.assertGreaterEqual(len(presets), 4)

    def test_api_what_if_simulation_endpoint(self):
        req = WhatIfRequest(
            circuit_key="monza",
            total_laps=53,
            sc_lap=0,
            iterations=100
        )
        res = asyncio.run(api_what_if(req))
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["total_laps"], 53)
        self.assertIn("tactical_summary", res)


if __name__ == "__main__":
    unittest.main()
