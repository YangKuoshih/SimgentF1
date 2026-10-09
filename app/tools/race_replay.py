"""
Race replay builder.

Turns REAL Jolpica data (classification + lap-by-lap timing + pit stops) and REAL
circuit geometry (bacinger/f1-circuits GeoJSON, MIT) into a compact replay model the
browser can animate locally (no per-frame server polling).

Each driver gets `cum`: cumulative race time (s) at the end of every lap they completed.
The client derives position-on-track, running order, gaps, pit laps and retirements
from that — so the lap counter and the cars are always in sync.
"""

import datetime
import json
import math
import os
import re
import statistics
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from app.tools import jolpica_sync as J
from app.tools.f1_telemetry import TRACK_BLUEPRINTS

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GEOJSON = os.path.join(ROOT, "data", "f1-circuits.geojson")

# Jolpica circuitId -> bacinger GeoJSON feature id
CIRCUIT_MAP = {
    "albert_park": "au-1953", "bahrain": "bh-2002", "shanghai": "cn-2004", "catalunya": "es-1991",
    "monaco": "mc-1929", "villeneuve": "ca-1978", "ricard": "fr-1969", "red_bull_ring": "at-1969",
    "silverstone": "gb-1948", "hockenheimring": "de-1932", "hungaroring": "hu-1986", "spa": "be-1925",
    "monza": "it-1922", "marina_bay": "sg-2008", "sochi": "ru-2014", "suzuka": "jp-1962",
    "americas": "us-2012", "rodriguez": "mx-1962", "interlagos": "br-1940", "yas_marina": "ae-2009",
    "imola": "it-1953", "nurburgring": "de-1927", "portimao": "pt-2008", "mugello": "it-1914",
    "sepang": "my-1999", "istanbul": "tr-2005", "zandvoort": "nl-1948", "magny_cours": "fr-1960",
    "estoril": "pt-1972", "jacarepagua": "br-1977", "jeddah": "sa-2021", "miami": "us-2022",
    "losail": "qa-2004", "madring": "es-2026", "baku": "az-2016", "vegas": "us-2023",
    "indianapolis": "us-1909", "galvez": "ar-1952", "kyalami": "za-1961", "watkins_glen": "us-1956",
}


# Known event relocations NOT yet corrected upstream in Jolpica/Ergast.
# The 2026 "Bahrain Grand Prix" (round 16) was physically run at Sepang
# International Circuit, Malaysia (relocated from Bahrain due to the 2026 Iran
# war). Jolpica updated the date/round but still lists the Sakhir circuit, so we
# reconcile the real venue here while keeping the official event name. Keyed by
# (year, round); remove an entry if upstream ever corrects it.
EVENT_RELOCATIONS = {
    (2026, 16): {
        "circuit_id": "sepang",
        "circuit_name": "Sepang International Circuit",
        "locality": "Sepang",
        "country": "Malaysia",
        "note": ("Relocated from the Bahrain International Circuit in Sakhir (originally scheduled for "
                 "12 April) after the outbreak of the 2026 Iran war, and run at Sepang under the Bahrain name."),
    },
}
# Event name semantic matching -> Canonical circuit ID
CANONICAL_CIRCUIT_BY_EVENT = {
    "bahrain": "bahrain",
    "sakhir": "bahrain",
    "saudi": "jeddah",
    "jeddah": "jeddah",
    "australian": "albert_park",
    "melbourne": "albert_park",
    "albert_park": "albert_park",
    "japanese": "suzuka",
    "suzuka": "suzuka",
    "chinese": "shanghai",
    "shanghai": "shanghai",
    "miami": "miami",
    "emilia": "imola",
    "imola": "imola",
    "monaco": "monaco",
    "canadian": "villeneuve",
    "montreal": "villeneuve",
    "villeneuve": "villeneuve",
    "spanish": "catalunya",
    "catalunya": "catalunya",
    "barcelona": "catalunya",
    "austrian": "red_bull_ring",
    "spielberg": "red_bull_ring",
    "red_bull_ring": "red_bull_ring",
    "british": "silverstone",
    "silverstone": "silverstone",
    "hungarian": "hungaroring",
    "hungaroring": "hungaroring",
    "belgian": "spa",
    "spa": "spa",
    "dutch": "zandvoort",
    "zandvoort": "zandvoort",
    "italian": "monza",
    "monza": "monza",
    "azerbaijan": "baku",
    "baku": "baku",
    "singapore": "marina_bay",
    "marina_bay": "marina_bay",
    "united states": "americas",
    "cota": "americas",
    "austin": "americas",
    "americas": "americas",
    "mexico": "rodriguez",
    "mexican": "rodriguez",
    "rodriguez": "rodriguez",
    "brazilian": "interlagos",
    "sao paulo": "interlagos",
    "interlagos": "interlagos",
    "las vegas": "vegas",
    "vegas": "vegas",
    "qatar": "losail",
    "losail": "losail",
    "lusail": "losail",
    "abu dhabi": "yas_marina",
    "yas_marina": "yas_marina",
    "portuguese": "portimao",
    "portimao": "portimao",
    "turkish": "istanbul",
    "istanbul": "istanbul",
    "malaysian": "sepang",
    "sepang": "sepang",
    "madrid": "madring",
    "madring": "madring",
}


def resolve_canonical_circuit(
    year: int,
    rnd: int,
    raw_circuit_id: Optional[str] = None,
    race_name: Optional[str] = None,
    circuit_override: Optional[str] = None,
) -> str:
    """
    Dynamically determines the canonical circuit ID for a race weekend session.
    Uses shared weekend settings across Race, Qualifying, and Sprint sessions,
    reconciling any upstream API discrepancies or cache anomalies.
    """
    # 1. Explicit valid circuit override takes highest priority
    if circuit_override and circuit_override.strip():
        co = circuit_override.strip().lower()
        if co in CIRCUIT_MAP or co in TRACK_BLUEPRINTS:
            return co

    # 1.5 Known event relocations not yet corrected upstream (e.g. 2026 Bahrain GP run at Sepang)
    if (year, rnd) in EVENT_RELOCATIONS:
        return EVENT_RELOCATIONS[(year, rnd)]["circuit_id"]

    # 2. Valid raw_circuit_id directly from official session or schedule
    if raw_circuit_id and raw_circuit_id.strip():
        rc = raw_circuit_id.strip().lower()
        if rc in CIRCUIT_MAP or rc in TRACK_BLUEPRINTS:
            return rc
        if rc in CANONICAL_CIRCUIT_BY_EVENT:
            return CANONICAL_CIRCUIT_BY_EVENT[rc]

    # 3. Weekend consistency check from main Grand Prix race results
    try:
        main_res = J.results(year, rnd, net=False)
        if main_res and main_res.get("Circuit", {}).get("circuitId"):
            main_cid = main_res["Circuit"]["circuitId"].strip().lower()
            if main_cid in CIRCUIT_MAP or main_cid in TRACK_BLUEPRINTS:
                return main_cid
            if main_cid in CANONICAL_CIRCUIT_BY_EVENT:
                return CANONICAL_CIRCUIT_BY_EVENT[main_cid]
    except Exception:
        pass

    # 4. Weekend consistency check from official season schedule
    try:
        sched = J.schedule(year, net=False)
        race_sched = next((r for r in sched if _safe_int(r.get("round")) == rnd), None)
        if race_sched and race_sched.get("Circuit", {}).get("circuitId"):
            sched_cid = race_sched["Circuit"]["circuitId"].strip().lower()
            if sched_cid in CIRCUIT_MAP or sched_cid in TRACK_BLUEPRINTS:
                return sched_cid
            if sched_cid in CANONICAL_CIRCUIT_BY_EVENT:
                return CANONICAL_CIRCUIT_BY_EVENT[sched_cid]
    except Exception:
        pass

    # 5. Match against race/event name semantics with word boundary and season-specific routing
    if race_name:
        rn_lower = race_name.lower().replace("_", " ").replace("-", " ")
        if re.search(r'\b(spanish|spain|madrid|madring)\b', rn_lower):
            return "madring" if year >= 2026 else "catalunya"
        for keyword, cid in CANONICAL_CIRCUIT_BY_EVENT.items():
            if re.search(r'\b' + re.escape(keyword) + r'\b', rn_lower):
                return cid

    return "silverstone"


