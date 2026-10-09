"""
F1 Simgent - What-If Strategy Simulator & Historical Scenario Engine
Simulates full-distance race battles between different drivers, tyre stint strategies,
pit windows, tyre degradation curves, and Safety Car neutralisations.
Calculates lap-by-lap pace deltas, crossover overtake laps, finish margins, and Monte Carlo win probabilities.
"""

import math
import random
from typing import Any, Dict, List, Optional, Tuple


# Baseline circuit parameters
CIRCUIT_BASELINES: Dict[str, Dict[str, Any]] = {
    "default": {"length_km": 5.4, "total_laps": 57, "base_lap_s": 91.5, "pit_loss_s": 21.0, "sc_pit_loss_s": 11.5},
    "bahrain": {"length_km": 5.412, "total_laps": 57, "base_lap_s": 93.0, "pit_loss_s": 23.0, "sc_pit_loss_s": 12.0},
    "monaco": {"length_km": 3.337, "total_laps": 78, "base_lap_s": 74.5, "pit_loss_s": 21.0, "sc_pit_loss_s": 11.0},
    "silverstone": {"length_km": 5.891, "total_laps": 52, "base_lap_s": 88.5, "pit_loss_s": 19.8, "sc_pit_loss_s": 10.2},
    "spa": {"length_km": 7.004, "total_laps": 44, "base_lap_s": 106.0, "pit_loss_s": 22.5, "sc_pit_loss_s": 12.0},
    "monza": {"length_km": 5.793, "total_laps": 53, "base_lap_s": 82.0, "pit_loss_s": 24.2, "sc_pit_loss_s": 13.0},
    "interlagos": {"length_km": 4.309, "total_laps": 71, "base_lap_s": 71.5, "pit_loss_s": 20.5, "sc_pit_loss_s": 10.8},
    "yas_marina": {"length_km": 5.281, "total_laps": 58, "base_lap_s": 86.5, "pit_loss_s": 21.5, "sc_pit_loss_s": 11.2},
    "villeneuve": {"length_km": 4.361, "total_laps": 70, "base_lap_s": 73.5, "pit_loss_s": 19.5, "sc_pit_loss_s": 10.5},
    "suzuka": {"length_km": 5.807, "total_laps": 53, "base_lap_s": 91.0, "pit_loss_s": 22.8, "sc_pit_loss_s": 11.8},
    "albert_park": {"length_km": 5.278, "total_laps": 58, "base_lap_s": 79.5, "pit_loss_s": 20.0, "sc_pit_loss_s": 10.5},
    "marina_bay": {"length_km": 4.940, "total_laps": 62, "base_lap_s": 96.0, "pit_loss_s": 28.5, "sc_pit_loss_s": 14.5},
}

# Compound physics profiles: initial pace delta (s vs hard) and degradation per lap (s/lap)
COMPOUND_PROFILES = {
    "S": {"name": "Soft", "pace_delta": -1.15, "deg_rate": 0.115, "color": "#E10600"},
    "M": {"name": "Medium", "pace_delta": -0.65, "deg_rate": 0.065, "color": "#FFD166"},
    "H": {"name": "Hard", "pace_delta": 0.0, "deg_rate": 0.038, "color": "#FFFFFF"},
    "I": {"name": "Intermediate", "pace_delta": 4.5, "deg_rate": 0.080, "color": "#10B981"},
    "W": {"name": "Wet", "pace_delta": 9.0, "deg_rate": 0.050, "color": "#3B82F6"},
}

