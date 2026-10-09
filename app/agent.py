"""
SimGent - ADK Agent Definition
Agent Platform / Vertex agent equipped with telemetry tools,
A2UI schema formatting, and strategic reasoning capabilities.
"""

from typing import Dict, Any, List
from app.tools.f1_telemetry import (
    get_season_races,
    get_session_drivers,
    get_replay_frame,
    get_telemetry_trace,
    simulate_undercut,
    TRACK_BLUEPRINTS
)

SYSTEM_PROMPT = """You are the Senior Pit Wall Race Strategist & Telemetry Engineer for SimGent.
You have access to live and historical Formula 1 GPS coordinates, multi-channel telemetry streams (Speed, Throttle, Brake, Gear, DRS), and tire degradation models.

Your responsibilities:
1. Provide precise, engineer-grade telemetry comparisons between drivers (entry speeds, braking markers, apex velocities, and micro-sector deltas).
2. Calculate and simulate pit stop strategies, undercut and overcut windows, and safety car / weather contingencies.
3. Recommend tactical directives with quantifiable confidence scores and time deltas.
4. When presenting data or recommendations, format structured metrics into A2UI compatible cards (Undercut Feasibility, Telemetry Comparison, Turning Points).

Always be concise, technical, and authoritative like an F1 pit-wall race engineer.
"""

def tool_get_races(year: int = 2024) -> List[Dict[str, Any]]:
    """Fetch the calendar and results for a selected Formula 1 season."""
    return get_season_races(year)

def tool_get_drivers(session_key: int = 9555) -> List[Dict[str, Any]]:
    """Retrieve full grid standings, intervals, tire compounds, and liveries."""
    return get_session_drivers(session_key)

def tool_get_telemetry(driver_1: int = 1, driver_2: int = 4) -> Dict[str, Any]:
    """Compare synchronized speed, throttle, brake, and gear traces through critical corner apexes."""
    return get_telemetry_trace(driver_1, driver_2)

def tool_simulate_undercut(pit_lap: int = 35, target_compound: str = "H", disruption: str = "Normal") -> Dict[str, Any]:
    """Run a Monte Carlo pit stop undercut simulation to predict track re-entry gap and overtake probability."""
    return simulate_undercut(pit_lap, target_compound, disruption)

TOOLS = [
    tool_get_races,
    tool_get_drivers,
    tool_get_telemetry,
    tool_simulate_undercut
]