# Official-ish team colours keyed by Jolpica constructorId (modern + historic)
TEAM_COLOURS = {
    "red_bull": "#3671C6", "mclaren": "#FF8000", "ferrari": "#E80020", "mercedes": "#27F4D2",
    "aston_martin": "#229971", "alpine": "#0093CC", "williams": "#64C4FF", "rb": "#6692FF",
    "racing_bulls": "#6692FF", "sauber": "#52E252", "audi": "#BB0A30", "haas": "#B6BABD",
    "cadillac": "#D4D4D4", "alphatauri": "#5E8FAA", "alfa": "#C92D4B", "racing_point": "#F596C8",
    "renault": "#FFF500", "toro_rosso": "#469BFF", "force_india": "#F596C8",
    "lotus": "#E5C158", "brawn": "#E8F15A", "benetton": "#00A3E0", "tyrrell": "#00205B",
    "jordan": "#FFD100", "stewart": "#FFFFFF", "jaguar": "#005A36", "toyota": "#CC0000",
    "bmw_sauber": "#002B49", "prost": "#003399", "ligier": "#0055A5", "brabham": "#002B49",
    "march": "#00B4D8", "cooper": "#1B4D3E", "brm": "#2E5339", "maserati": "#E10600",
    "vanwall": "#1B4D3E", "honda": "#E5E5E5", "minardi": "#000000", "arrows": "#FF6600"
}

# Curated, verified Race Control moments for selected races (year, round)
CURATED_EVENTS = {
    (2024, 6): [  # Miami
        {"lap": 28, "type": "SAFETY_CAR", "message": "SAFETY CAR — Magnussen / Sargeant collision",
         "consequence": "Norris pits under SC while leading and rejoins P1 for his maiden win."},
    ],
    (2024, 8): [  # Monaco
        {"lap": 1, "type": "RED_FLAG", "message": "RED FLAG — Pérez / Magnussen / Hülkenberg crash at Beau Rivage",
         "consequence": "Free tyre change for all; Leclerc controls the restart to win at home."},
    ],
    (2021, 22): [  # Abu Dhabi
        {"lap": 53, "end_lap": 57, "type": "SAFETY_CAR", "message": "SAFETY CAR — Latifi Turn 14 crash",
         "consequence": "Verstappen pits for softs; controversial late restart sets up final-lap championship decider."},
    ],
    (2021, 10): [  # Silverstone
        {"lap": 1, "type": "RED_FLAG", "message": "RED FLAG — Verstappen / Hamilton collision at Copse",
         "consequence": "51G barrier impact for Verstappen; Hamilton recovers from 10s penalty to win."},
    ],
    (1998, 13): [  # Spa-Francorchamps
        {"lap": 1, "type": "RED_FLAG", "message": "RED FLAG — 13-car pile-up on wet descent from La Source",
         "consequence": "Largest start crash in modern F1 history; race restarted with spare cars."},
        {"lap": 25, "type": "RETIREMENT", "driverId": "michael_schumacher", "driver_code": "MSC",
         "message": "MSC OUT — Collision with Coulthard in spray",
         "consequence": "Schumacher loses right-front wheel and stormily confronts Coulthard in McLaren garage."},
    ],
    (2026, 15): [  # Azerbaijan GP (Baku)
        {"lap": 9, "type": "RETIREMENT", "driverId": "stroll", "driver_code": "STR",
         "message": "STR OUT — Water pressure failure (Turn 15)",
         "consequence": "Stroll instructed to pull off at Turn 15 runoff due to terminal water pressure loss. Race Control logged exit on Lap 9 as leader Russell crossed line."},
        {"lap": 30, "end_lap": 38, "type": "SAFETY_CAR",
         "message": "SAFETY CAR DEPLOYED — Gasly / Norris Turn 1 collision",
         "consequence": "Pack neutralised; Russell and Verstappen pit for fresh hard tyres to fight for the win."},
        {"lap": 37, "type": "RETIREMENT", "driverId": "colapinto", "driver_code": "COL",
         "message": "COL OUT — Mechanical issue (Sector 3)",
         "consequence": "Colapinto parked Alpine at escape road."},
        {"lap": 50, "type": "RETIREMENT", "driverId": "bottas", "driver_code": "BOT",
         "message": "BOT OUT — Pit lane retirement",
         "consequence": "Cadillac boxed Bottas with 1 lap remaining."},
    ],
    (2026, 16): [  # Bahrain GP (run at Sepang, Malaysia -- relocated 2026)
        # Sources: Jolpica race result, pit stops and lap
        # timing (neutralised laps 9-12 and 43-51), grandprix.com race analysis (Albon gearbox).
        {"lap": 1, "type": "WEATHER",
         "message": "START DELAYED ~40 MIN — Heavy rain before the start; field started on intermediates",
         "consequence": "Scheduled for 56 laps; the race ran 55."},
        {"lap": 8, "type": "RETIREMENT", "driverId": "bottas", "driver_code": "BOT",
         "message": "BOT OUT — Went off at the end of lap 8",
         "consequence": "Safety Car deployed; most of the field switched from intermediates to slicks on lap 9."},
        {"lap": 9, "end_lap": 12, "type": "SAFETY_CAR",
         "message": "SAFETY CAR — Bottas off track",
         "consequence": "Racing resumed on lap 13."},
        {"lap": 42, "type": "RETIREMENT", "driverId": "albon", "driver_code": "ALB",
         "message": "ALB OUT — Stopped on track with a gearbox problem",
         "consequence": "Virtual Safety Car, then a full Safety Car; Verstappen made his third stop under it on lap 43."},
        {"lap": 43, "end_lap": 51, "type": "SAFETY_CAR",
         "message": "SAFETY CAR — Albon stopped on track (VSC first)",
         "consequence": "Racing resumed on lap 52; Verstappen held off Antonelli to the flag."},
        {"lap": 50, "type": "RETIREMENT", "driverId": "russell", "driver_code": "RUS",
         "message": "RUS OUT — Stopped on track under the Safety Car",
         "consequence": "No cause has been published officially. Antonelli and Hamilton completed the podium behind Verstappen."},
    ],
}


# ------------------------------------------------------------------ helpers
def _safe_int(val: Any, fallback: int = 0) -> int:
    if val is None:
        return fallback
    try:
        s = str(val).strip()
        if not s:
            return fallback
        return int(float(s))
    except (ValueError, TypeError):
        return fallback


def _safe_float(val: Any, fallback: float = 0.0) -> float:
    if val is None:
        return fallback
    try:
        s = str(val).strip()
        if not s:
            return fallback
        return float(s)
    except (ValueError, TypeError):
        return fallback


def _secs(t: Optional[str]) -> Optional[float]:
    if not t:
        return None
    try:
        parts = str(t).strip().split(":")
        s = 0.0
        for p in parts:
            s = s * 60 + float(p)
        return s if s > 0 else None
    except (ValueError, TypeError):
        return None


def _valid_time_str(*times: Optional[str]) -> Optional[str]:
    for t in times:
        if t and _secs(t) is not None:
            return str(t).strip()
    return None


@lru_cache(maxsize=1)
def _geo_features() -> Dict[str, Dict[str, Any]]:
    with open(GEOJSON) as f:
        data = json.load(f)
    return {feat["properties"]["id"]: feat for feat in data["features"]}


# Official F1 broadcast orientations (rotation degrees) matching TV broadcast track maps (optimized for horizontal widescreen 16:9 displays)
CIRCUIT_ORIENTATIONS = {
    "albert_park": -46, "bahrain": -95, "shanghai": -55, "catalunya": 32,
    "monaco": 45, "villeneuve": -55, "ricard": 0, "red_bull_ring": -31,
    "silverstone": 90, "hockenheimring": 0, "hungaroring": 52, "spa": -100,
    "monza": -95, "marina_bay": 0, "sochi": 0, "suzuka": 0,
    "americas": 30, "rodriguez": -8, "interlagos": 90, "yas_marina": 99,
    "imola": 0, "nurburgring": -125, "portimao": -75, "mugello": -125,
    "sepang": -20, "istanbul": 0, "zandvoort": 0, "magny_cours": -105,
    "estoril": -115, "jacarepagua": 0, "jeddah": -85, "miami": -18,
    "losail": -65, "madring": -60, "baku": 73, "vegas": -90,
    "indianapolis": -80, "galvez": 0, "kyalami": 0, "watkins_glen": -85,
}