HISTORICAL_WHAT_IF_PRESETS = [
    {
        "id": "2021_abu_dhabi_hamilton_box",
        "title": "2021 Abu Dhabi GP: What if Hamilton Pitted for Softs?",
        "subtitle": "Lap 53 Latifi Safety Car — Mercedes covers Red Bull by boxing Hamilton",
        "circuit_key": "yas_marina",
        "circuit_name": "Yas Marina Circuit",
        "total_laps": 58,
        "sc_lap": 53,
        "driver_1": {
            "name": "Lewis Hamilton",
            "team": "Mercedes",
            "color": "#27F4D2",
            "starting_grid": 2,
            "stints": [
                {"compound": "M", "start_lap": 1, "end_lap": 14},
                {"compound": "H", "start_lap": 15, "end_lap": 53},
                {"compound": "S", "start_lap": 54, "end_lap": 58}
            ],
            "description": "Boxes for fresh Softs under the Lap 53 Safety Car"
        },
        "driver_2": {
            "name": "Max Verstappen",
            "team": "Red Bull Racing",
            "color": "#1E41FF",
            "starting_grid": 1,
            "stints": [
                {"compound": "S", "start_lap": 1, "end_lap": 13},
                {"compound": "H", "start_lap": 14, "end_lap": 36},
                {"compound": "H", "start_lap": 37, "end_lap": 53},
                {"compound": "S", "start_lap": 54, "end_lap": 58}
            ],
            "description": "Boxes for fresh Softs on Lap 53 (as in real race)"
        },
        "historical_context": (
            "In reality, Mercedes kept Hamilton on 40-lap old Hard tyres to maintain track position, while Verstappen pitted for fresh Softs "
            "and passed him on the final lap. In this simulation, Hamilton pits for Softs under the Safety Car, re-entering right ahead or alongside Verstappen on equal tyre rubber."
        )
    },
    {
        "id": "2024_silverstone_norris_mediums",
        "title": "2024 British GP: What if McLaren Fitted Norris with Mediums?",
        "subtitle": "Final stop tyre selection — fresh Mediums vs Hamilton's Softs",
        "circuit_key": "silverstone",
        "circuit_name": "Silverstone Circuit",
        "total_laps": 52,
        "sc_lap": 0,
        "driver_1": {
            "name": "Lando Norris",
            "team": "McLaren",
            "color": "#FF8000",
            "starting_grid": 3,
            "stints": [
                {"compound": "M", "start_lap": 1, "end_lap": 19},
                {"compound": "I", "start_lap": 20, "end_lap": 39},
                {"compound": "M", "start_lap": 40, "end_lap": 52}
            ],
            "description": "Fits brand-new Mediums instead of used Softs on Lap 40"
        },
        "driver_2": {
            "name": "Lewis Hamilton",
            "team": "Mercedes",
            "color": "#27F4D2",
            "starting_grid": 2,
            "stints": [
                {"compound": "M", "start_lap": 1, "end_lap": 18},
                {"compound": "I", "start_lap": 19, "end_lap": 38},
                {"compound": "S", "start_lap": 39, "end_lap": 52}
            ],
            "description": "Boxes on Lap 38 for Softs (Hamilton's winning strategy)"
        },
        "historical_context": (
            "McLaren chose used Softs for Norris at the final crossover to dry tyres, which suffered high degradation. "
            "McLaren had a pristine set of fresh Mediums available. This simulation tests if fresh Mediums would have hunted down Hamilton."
        )
    },
    {
        "id": "2026_bahrain_1stop_vs_2stop",
        "title": "2026 Bahrain GP: 1-Stop Management vs 2-Stop Attack",
        "subtitle": "Russell 1-Stop endurance vs Verstappen 2-Stop aggressive pursuit",
        "circuit_key": "bahrain",
        "circuit_name": "Bahrain International Circuit",
        "total_laps": 57,
        "sc_lap": 32,
        "driver_1": {
            "name": "Max Verstappen",
            "team": "Red Bull Racing",
            "color": "#1E41FF",
            "starting_grid": 1,
            "stints": [
                {"compound": "S", "start_lap": 1, "end_lap": 16},
                {"compound": "M", "start_lap": 17, "end_lap": 36},
                {"compound": "S", "start_lap": 37, "end_lap": 57}
            ],
            "description": "Aggressive 2-stop sprint with 2 Soft tyre stints"
        },
        "driver_2": {
            "name": "George Russell",
            "team": "Mercedes",
            "color": "#27F4D2",
            "starting_grid": 2,
            "stints": [
                {"compound": "M", "start_lap": 1, "end_lap": 26},
                {"compound": "H", "start_lap": 27, "end_lap": 57}
            ],
            "description": "Conserving 1-stop strategy holding track position"
        },
        "historical_context": (
            "Sakhir is notorious for high abrasive tyre degradation. Does a 2-stop attacker with fresh rubber overcome the +23s pit loss delta "
            "against a 1-stopping leader?"
        )
    },
    {
        "id": "1998_spa_schumacher_clean",
        "title": "1998 Belgian GP: What if Schumacher Stayed Patient?",
        "subtitle": "Torrential rain at Spa — Schumacher avoids Coulthard collision",
        "circuit_key": "spa",
        "circuit_name": "Circuit de Spa-Francorchamps",
        "total_laps": 44,
        "sc_lap": 0,
        "driver_1": {
            "name": "Michael Schumacher",
            "team": "Ferrari",
            "color": "#E10600",
            "starting_grid": 4,
            "stints": [
                {"compound": "W", "start_lap": 1, "end_lap": 26},
                {"compound": "W", "start_lap": 27, "end_lap": 44}
            ],
            "description": "Waits behind Coulthard in spray, passes on straight on Lap 26"
        },
        "driver_2": {
            "name": "Damon Hill",
            "team": "Jordan-Mugen",
            "color": "#FFD100",
            "starting_grid": 3,
            "stints": [
                {"compound": "W", "start_lap": 1, "end_lap": 44}
            ],
            "description": "Steady wet weather pace for Jordan (actual race winner)"
        },
        "historical_context": (
            "Schumacher led Hill by over 40 seconds before unsighted rear-ending Coulthard on Lap 25. "
            "If he avoids the incident, Ferrari cruises to a dominant wet-weather victory."
        )
    }
]