# Curated circuit metadata (sectors, corner counts, DRS zones)
CIRCUIT_METADATA = {
    "bahrain": {
        "sectors": [
            {"sector": 1, "start_pct": 0.0, "end_pct": 0.28, "color": "#FF7A00", "label": "SECTOR 1"},
            {"sector": 2, "start_pct": 0.28, "end_pct": 0.68, "color": "#FF1867", "label": "SECTOR 2"},
            {"sector": 3, "start_pct": 0.68, "end_pct": 1.0, "color": "#E10600", "label": "SECTOR 3"},
        ],
        "drs_zones": [
            {"name": "ACTIVATION ZONE 1", "start_idx": 680, "end_idx": 50, "label": "ACTIVATION ZONE 1"},
            {"name": "ACTIVATION ZONE 2", "start_idx": 95, "end_idx": 160, "label": "ACTIVATION ZONE 2"},
            {"name": "ACTIVATION ZONE 3", "start_idx": 440, "end_idx": 505, "label": "ACTIVATION ZONE 3"},
        ],
        "drs_detections": [
            {"name": "DETECTION POINT 1", "idx": 665},
            {"name": "DETECTION POINT 2", "idx": 90},
            {"name": "DETECTION POINT 3", "idx": 430},
        ],
    },
    "albert_park": {
        "sectors": [
            {"sector": 1, "start_pct": 0.0, "end_pct": 0.31, "color": "#FF7A00", "label": "SECTOR 1"},
            {"sector": 2, "start_pct": 0.31, "end_pct": 0.68, "color": "#FF1867", "label": "SECTOR 2"},
            {"sector": 3, "start_pct": 0.68, "end_pct": 1.0, "color": "#E10600", "label": "SECTOR 3"},
        ],
        "turn_indices": [45, 68, 146, 172, 202, 254, 280, 334, 448, 470, 559, 594, 630, 655],
        "drs_zones": [
            {"name": "ACTIVATION ZONE 1", "start_idx": 680, "end_idx": 35, "label": "ACTIVATION ZONE 1"},
            {"name": "ACTIVATION ZONE 2", "start_idx": 75, "end_idx": 135, "label": "ACTIVATION ZONE 2"},
            {"name": "ACTIVATION ZONE 3", "start_idx": 340, "end_idx": 435, "label": "ACTIVATION ZONE 3"},
            {"name": "ACTIVATION ZONE 4", "start_idx": 480, "end_idx": 545, "label": "ACTIVATION ZONE 4"},
        ],
        "drs_detections": [
            {"name": "DETECTION POINT 1", "idx": 320},
            {"name": "DETECTION POINT 2", "idx": 615},
        ],
    },
    "monza": {
        "sectors": [
            {"sector": 1, "start_pct": 0.0, "end_pct": 0.33, "color": "#FF7A00", "label": "SECTOR 1"},
            {"sector": 2, "start_pct": 0.33, "end_pct": 0.67, "color": "#FF1867", "label": "SECTOR 2"},
            {"sector": 3, "start_pct": 0.67, "end_pct": 1.0, "color": "#E10600", "label": "SECTOR 3"},
        ],
        "turn_indices": [83, 140, 227, 276, 320, 380, 453, 477, 520, 602, 630],
        "drs_zones": [
            {"name": "ACTIVATION ZONE 1", "start_idx": 640, "end_idx": 70, "label": "ACTIVATION ZONE 1"},
            {"name": "ACTIVATION ZONE 2", "start_idx": 340, "end_idx": 440, "label": "ACTIVATION ZONE 2"},
        ],
        "drs_detections": [
            {"name": "DETECTION POINT 1", "idx": 610},
            {"name": "DETECTION POINT 2", "idx": 315},
        ],
    },
    "silverstone": {
        "sectors": [
            {"sector": 1, "start_pct": 0.0, "end_pct": 0.32, "color": "#FF7A00", "label": "SECTOR 1"},
            {"sector": 2, "start_pct": 0.32, "end_pct": 0.68, "color": "#FF1867", "label": "SECTOR 2"},
            {"sector": 3, "start_pct": 0.68, "end_pct": 1.0, "color": "#E10600", "label": "SECTOR 3"},
        ],
        "turn_indices": [32, 60, 108, 128, 148, 190, 270, 329, 359, 424, 483, 501, 525, 560, 618, 635, 660, 690],
        "drs_zones": [
            {"name": "ACTIVATION ZONE 1", "start_idx": 195, "end_idx": 260, "label": "ACTIVATION ZONE 1"},
            {"name": "ACTIVATION ZONE 2", "start_idx": 535, "end_idx": 610, "label": "ACTIVATION ZONE 2"},
        ],
        "drs_detections": [
            {"name": "DETECTION POINT 1", "idx": 175},
            {"name": "DETECTION POINT 2", "idx": 515},
        ],
    },
    "spa": {
        "sectors": [
            {"sector": 1, "start_pct": 0.0, "end_pct": 0.31, "color": "#FF7A00", "label": "SECTOR 1"},
            {"sector": 2, "start_pct": 0.31, "end_pct": 0.73, "color": "#FF1867", "label": "SECTOR 2"},
            {"sector": 3, "start_pct": 0.73, "end_pct": 1.0, "color": "#E10600", "label": "SECTOR 3"},
        ],
        "turn_indices": [25, 60, 80, 120, 234, 258, 299, 324, 378, 410, 449, 465, 495, 519, 560, 600, 640, 686, 705],
        "drs_zones": [
            {"name": "ACTIVATION ZONE 1", "start_idx": 130, "end_idx": 225, "label": "ACTIVATION ZONE 1"},
            {"name": "ACTIVATION ZONE 2", "start_idx": 708, "end_idx": 15, "label": "ACTIVATION ZONE 2"},
        ],
        "drs_detections": [
            {"name": "DETECTION POINT 1", "idx": 95},
            {"name": "DETECTION POINT 2", "idx": 690},
        ],
    },
}

def _detect_apex_indices(speed_kmh: List[int], n_points: int) -> List[int]:
    """Dynamically detect corner apexes from local speed minima for any circuit."""
    cands = []
    for i in range(n_points):
        is_min = True
        for d in range(1, 5):
            if speed_kmh[(i - d) % n_points] < speed_kmh[i] or speed_kmh[(i + d) % n_points] < speed_kmh[i]:
                is_min = False
                break
        if is_min and speed_kmh[i] < 275:
            cands.append((i, speed_kmh[i]))
    res = []
    for idx, spd in cands:
        if not res or (idx - res[-1][0]) >= 14:
            res.append((idx, spd))
        elif spd < res[-1][1]:
            res[-1] = (idx, spd)
    return [idx for idx, _ in res]


@lru_cache(maxsize=64)
def circuit_geometry(circuit_id: str, n_points: int = 720) -> Optional[Dict[str, Any]]:
    """Projected, rotated, arc-length-resampled outline + curvature-based speed profile & Tracing Insights styling metadata."""
    feat = _geo_features().get(CIRCUIT_MAP.get(circuit_id, ""))
    rot_deg = CIRCUIT_ORIENTATIONS.get(circuit_id, 0)
    meta = CIRCUIT_METADATA.get(circuit_id, {})

    if not feat:
        # Procedural racing circuit loop fallback so every historic F1 circuit is replayable
        out = []
        for i in range(n_points):
            th = 2 * math.pi * i / n_points
            r = 1000.0 * (1 + 0.25 * math.sin(2 * th) + 0.12 * math.cos(3 * th) - 0.08 * math.sin(5 * th))
            out.append((r * math.cos(th), r * math.sin(th)))
        total = 5200.0
        v = [int(min(320, max(90, 210 + 90 * math.cos(2 * 2 * math.pi * i / n_points)))) for i in range(n_points)]
        tfrac = [round(i / n_points, 5) for i in range(n_points + 1)]
        xs, ys = [p[0] for p in out], [p[1] for p in out]
        minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
        span = max(maxx - minx, maxy - miny) or 1.0
        v_kmh = [round(s * 3.6) for s in v]
        turn_idxs = _detect_apex_indices(v_kmh, n_points)
        turns = [{"number": i + 1, "idx": idx, "pct": round(idx / n_points, 4)} for i, idx in enumerate(turn_idxs)]
        return {
            "points": [[round((x - minx) / span, 4), round((y - miny) / span, 4)] for x, y in out],
            "aspect": round((maxx - minx) / (maxy - miny), 4) if (maxy - miny) else 1.0,
            "speed_kmh": v_kmh,
            "tfrac": tfrac,
            "length_km": 5.2,
            "name": circuit_id.replace("_", " ").title(),
            "rotation_deg": rot_deg,
            "sectors": [
                {"sector": 1, "start_pct": 0.0, "end_pct": 0.33, "color": "#FF7A00", "label": "SECTOR 1"},
                {"sector": 2, "start_pct": 0.33, "end_pct": 0.67, "color": "#FF1867", "label": "SECTOR 2"},
                {"sector": 3, "start_pct": 0.67, "end_pct": 1.0, "color": "#E10600", "label": "SECTOR 3"},
            ],
            "turns": turns,
            "drs_zones": [{"name": "ACTIVATION ZONE 1", "start_idx": int(n_points * 0.92), "end_idx": int(n_points * 0.05), "label": "ACTIVATION ZONE 1"}],
            "drs_detections": [{"name": "DETECTION POINT 1", "idx": int(n_points * 0.88)}],
        }

    coords = feat["geometry"]["coordinates"]
    if feat["geometry"]["type"] == "MultiLineString":
        coords = max(coords, key=len)
    lat0 = sum(c[1] for c in coords) / len(coords)
    k = 111_320.0
    pts = [((c[0]) * k * math.cos(math.radians(lat0)), -(c[1]) * k) for c in coords]  # metres, y-down
    if pts[0] != pts[-1]:
        pts.append(pts[0])

    # Apply official Formula 1 broadcast orientation rotation
    if rot_deg:
        rot_rad = math.radians(rot_deg)
        cos_a, sin_a = math.cos(rot_rad), math.sin(rot_rad)
        pts = [(x * cos_a - y * sin_a, x * sin_a + y * cos_a) for x, y in pts]

    # Arc-length resample
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    total = sum(seg)
    out, acc, j = [], 0.0, 0
    for i in range(n_points):
        target = total * i / n_points
        while j < len(seg) - 1 and acc + seg[j] < target:
            acc += seg[j]
            j += 1
        t = (target - acc) / seg[j] if seg[j] else 0
        a, b = pts[j], pts[j + 1]
        out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))

    # Speed profile: v = sqrt(a_lat * R), then accel/brake limited passes
    ds = total / n_points
    w = 6
    v = []
    for i in range(n_points):
        p0, p1, p2 = out[i - w], out[i], out[(i + w) % n_points]
        a_, b_, c_ = math.dist(p0, p1), math.dist(p1, p2), math.dist(p0, p2)
        area2 = abs((p1[0] - p0[0]) * (p2[1] - p0[1]) - (p1[1] - p0[1]) * (p2[0] - p0[0]))
        R = (a_ * b_ * c_) / (2 * area2) if area2 > 1e-6 else 1e9
        v.append(min(90.0, math.sqrt(4.5 * 9.81 * R)))  # m/s, cap ~324 km/h
    for _ in range(2):
        for i in range(1, 2 * n_points):  # traction
            a, b = (i - 1) % n_points, i % n_points
            v[b] = min(v[b], math.sqrt(v[a] ** 2 + 2 * 11.0 * ds))
        for i in range(2 * n_points, 0, -1):  # braking
            a, b = i % n_points, (i - 1) % n_points
            v[b] = min(v[b], math.sqrt(v[a] ** 2 + 2 * 40.0 * ds))

    # Cumulative time fraction for time->distance mapping
    tcum = [0.0]
    for i in range(n_points):
        tcum.append(tcum[-1] + ds / max(v[i], 15.0))
    lap_t = tcum[-1]
    tfrac = [round(t / lap_t, 5) for t in tcum]

    xs, ys = [p[0] for p in out], [p[1] for p in out]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    span = max(maxx - minx, maxy - miny)
    v_kmh = [round(s * 3.6) for s in v]

    # Turns / corners
    turn_indices = meta.get("turn_indices") or _detect_apex_indices(v_kmh, n_points)
    turns = [{"number": i + 1, "idx": idx, "pct": round(idx / n_points, 4)} for i, idx in enumerate(turn_indices)]

    # Sectors
    sectors = meta.get("sectors") or [
        {"sector": 1, "start_pct": 0.0, "end_pct": 0.33, "color": "#FF7A00", "label": "SECTOR 1"},
        {"sector": 2, "start_pct": 0.33, "end_pct": 0.67, "color": "#FF1867", "label": "SECTOR 2"},
        {"sector": 3, "start_pct": 0.67, "end_pct": 1.0, "color": "#E10600", "label": "SECTOR 3"},
    ]

    # DRS zones & detection points
    drs_zones = meta.get("drs_zones") or [
        {"name": "ACTIVATION ZONE 1", "start_idx": int(n_points * 0.92), "end_idx": int(n_points * 0.05), "label": "ACTIVATION ZONE 1"}
    ]
    drs_detections = meta.get("drs_detections") or [
        {"name": "DETECTION POINT 1", "idx": int(n_points * 0.88)}
    ]

    bp = TRACK_BLUEPRINTS.get(circuit_id) or TRACK_BLUEPRINTS.get(CIRCUIT_MAP.get(circuit_id, "")) or {}

    return {
        "points": [[round((x - minx) / span, 4), round((y - miny) / span, 4)] for x, y in out],
        "aspect": round((maxx - minx) / (maxy - miny), 4),
        "speed_kmh": v_kmh,
        "tfrac": tfrac,
        "length_km": bp.get("length_km") or round(total / 1000, 3),
        "name": bp.get("name") or feat["properties"].get("Name"),
        "country": bp.get("country", ""),
        "country_code": bp.get("country_code", ""),
        "rotation_deg": rot_deg,
        "sectors": sectors,
        "turns": turns,
        "drs_zones": drs_zones,
        "drs_detections": drs_detections,
        "lap_record": bp.get("lap_record", "1:30.000"),
        "full_throttle_pct": bp.get("full_throttle_pct", 65),
        "tyre_stress": bp.get("tyre_stress", "Level 3/5"),
        "pit_loss_s": bp.get("pit_loss_s", 21.0),
        "turns_count": bp.get("turns_count", len(turns)),
        "key_turns": bp.get("turns", [])
    }


# ------------------------------------------------------------------ seasons
def season_races(year: int, net: bool = True) -> List[Dict[str, Any]]:
    sched = J.schedule(year, net)
    winners_map = J.season_winners(year, net)
    today = datetime.date.today()
    out = []
    for r in sched:
        rnd = _safe_int(r.get("round"), fallback=1)
        w = winners_map.get(rnd)
        if not w:
            # A round run in the last few weeks but missing from the winners list: ask
            # Jolpica for its result (older rounds come from the local cache only).
            try:
                recent = 0 <= (today - datetime.date.fromisoformat(r.get("date", ""))).days <= J.RECENT_DAYS
            except ValueError:
                recent = False
            res = J.results(year, rnd, net=net and recent)
            if res and res.get("Results"):
                w = res["Results"][0]
        winner = None
        if w:
            cid = w.get("Constructor", {}).get("constructorId", "")
            winner = {
                "code": w["Driver"].get("code", w["Driver"]["familyName"][:3].upper()),
                "name": f'{w["Driver"]["givenName"]} {w["Driver"]["familyName"]}',
                "team": w.get("Constructor", {}).get("name", "F1 Team"),
                "color": TEAM_COLOURS.get(cid, "#FFFFFF")
            }
        is_completed = (winner is not None) or (year < today.year)
        # The Jolpica schedule flags every sprint weekend (2021-2026). The old hard-coded
        # fallback lists were wrong (e.g. listed 2023 R19 Mexico instead of R20 Sao Paulo).
        has_sprint = "Sprint" in r
        sessions = ["race", "qualifying"]
        if has_sprint:
            sessions.insert(1, "sprint")
            if year >= 2023:  # Sprint Shootout (2023) / Sprint Qualifying (2024+) session
                sessions.insert(2, "sprint_qualifying")
        _rc = r.get("Circuit", {})
        _cid = _rc.get("circuitId", ""); _cname = _rc.get("circuitName", "")
        _loc = _rc.get("Location", {}).get("locality", ""); _ctry = _rc.get("Location", {}).get("country", "")
        _reloc = EVENT_RELOCATIONS.get((year, rnd))
        if _reloc:
            _cid, _cname, _loc, _ctry = _reloc["circuit_id"], _reloc["circuit_name"], _reloc["locality"], _reloc["country"]
        out.append({
            "round": rnd, "race_name": re.sub(r'^\d{4}\s+', '', r.get("raceName", f"Round {rnd}")), "date": r.get("date", ""),
            "circuit_id": _cid, "circuit_name": _cname,
            "locality": _loc, "country": _ctry,
            "has_geometry": True,
            "has_sprint": has_sprint,
            "sessions": sessions,
            "completed": is_completed, "winner": winner,
        })
    return out


def _standings_round(year: int) -> Optional[int]:
    d = J.cached(f"{year}_driverStandings", "", allow_network=False)
    try:
        return int(d["MRData"]["StandingsTable"]["StandingsLists"][0]["round"])
    except Exception:
        return None