def get_what_if_presets() -> List[Dict[str, Any]]:
    return HISTORICAL_WHAT_IF_PRESETS


def simulate_what_if_battle(
    circuit_key: str = "bahrain",
    total_laps: Optional[int] = None,
    driver_1: Optional[Dict[str, Any]] = None,
    driver_2: Optional[Dict[str, Any]] = None,
    sc_lap: int = 0,
    iterations: int = 200
) -> Dict[str, Any]:
    """
    Executes a lap-by-lap simulation between Driver 1 and Driver 2.
    Computes lap-by-lap running gap, crossover passes, finishing delta, and Monte Carlo probability.
    """
    base_info = CIRCUIT_BASELINES.get(circuit_key.lower()) or CIRCUIT_BASELINES["default"]
    laps_total = total_laps or base_info["total_laps"]
    base_lap_s = base_info["base_lap_s"]
    pit_loss = base_info["pit_loss_s"]
    sc_loss = base_info["sc_pit_loss_s"]

    # Fallback default drivers if not provided
    d1 = driver_1 or {
        "name": "Driver 1 (Attacker)",
        "team": "Red Bull Racing",
        "color": "#1E41FF",
        "starting_grid": 1,
        "stints": [
            {"compound": "S", "start_lap": 1, "end_lap": 20},
            {"compound": "H", "start_lap": 21, "end_lap": laps_total}
        ]
    }
    d2 = driver_2 or {
        "name": "Driver 2 (Rival)",
        "team": "Mercedes",
        "color": "#27F4D2",
        "starting_grid": 2,
        "stints": [
            {"compound": "M", "start_lap": 1, "end_lap": 26},
            {"compound": "H", "start_lap": 27, "end_lap": laps_total}
        ]
    }

    d1_stints = d1.get("stints", [])
    d2_stints = d2.get("stints", [])

    def get_stint_compound(stints: List[Dict[str, Any]], lap: int) -> Tuple[str, int]:
        for idx, s in enumerate(stints):
            s_start = s.get("start_lap", 1)
            s_end = s.get("end_lap", laps_total)
            if s_start <= lap <= s_end:
                tyre_age = lap - s_start
                return s.get("compound", "M").upper(), tyre_age
        return "H", 10

    def is_pit_lap(stints: List[Dict[str, Any]], lap: int) -> bool:
        for idx, s in enumerate(stints):
            if idx > 0 and s.get("start_lap") == lap:
                return True
        return False

    # 1. Deterministic Baseline Lap-by-Lap Calculation
    lap_progression = []
    cum_t1 = 0.0
    cum_t2 = 0.0
    # Grid offset: P1 starts at 0.0s, P2 starts +0.25s, P3 +0.50s
    grid1 = d1.get("starting_grid", 1)
    grid2 = d2.get("starting_grid", 2)
    if grid1 > grid2:
        cum_t1 += (grid1 - grid2) * 0.25
    elif grid2 > grid1:
        cum_t2 += (grid2 - grid1) * 0.25

    crossover_laps = []
    prev_leader = None

    for lap in range(1, laps_total + 1):
        # Fuel burn-off advantage per lap
        fuel_gain = (lap - 1) * 0.035

        # Driver 1
        comp1, age1 = get_stint_compound(d1_stints, lap)
        c_prof1 = COMPOUND_PROFILES.get(comp1, COMPOUND_PROFILES["M"])
        t1_lap = base_lap_s + c_prof1["pace_delta"] + (age1 * c_prof1["deg_rate"]) - fuel_gain

        # Driver 2
        comp2, age2 = get_stint_compound(d2_stints, lap)
        c_prof2 = COMPOUND_PROFILES.get(comp2, COMPOUND_PROFILES["M"])
        t2_lap = base_lap_s + c_prof2["pace_delta"] + (age2 * c_prof2["deg_rate"]) - fuel_gain

        # Pit stop addition
        is_sc_active = (sc_lap > 0 and sc_lap <= lap <= sc_lap + 3)
        curr_pit_loss = sc_loss if is_sc_active else pit_loss

        if is_pit_lap(d1_stints, lap):
            t1_lap += curr_pit_loss
        if is_pit_lap(d2_stints, lap):
            t2_lap += curr_pit_loss

        # Under Safety Car, delta lap times are clamped
        if is_sc_active:
            t1_lap = max(t1_lap, base_lap_s * 1.38)
            t2_lap = max(t2_lap, base_lap_s * 1.38)

        cum_t1 += t1_lap
        cum_t2 += t2_lap

        # Gap calculation: Driver 1 relative to Driver 2 (negative = Driver 1 ahead)
        gap_s = round(cum_t1 - cum_t2, 2)
        leader = d1["name"] if gap_s < 0 else d2["name"]

        if prev_leader and leader != prev_leader:
            crossover_laps.append({"lap": lap, "new_leader": leader, "margin_s": abs(gap_s)})
        prev_leader = leader

        lap_progression.append({
            "lap": lap,
            "d1_time": round(t1_lap, 3),
            "d2_time": round(t2_lap, 3),
            "cum_t1": round(cum_t1, 2),
            "cum_t2": round(cum_t2, 2),
            "gap_s": abs(gap_s),
            "leader": leader,
            "d1_lead": (cum_t1 <= cum_t2),
            "d1_tyre": comp1,
            "d2_tyre": comp2,
            "is_sc": is_sc_active
        })

    # Final margin
    final_gap = round(abs(cum_t1 - cum_t2), 2)
    overall_winner = d1["name"] if cum_t1 < cum_t2 else d2["name"]
    runner_up = d2["name"] if overall_winner == d1["name"] else d1["name"]

    # 2. Monte Carlo Win Probability Estimation (Simulating 200 race runs with stochastic noise)
    d1_wins = 0
    d2_wins = 0
    random.seed(42)  # repeatable seed for consistent client results

    for _ in range(iterations):
        sim_t1 = 0.0
        sim_t2 = 0.0
        # Stochastic variance in pit stop efficiency and tyre deg
        p_stop_var1 = random.gauss(0.0, 0.35)
        p_stop_var2 = random.gauss(0.0, 0.35)
        deg_var1 = random.gauss(1.0, 0.06)
        deg_var2 = random.gauss(1.0, 0.06)

        for lap in range(1, laps_total + 1):
            fuel_gain = (lap - 1) * 0.035
            comp1, age1 = get_stint_compound(d1_stints, lap)
            c1 = COMPOUND_PROFILES.get(comp1, COMPOUND_PROFILES["M"])
            t1 = base_lap_s + c1["pace_delta"] + (age1 * c1["deg_rate"] * deg_var1) - fuel_gain + random.gauss(0.0, 0.12)

            comp2, age2 = get_stint_compound(d2_stints, lap)
            c2 = COMPOUND_PROFILES.get(comp2, COMPOUND_PROFILES["M"])
            t2 = base_lap_s + c2["pace_delta"] + (age2 * c2["deg_rate"] * deg_var2) - fuel_gain + random.gauss(0.0, 0.12)

            is_sc = (sc_lap > 0 and sc_lap <= lap <= sc_lap + 3)
            loss = sc_loss if is_sc else pit_loss

            if is_pit_lap(d1_stints, lap):
                t1 += (loss + p_stop_var1)
            if is_pit_lap(d2_stints, lap):
                t2 += (loss + p_stop_var2)

            sim_t1 += t1
            sim_t2 += t2

        if sim_t1 < sim_t2:
            d1_wins += 1
        else:
            d2_wins += 1

    d1_prob = round((d1_wins / iterations) * 100, 1)
    d2_prob = round(100.0 - d1_prob, 1)

    # Narrative Tactical Breakdown
    crossover_text = ""
    if crossover_laps:
        cl = crossover_laps[-1]
        crossover_text = f"Key turning point on **Lap {cl['lap']}**, where **{cl['new_leader']}** made the decisive crossover overtake."
    else:
        crossover_text = f"**{overall_winner}** maintained continuous track command throughout all {laps_total} laps."

    sc_text = f"under the **Lap {sc_lap} Safety Car** window" if sc_lap > 0 else "under green-flag running"
    tactical_summary = (
        f"**What-If Simulation Verdict: {overall_winner} Takes Victory (+{final_gap:.1f}s margin)**\n\n"
        f"• **Predicted Winner**: **{overall_winner}** ({d1_prob if overall_winner == d1['name'] else d2_prob}% Monte Carlo Win Probability)\n"
        f"• **Winning Margin**: **+{final_gap:.2f} seconds** after {laps_total} laps {sc_text}.\n"
        f"• **Crossover Dynamics**: {crossover_text}\n"
        f"• **Strategic Delta**: {d1['name']} ({', '.join(s['compound'] for s in d1_stints)}) vs {d2['name']} ({', '.join(s['compound'] for s in d2_stints)})."
    )

    return {
        "status": "success",
        "circuit": base_info,
        "circuit_name": base_info.get("name", circuit_key.title()),
        "total_laps": laps_total,
        "sc_lap": sc_lap,
        "driver_1": d1,
        "driver_2": d2,
        "winner": overall_winner,
        "runner_up": runner_up,
        "final_gap_s": final_gap,
        "d1_win_prob_pct": d1_prob,
        "d2_win_prob_pct": d2_prob,
        "crossover_laps": crossover_laps,
        "tactical_summary": tactical_summary,
        "lap_progression": lap_progression
    }