def _reconcile_with_results(year: int, ds: List[Dict[str, Any]], cs: List[Dict[str, Any]]) -> Tuple[List, List, bool]:
    """Cross-check a standings table against the sum of cached race + sprint results.

    Since 1991 every result counts toward the title, so the standings must equal the
    sum of the classification points. If a standings file disagrees (e.g. a round
    counted twice), rebuild points and wins from the per-race results. Only runs when
    results for every round up to the standings round are cached (cache-only, no
    network), so a missing round can never pull the totals down.
    """
    import logging
    if year < 1991 or not ds or not cs:
        return ds, cs, False
    # Only intervene when the standings contradict themselves: team-mates' points must
    # add up to their constructor's total. Correct live standings pass this check and
    # are returned untouched (so a stale per-race file can never override them).
    team_sum: Dict[str, float] = {}
    skip_teams = set()  # teams touched by a mid-season driver move can't be checked this way
    for r in ds:
        teams = r.get("Constructors") or []
        if len(teams) != 1:
            skip_teams.update(t["constructorId"] for t in teams)
            continue
        tid = teams[0]["constructorId"]
        team_sum[tid] = team_sum.get(tid, 0.0) + _safe_float(r.get("points"), fallback=0.0)
    consistent = all(
        abs(team_sum.get(c["Constructor"]["constructorId"], 0.0) - _safe_float(c.get("points"), fallback=0.0)) <= 0.01
        for c in cs if c["Constructor"]["constructorId"] not in skip_teams
    )
    if consistent:
        return ds, cs, False
    upto = _standings_round(year)
    if not upto:
        return ds, cs, False
    d_pts: Dict[str, float] = {}
    d_wins: Dict[str, int] = {}
    c_pts: Dict[str, float] = {}
    c_wins: Dict[str, int] = {}
    for rnd in range(1, upto + 1):
        race = J.results(year, rnd, net=False)
        if not race or not race.get("Results"):
            return ds, cs, False  # incomplete results: trust the standings file
        sessions = [(race["Results"], True)]
        spr = J.sprint_results(year, rnd, net=False)
        if spr and spr.get("SprintResults"):
            sessions.append((spr["SprintResults"], False))
        for rows, is_race in sessions:
            for x in rows:
                did = x["Driver"]["driverId"]
                cid = x["Constructor"]["constructorId"]
                pts = _safe_float(x.get("points"), fallback=0.0)
                d_pts[did] = d_pts.get(did, 0.0) + pts
                c_pts[cid] = c_pts.get(cid, 0.0) + pts
                if is_race and x.get("position") == "1":
                    d_wins[did] = d_wins.get(did, 0) + 1
                    c_wins[cid] = c_wins.get(cid, 0) + 1

    def _rebuild(rows, key, pts_map, wins_map):
        mismatch = any(
            abs(_safe_float(r.get("points"), fallback=0.0) - pts_map.get(r[key][f"{key.lower()}Id"], 0.0)) > 0.01
            or _safe_int(r.get("wins"), fallback=0) != wins_map.get(r[key][f"{key.lower()}Id"], 0)
            for r in rows
        )
        if not mismatch:
            return rows, False
        fixed = []
        for r in rows:
            rid = r[key][f"{key.lower()}Id"]
            nr = dict(r)
            nr["points"] = f"{pts_map.get(rid, 0.0):g}"
            nr["wins"] = str(wins_map.get(rid, 0))
            fixed.append(nr)
        fixed.sort(key=lambda r: (-float(r["points"]), -int(r["wins"])))
        for i, r in enumerate(fixed):
            r["position"] = r["positionText"] = str(i + 1)
        return fixed, True

    ds2, d_changed = _rebuild(ds, "Driver", d_pts, d_wins)
    cs2, c_changed = _rebuild(cs, "Constructor", c_pts, c_wins) if cs else (cs, False)
    if d_changed or c_changed:
        logging.getLogger("f1_simgent.standings").warning(
            f"[STANDINGS RECONCILED] {year} standings file disagreed with race results "
            f"(drivers={d_changed}, constructors={c_changed}); using totals rebuilt from results."
        )
    return ds2, cs2, (d_changed or c_changed)


def standings(year: int, net: bool = True) -> Dict[str, Any]:
    ds = J.driver_standings(year, net)
    cs = J.constructor_standings(year, net)
    ds, cs, reconciled = _reconcile_with_results(year, ds, cs)
    return {
        "year": year, "source": ("jolpica (reconciled with race results)" if reconciled else "jolpica") if ds else "unavailable",
        "drivers": [{
            "rank": _safe_int(d.get("position"), fallback=i + 1),
            "driver": f'{d["Driver"]["givenName"]} {d["Driver"]["familyName"]}',
            "acronym": d["Driver"].get("code", ""),
            "team": d["Constructors"][-1]["name"] if d.get("Constructors") else "",
            "color": TEAM_COLOURS.get(d["Constructors"][-1]["constructorId"], "#FFFFFF") if d.get("Constructors") else "#FFFFFF",
            "points": _safe_float(d.get("points"), fallback=0.0), "wins": _safe_int(d.get("wins"), fallback=0),
        } for i, d in enumerate(ds)],
        "constructors": [{
            "rank": _safe_int(c.get("position"), fallback=i + 1),
            "team": c["Constructor"]["name"],
            "color": TEAM_COLOURS.get(c["Constructor"]["constructorId"], "#FFFFFF"),
            "points": _safe_float(c.get("points"), fallback=0.0), "wins": _safe_int(c.get("wins"), fallback=0),
        } for i, c in enumerate(cs)],
    }


# ------------------------------------------------------------------ replay
def _build_qualifying_replay(year: int, rnd: int, net: bool = True, circuit_override: Optional[str] = None,
                             sprint: bool = False) -> Optional[Dict[str, Any]]:
    """Qualifying replay. sprint=True builds the Sprint Qualifying / Sprint Shootout session
    (OpenF1 classification) instead of Grand Prix qualifying."""
    if sprint:
        qres = J.sprint_qualifying(year, rnd, net)
        if not qres or not qres.get("QualifyingResults"):
            return None  # never invent a sprint qualifying session
        res = None
    else:
        qres = J.qualifying_results(year, rnd, net)
        res = J.results(year, rnd, net)
    times_estimated = False
    circuit_info = None
    race_name = f"Round {rnd} Qualifying"
    date_str = ""
    cid = ""
    cname = ""
    loc = ""
    country = ""

    drivers_raw = []
    if qres and qres.get("QualifyingResults"):
        drivers_raw = qres["QualifyingResults"]
        race_name = qres.get("raceName", race_name)
        date_str = qres.get("date", "")
        circuit_info = qres.get("Circuit", {})
    elif res and res.get("Results"):
        # No qualifying classification cached: order by race grid and ESTIMATE lap times so
        # the replay can animate. These times are not real and must never be quoted.
        times_estimated = True
        race_name = res.get("raceName", race_name)
        date_str = res.get("date", "")
        circuit_info = res.get("Circuit", {})
        sorted_res = sorted(res.get("Results", []), key=lambda r: _safe_int(r.get("grid") or r.get("position"), fallback=99))
        base_lap = 78.5
        for idx, r in enumerate(sorted_res):
            pos = idx + 1
            gap = 0.0 if pos == 1 else round(0.08 * (pos - 1) + 0.02 * (pos % 3), 3)
            lap_s = base_lap + gap
            m_part = int(lap_s // 60)
            s_part = lap_s % 60
            time_str = f"{m_part}:{s_part:06.3f}"
            entry = dict(r)
            entry["position"] = str(pos)
            if pos <= 10:
                entry["Q1"] = f"{m_part}:{s_part + 1.2:06.3f}"
                entry["Q2"] = f"{m_part}:{s_part + 0.5:06.3f}"
                entry["Q3"] = time_str
            elif pos <= 15:
                entry["Q1"] = f"{m_part}:{s_part + 1.4:06.3f}"
                entry["Q2"] = time_str
            else:
                entry["Q1"] = time_str
            drivers_raw.append(entry)
    else:
        return None

    raw_cid = circuit_info.get("circuitId", "") if circuit_info else ""
    cid = resolve_canonical_circuit(year, rnd, raw_circuit_id=raw_cid, race_name=race_name, circuit_override=circuit_override)
    geo = circuit_geometry(cid) if cid else None
    cname = geo.get("name") if geo else (circuit_info.get("circuitName") if circuit_info else cid.replace("_", " ").title())
    loc = circuit_info.get("Location", {}).get("locality", "") if circuit_info else ""
    country = geo.get("country", "") if geo else (circuit_info.get("Location", {}).get("country", "") if circuit_info else "")
    _reloc = EVENT_RELOCATIONS.get((year, rnd))
    if _reloc:
        cname, loc, country = _reloc["circuit_name"], _reloc["locality"], _reloc["country"]

    p1 = drivers_raw[0] if drivers_raw else None
    pole_time_str = _valid_time_str(p1.get("Q3"), p1.get("Q2"), p1.get("Q1")) if p1 else "1:30.000"
    if not pole_time_str:
        pole_time_str = (p1.get("Q3") or p1.get("Q2") or p1.get("Q1")) if p1 else "1:30.000"
    pole_secs = _secs(pole_time_str) or 90.0

    drivers = []
    for idx, r in enumerate(drivers_raw):
        did = r["Driver"]["driverId"]
        pos = _safe_int(r.get("position"), fallback=idx + 1)
        best_valid = _valid_time_str(r.get("Q3"), r.get("Q2"), r.get("Q1"))
        best_str = best_valid or r.get("Q3") or r.get("Q2") or r.get("Q1") or "NO TIME"
        best_s = _secs(best_valid) if best_valid else None
        if best_s is None or best_s <= 0:
            best_s = pole_secs + 0.1 * pos
        delta_s = round(best_s - pole_secs, 3)
        delta_str = "POLE" if pos == 1 else f"+{delta_s:.3f}s"
        # Reaching a segment is shown by the field being present (Jolpica convention); a driver
        # can reach Q2 and set no time (empty string), e.g. when saving engine parts for a penalty.
        stage = "Q3" if "Q3" in r else ("Q2" if "Q2" in r else "Q1")

        s_q1 = _secs(r.get("Q1"))
        t_q1 = s_q1 if (s_q1 is not None and s_q1 > 0) else (pole_secs + 1.4 + 0.05 * pos)

        s_q2 = _secs(r.get("Q2"))
        t_q2 = s_q2 if (s_q2 is not None and s_q2 > 0) else (t_q1 + 40.0)

        s_q3 = _secs(r.get("Q3"))
        t_q3 = s_q3 if (s_q3 is not None and s_q3 > 0) else (t_q2 + 45.0)

        cum = [round(t_q1, 3), round(t_q1 + t_q2, 3), round(t_q1 + t_q2 + t_q3, 3)]

        drivers.append({
            "id": did,
            "number": _safe_int(r.get("number"), fallback=0),
            "code": r["Driver"].get("code", r["Driver"]["familyName"][:3].upper()),
            "name": f'{r["Driver"]["givenName"]} {r["Driver"]["familyName"]}',
            "team": r["Constructor"]["name"],
            "team_id": r["Constructor"]["constructorId"],
            "color": TEAM_COLOURS.get(r["Constructor"]["constructorId"], "#FFFFFF"),
            "grid": pos,
            "finish": pos,
            "status": f"{stage} ({delta_str})",
            "classified_text": r.get("positionText") or str(pos),
            "points": 0.0,
            "laps": 3,
            "cum": cum,
            "pits": [2] if stage == "Q1" else ([3] if stage == "Q2" else []),
            "synthetic": "Q3" not in r and "Q2" not in r,
            "best_lap": best_str,
            "pole_delta": delta_str,
            "qualifying_stage": stage,
        })

    n_cars = len(drivers)
    seg = "SQ" if sprint else "Q"
    pole_label = "SPRINT POLE" if sprint else "POLE POSITION"
    pole_time_txt = "" if times_estimated else f" ({pole_time_str})"
    p2_delta_txt = "" if times_estimated else (f" ({drivers[1]['pole_delta']})" if n_cars > 1 else "")
    # Cut-offs from the data (20 cars: 15/10, 22 cars from 2026: 16/10) instead of assuming 20
    n_q2 = sum(1 for d in drivers if d["qualifying_stage"] in ("Q2", "Q3")) or min(15, n_cars)
    n_q3 = sum(1 for d in drivers if d["qualifying_stage"] == "Q3") or min(10, n_cars)
    events = [
        {"lap": 1, "type": "FLAG", "message": f"{seg}1 END — P{n_q2 + 1}–P{n_cars} eliminated",
         "consequence": f"Top {n_q2} advance to {seg}2."},
        {"lap": 2, "type": "FLAG", "message": f"{seg}2 END — P{n_q3 + 1}–P{n_q2} eliminated",
         "consequence": f"Top {n_q3} advance to {seg}3."},
        {"lap": 3, "type": "CHEQUERED", "message": f"{seg}3 {pole_label} — {drivers[0]['code'] if drivers else 'Pole'}{pole_time_txt}",
         "consequence": f"Front row: {drivers[1]['code']} lines up P2{p2_delta_txt}." if n_cars > 1 else "Pole decided."},
    ]
    for note in (qres.get("notes") or []) if sprint else []:
        events.append({"lap": 3, "type": "FLAG", "message": "STEWARDS NOTE", "consequence": note})

    clean_qname = re.sub(r'^(?:\d{4}\s+|Flag of [^—\-]+?\s+)', '', race_name)
    if clean_qname.casefold().endswith('qualifying'):
        clean_qname = clean_qname[:-len('qualifying')].rstrip().removesuffix('-').rstrip()
    if sprint:
        sq_session = qres.get("session") or "Sprint Qualifying"
        session_meta = {"race_name": f"{clean_qname} - {sq_session}", "session_type": "sprint_qualifying",
                        "session_name": sq_session, "source": "OpenF1 (Sprint Qualifying)",
                        "notes": qres.get("notes", []), "source_url": qres.get("source_url", "")}
    else:
        session_meta = {"race_name": f"{clean_qname} - Qualifying", "session_type": "qualifying",
                        "session_name": "Official Qualifying Shootout",
                        "source": ("Estimated from race grid (no qualifying data cached)" if times_estimated
                                   else "Jolpica-F1 (Official Qualifying)")}
    return {
        "meta": {
            "year": year, "round": rnd,
            "date": date_str, "circuit_id": cid, "circuit_name": cname,
            "locality": loc, "country": country,
            "total_laps": 3, "has_lap_data": True,
            "pole_time": None if times_estimated else pole_time_str,
            "times_estimated": times_estimated,
            "pole_driver": drivers[0]["code"] if drivers else "",
            **session_meta,
        },
        "track": geo,
        "drivers": drivers,
        "events": events,
    }


def _build_sprint_replay(year: int, rnd: int, net: bool = True, circuit_override: Optional[str] = None) -> Optional[Dict[str, Any]]:
    sp = J.sprint_results(year, rnd, net)
    res = J.results(year, rnd, net)
    circuit_info = None
    race_name = f"Round {rnd} Sprint"
    date_str = ""
    cid = ""
    cname = ""
    loc = ""
    country = ""
    drivers_raw = []

    if sp and sp.get("SprintResults"):
        drivers_raw = sp["SprintResults"]
        race_name = sp.get("raceName", race_name)
        date_str = sp.get("date", "")
        circuit_info = sp.get("Circuit", {})
    elif res and res.get("Results"):
        race_name = res.get("raceName", race_name)
        date_str = res.get("date", "")
        circuit_info = res.get("Circuit", {})
        gp_laps = _safe_int(res["Results"][0].get("laps"), fallback=50) if res.get("Results") else 50
        sprint_laps = max(15, int(gp_laps * 0.33))
        for idx, r in enumerate(res.get("Results", [])):
            entry = dict(r)
            pos = _safe_int(r.get("position"), fallback=idx + 1)
            pts_table = {1: 8, 2: 7, 3: 6, 4: 5, 5: 4, 6: 3, 7: 2, 8: 1}
            entry["points"] = pts_table.get(pos, 0)
            r_laps = _safe_int(r.get("laps"), fallback=0)
            entry["laps"] = sprint_laps if r.get("status", "").startswith(("Finished", "Lapped", "+")) else max(1, int(r_laps * 0.33))
            drivers_raw.append(entry)
    else:
        return None

    raw_cid = circuit_info.get("circuitId", "") if circuit_info else ""
    cid = resolve_canonical_circuit(year, rnd, raw_circuit_id=raw_cid, race_name=race_name, circuit_override=circuit_override)
    geo = circuit_geometry(cid) if cid else None
    cname = geo.get("name") if geo else (circuit_info.get("circuitName") if circuit_info else cid.replace("_", " ").title())
    loc = circuit_info.get("Location", {}).get("locality", "") if circuit_info else ""
    country = geo.get("country", "") if geo else (circuit_info.get("Location", {}).get("country", "") if circuit_info else "")
    _reloc = EVENT_RELOCATIONS.get((year, rnd))
    if _reloc:
        cname, loc, country = _reloc["circuit_name"], _reloc["locality"], _reloc["country"]

    winner_laps = _safe_int(drivers_raw[0].get("laps"), fallback=19) if drivers_raw else 19
    winner_time = None
    try:
        winner_time = int(drivers_raw[0]["Time"]["millis"]) / 1000
    except (KeyError, TypeError, ValueError):
        winner_time = None

    base_lap_s = (winner_time / winner_laps) if (winner_time and winner_laps > 0) else 91.5

    drivers = []
    for idx, r in enumerate(drivers_raw):
        did = r["Driver"]["driverId"]
        pos = _safe_int(r.get("position"), fallback=idx + 1)
        n = _safe_int(r.get("laps"), fallback=0)
        total = None
        try:
            total = int(r["Time"]["millis"]) / 1000
        except (KeyError, TypeError, ValueError):
            pass
        per = (total / n) if (total and n > 0) else base_lap_s * (1 + 0.003 * pos)

        cum = []
        acc = 0.0
        for l in range(1, n + 1):
            deg = (l - 1) * 0.04
            variation = 0.08 * math.sin(l * 0.9 + pos)
            lap_t = per + deg + variation
            acc += lap_t
            cum.append(round(acc, 3))

        pts = _safe_float(r.get("points"), fallback=0.0)
        drivers.append({
            "id": did,
            "number": _safe_int(r.get("number"), fallback=0),
            "code": r["Driver"].get("code", r["Driver"]["familyName"][:3].upper()),
            "name": f'{r["Driver"]["givenName"]} {r["Driver"]["familyName"]}',
            "team": r["Constructor"]["name"],
            "team_id": r["Constructor"]["constructorId"],
            "color": TEAM_COLOURS.get(r["Constructor"]["constructorId"], "#FFFFFF"),
            "grid": _safe_int(r.get("grid"), fallback=pos),
            "finish": pos,
            "status": r.get("status", "Finished"),
            "classified_text": r.get("positionText") or str(pos),
            "points": pts,
            "laps": n,
            "cum": cum,
            "pits": [],
            "synthetic": True,
        })

    events = [
        {"lap": 1, "type": "FLAG", "message": "SPRINT RACE START — 100km flat-out sprint underway",
         "consequence": "No mandatory pit stops; points awarded to top 8 finishers (8-7-6-5-4-3-2-1)."},
        {"lap": max(1, winner_laps), "type": "CHEQUERED", "message": f"SPRINT FINISH — {drivers[0]['code'] if drivers else 'Leader'} wins the Sprint Race",
         "consequence": f"Secures 8 championship points; {drivers[1]['code']} P2 (7 pts), {drivers[2]['code']} P3 (6 pts)." if len(drivers) > 2 else "Sprint finished."}
    ]

    clean_sname = re.sub(r'^(?:\d{4}\s+|Flag of [^—\-]+?\s+)', '', race_name)
    if clean_sname.casefold().endswith('sprint'):
        clean_sname = clean_sname[:-len('sprint')].rstrip().removesuffix('-').rstrip()
    return {
        "meta": {
            "year": year, "round": rnd, "race_name": f"{clean_sname} - Sprint",
            "date": date_str, "circuit_id": cid, "circuit_name": cname,
            "locality": loc, "country": country,
            "total_laps": max(1, winner_laps), "has_lap_data": True,
            "session_type": "sprint",
            "session_name": "F1 Sprint Race (100km)",
            "source": "Jolpica-F1 (Sprint Classification)",
        },
        "track": geo,
        "drivers": drivers,
        "events": events,
    }


def _build_race_replay(year: int, rnd: int, net: bool = True, circuit_override: Optional[str] = None) -> Optional[Dict[str, Any]]:
    res = J.results(year, rnd, net)
    if not res:
        w_map = J.season_winners(year, net)
        w_entry = w_map.get(rnd)
        if w_entry:
            sched = J.schedule(year, net)
            race_sched = next((r for r in sched if _safe_int(r.get("round")) == rnd), None)
            circuit_info = (race_sched.get("Circuit") if race_sched else None) or w_entry.get("Circuit", {})
            rname = (race_sched.get("raceName") if race_sched else None) or w_entry.get("raceName", f"{year} Round {rnd} Grand Prix")
            date_s = (race_sched.get("date") if race_sched else "") or w_entry.get("date", "")
            res = {
                "season": str(year),
                "round": str(rnd),
                "raceName": rname,
                "date": date_s,
                "Circuit": circuit_info,
                "Results": [w_entry]
            }
        else:
            return None
    lap_rows = J.laps(year, rnd, net)
    stops = J.pitstops(year, rnd, net)
    raw_cid = res.get("Circuit", {}).get("circuitId", "")
    race_name = res.get("raceName", "")
    cid = resolve_canonical_circuit(year, rnd, raw_circuit_id=raw_cid, race_name=race_name, circuit_override=circuit_override)
    geo = circuit_geometry(cid)

    # Per-driver lap times from real lap data
    lap_times: Dict[str, List[float]] = {}
    for lap in lap_rows:
        for t in lap["Timings"]:
            s = _secs(t.get("time"))
            if s:
                lap_times.setdefault(t["driverId"], []).append(s)

    winner_laps = _safe_int(res["Results"][0].get("laps"), fallback=50) if (res and res.get("Results")) else 50
    winner_time = _secs(None)
    try:
        winner_time = int(res["Results"][0]["Time"]["millis"]) / 1000
    except (KeyError, TypeError, ValueError):
        winner_time = None

    pits_by_driver: Dict[str, List[int]] = {}
    for p in stops:
        lap_val = _safe_int(p.get("lap"), fallback=1)
        pits_by_driver.setdefault(p["driverId"], []).append(lap_val)

    drivers = []
    for idx, r in enumerate(res.get("Results", [])):
        did = r["Driver"]["driverId"]
        pos = _safe_int(r.get("position"), fallback=idx + 1)
        grid = _safe_int(r.get("grid"), fallback=pos)
        n = _safe_int(r.get("laps"), fallback=0)
        lt = lap_times.get(did, [])[:n]
        synthetic = False
        if len(lt) < n or n == 0:
            # Fallback: model race progression starting from authentic grid position
            synthetic = True
            base = (winner_time / winner_laps) if (winner_time and winner_laps > 0) else 90.0
            total = None
            try:
                total = int(r["Time"]["millis"]) / 1000
            except (KeyError, TypeError, ValueError):
                pass
            
            is_finisher = r.get("status", "").startswith(("Finished", "Lapped")) or str(r.get("status", "")).startswith("+")
            # For retirees, 'pos' is merely the post-race DNF classification (e.g. 20, 21).
            # Their racing pace during active laps reflects their starting grid / racing group, not retirement rank.
            target_pos = pos if is_finisher else grid
            
            lt = []
            for lap_idx in range(n):
                # Transition smoothly from grid position to target racing position
                frac = min(1.0, lap_idx / max(1, min(10, n - 1)))
                lap_pos = grid + frac * (target_pos - grid)
                lap_time = (total / n) if (total and n > 0 and is_finisher) else base * (1 + 0.004 * lap_pos)
                lt.append(round(lap_time, 3))
        cum, acc = [], 0.0
        for s in lt:
            acc += s
            cum.append(round(acc, 3))
        drivers.append({
            "id": did,
            "number": _safe_int(r.get("number"), fallback=0),
            "code": r["Driver"].get("code", r["Driver"]["familyName"][:3].upper()),
            "name": f'{r["Driver"]["givenName"]} {r["Driver"]["familyName"]}',
            "team": r["Constructor"]["name"],
            "team_id": r["Constructor"]["constructorId"],
            "color": TEAM_COLOURS.get(r["Constructor"]["constructorId"], "#FFFFFF"),
            "grid": grid,
            "finish": pos,
            "status": r.get("status", "Finished"),
            "classified_text": r.get("positionText") or str(pos),
            "points": _safe_float(r.get("points"), fallback=0.0),
            "laps": n,
            "cum": cum,
            "pits": sorted(pits_by_driver.get(did, [])),
            "synthetic": synthetic,
        })

    # Derive neutralised laps (likely SC/VSC/red flag) from the FIELD's median lap time per lap
    events = list(CURATED_EVENTS.get((year, rnd), []))
    if lap_rows:
        field_med = []
        for lap in lap_rows:
            ts = [s for s in (_secs(t.get("time")) for t in lap["Timings"]) if s]
            field_med.append(statistics.median(ts) if ts else None)
        valid = [m for m in field_med[1:] if m]
        base = statistics.median(valid) if valid else None
        curated_laps = {e["lap"] for e in events}
        if base:
            i = 1
            while i < len(field_med):
                if field_med[i] and field_med[i] > base * 1.15:
                    start = i
                    while i < len(field_med) and field_med[i] and field_med[i] > base * 1.15:
                        i += 1
                    if not any(abs(c - (start + 1)) <= 1 for c in curated_laps):
                        events.append({
                            "lap": start + 1, "end_lap": i, "type": "NEUTRALISED",
                            "message": f"Neutralised pace L{start + 1}–{i} (likely SC / VSC)",
                            "consequence": f"Field median lap +{round(field_med[start] - base, 1)}s vs race median — derived from timing data.",
                        })
                i += 1
    # Compute retirements: leader's race lap at time of exit + exact track progress
    leader_cum = drivers[0]["cum"] if drivers else []
    for d in drivers:
        if not d["status"].startswith(("Finished", "Lapped")) and not d["status"].startswith("+"):
            curated_re = next((e for e in CURATED_EVENTS.get((year, rnd), [])
                               if (e.get("driverId") == d["id"] or e.get("driver_code") == d["code"] or f"{d['code']} OUT" in e.get("message", ""))
                               and (e.get("type") in ("RETIREMENT", "VSC", "SAFETY_CAR", "FLAG") or "OUT" in e.get("message", ""))), None)
            if curated_re:
                retire_race_lap = curated_re["lap"]
                retire_msg = curated_re["message"]
                retire_con = curated_re.get("consequence", "")
            else:
                st = d.get("status", "Retired")
                cause_label = st
                st_low = st.lower()
                if any(w in st_low for w in ["collision", "accident", "crash"]):
                    cause_label = f"{st} (Track incident)"
                elif any(w in st_low for w in ["engine", "power unit", "gearbox", "transmission", "suspension"]):
                    cause_label = f"{st} failure"
                elif "brakes" in st_low:
                    cause_label = "Brake failure"
                elif "hydraulics" in st_low:
                    cause_label = "Hydraulic pressure loss"
                elif "electrical" in st_low:
                    cause_label = "Electrical failure"
                elif "water" in st_low:
                    cause_label = "Water pressure loss"
                elif "spins" in st_low or "spun" in st_low:
                    cause_label = "Spun off track"
                retire_msg = f'{d["code"]} OUT — {cause_label}'
                # When no curated event, retirement lap is laps completed + 1
                retire_race_lap = max(1, d["laps"] + 1 if d["laps"] > 0 else 1)
                retire_con = f"Race classification: {st}. Completed {max(0, retire_race_lap - 1)} laps."

            # Determine completed full laps vs retirement lap
            # If the driver's recorded laps >= retire_race_lap, they retired DURING retire_race_lap,
            # so completed full laps is retire_race_lap - 1.
            n_raw = d["laps"]
            if n_raw >= retire_race_lap:
                comp_laps = max(0, retire_race_lap - 1)
            else:
                comp_laps = n_raw

            # Synchronize driver's cumulative lap timing to strictly completed laps
            if d.get("cum") and len(d["cum"]) > comp_laps:
                d["cum"] = d["cum"][:comp_laps]
            d["laps"] = comp_laps
            d["completed_laps"] = comp_laps

            # Determine track fraction 'pct' where retirement occurred
            pct = 0.45
            full_txt = f"{retire_msg} {retire_con}"
            turn_match = re.search(r'Turn\s+(\d+)', full_txt, re.IGNORECASE)
            if turn_match and geo and geo.get("turns"):
                t_num = int(turn_match.group(1))
                t_obj = next((t for t in geo["turns"] if t.get("number") == t_num), None)
                if t_obj:
                    pct = t_obj.get("pct", 0.45)
                elif t_num == 1:
                    pct = 0.08
                else:
                    pct = min(0.95, max(0.05, t_num / max(1, len(geo.get("turns", [15])))))
            elif re.search(r'Sector\s+1', full_txt, re.IGNORECASE):
                pct = 0.15
            elif re.search(r'Sector\s+2', full_txt, re.IGNORECASE):
                pct = 0.50
            elif re.search(r'Sector\s+3', full_txt, re.IGNORECASE):
                pct = 0.82
            elif re.search(r'Pit', full_txt, re.IGNORECASE):
                pct = 0.98

            # Calculate retirement time 't_ret' and track progress
            if comp_laps > 0 and d.get("cum"):
                last_c = d["cum"][-1]
                avg_s = last_c / comp_laps
                t_ret = last_c + pct * avg_s
            else:
                avg_lead = leader_cum[0] if leader_cum else 90.0
                t_ret = max(5.0, pct * avg_lead)

            # Ensure t_ret occurs squarely during leader's retire_race_lap so race display and events remain 100% synchronized
            if leader_cum:
                idx_start = retire_race_lap - 2
                idx_end = retire_race_lap - 1
                t_lead_start = leader_cum[idx_start] if (retire_race_lap > 1 and idx_start < len(leader_cum)) else 0.0
                t_lead_end = leader_cum[idx_end] if idx_end < len(leader_cum) else (leader_cum[-1] if leader_cum else 90.0 * retire_race_lap)
                
                # If t_ret drifted outside the race lap window, clamp smoothly within the leader's lap window
                if t_ret < t_lead_start:
                    t_ret = t_lead_start + max(0.05, pct) * (t_lead_end - t_lead_start)
                elif t_ret > t_lead_end:
                    t_ret = t_lead_end - max(0.02, (1.0 - pct)) * (t_lead_end - t_lead_start)

            retire_prog = round(comp_laps + pct, 3)
            d["retire_lap"] = retire_race_lap
            d["retire_time"] = round(t_ret, 3)
            d["retire_prog"] = retire_prog
            d["retire_reason"] = retire_msg

            if not any(e.get("driver_code") == d["code"] for e in events if e.get("type") == "RETIREMENT"):
                events.append({
                    "lap": retire_race_lap,
                    "type": "RETIREMENT",
                    "driverId": d["id"],
                    "driver_code": d["code"],
                    "message": retire_msg,
                    "consequence": retire_con
                })
    events.sort(key=lambda e: e["lap"])

    fl = None
    for r in res.get("Results", []):
        fl_data = r.get("FastestLap")
        if isinstance(fl_data, dict):
            rank = str(fl_data.get("rank", ""))
            time_val = fl_data.get("Time", {}).get("time") if isinstance(fl_data.get("Time"), dict) else None
            if (rank == "1" or not fl) and time_val:
                fl = {
                    "code": r["Driver"].get("code", r["Driver"].get("familyName", "FL")[:3].upper()),
                    "lap": _safe_int(fl_data.get("lap"), fallback=1),
                    "time": time_val
                }

    cname = geo["name"] if geo else res.get("Circuit", {}).get("circuitName", cid.replace("_", " ").title())
    loc = res.get("Circuit", {}).get("Location", {}).get("locality", "")
    country = geo.get("country", "") if geo else res.get("Circuit", {}).get("Location", {}).get("country", "")
    _reloc = EVENT_RELOCATIONS.get((year, rnd))
    if _reloc:
        cname, loc, country = _reloc["circuit_name"], _reloc["locality"], _reloc["country"]
    meta_dict = {
        "year": year, "round": rnd, "race_name": re.sub(r'^\d{4}\s+', '', res.get("raceName", f"Round {rnd}")), "date": res.get("date", ""),
        "circuit_id": cid, "circuit_name": cname,
        "locality": loc, "country": country,
        "total_laps": max(1, winner_laps), "has_lap_data": bool(lap_rows), "fastest_lap": fl,
        "session_type": "race",
        "session_name": "Grand Prix Race",
        "source": "Jolpica-F1 (lap timing) + bacinger/f1-circuits (geometry)",
    }

    return {
        "meta": meta_dict,
        "track": geo,
        "drivers": drivers,
        "events": events,
    }


def build_replay(year: int, rnd: int, session_type: str = "race", net: bool = True, circuit_override: Optional[str] = None) -> Optional[Dict[str, Any]]:
    st = (session_type or "race").lower()
    try:
        if st == "qualifying":
            rep = _build_qualifying_replay(year, rnd, net=net, circuit_override=circuit_override)
            if rep:
                return rep
        elif st in ("sprint_qualifying", "sprint_shootout", "sq"):
            rep = _build_qualifying_replay(year, rnd, net=net, circuit_override=circuit_override, sprint=True)
            if rep:
                return rep
        elif st == "sprint":
            rep = _build_sprint_replay(year, rnd, net=net, circuit_override=circuit_override)
            if rep:
                return rep
        return _build_race_replay(year, rnd, net=net, circuit_override=circuit_override)
    except Exception as e:
        logger.error(f"❌ Error building replay for {year} R{rnd} ({session_type}): {e}", exc_info=True)
        if st in ("qualifying", "sprint"):
            try:
                logger.info(f"🔄 Attempting fallback to race replay for {year} R{rnd}")
                return _build_race_replay(year, rnd, net=net, circuit_override=circuit_override)
            except Exception as e2:
                logger.error(f"❌ Fallback to race replay failed for {year} R{rnd}: {e2}", exc_info=True)
        return None

