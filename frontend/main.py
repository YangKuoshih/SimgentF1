"""
SimGent - FastAPI Server & Agentic Telemetry Proxy
Exposes REST endpoints for the multi-circuit replay player, Race Control events,
WDC/WCC Championship standings, Technical Regulations Era comparisons,
and proxies natural language requests to the AI agent engine.
"""

import datetime
import ipaddress
import json
import re
import secrets
import logging
import os
import sys
import time
from typing import Dict, Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("simgent.api")

from fastapi import FastAPI, Query, HTTPException, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from app.tools import race_replay, race_agent
from app.tools.agent_memory import memory_manager
from app.tools.llm_router import LLMRouter
from app.tools.guardrails import (
    sanitize_input,
    check_prompt_injection,
    check_dangerous_content,
    sanitize_a2ui_card,
    rate_limiter,
    evaluate_all_guardrails,
)

llm_router = LLMRouter()

from app.tools.f1_telemetry import (
    get_seasons,
    get_season_races,
    get_session_drivers,
    generate_circuit_spline,
    get_replay_frame,
    get_telemetry_trace,
    simulate_undercut,
    get_race_control,
    STANDINGS_2024,
    STANDINGS_2026,
    F1_REGULATIONS_ERAS,
    TRACK_BLUEPRINTS
)
from app.tools.strategy_simulator import simulate_what_if_battle, get_what_if_presets

app = FastAPI(title="SimGent · Simulator Agent", version="4.2.0")

# ------------------------------------------------------------------ client identity
# Cloud Run's front end appends the connecting IP as the RIGHTMOST X-Forwarded-For entry;
# anything to its left is client-supplied and can be forged. Behind Cloudflare the connecting
# IP is a Cloudflare edge, and Cloudflare sets CF-Connecting-IP to the real visitor.
# Ranges: https://www.cloudflare.com/ips-v4 and /ips-v6 (October 2026).
_CLOUDFLARE_NETS = [ipaddress.ip_network(n) for n in (
    "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22", "141.101.64.0/18",
    "108.162.192.0/18", "190.93.240.0/20", "188.114.96.0/20", "197.234.240.0/22", "198.41.128.0/17",
    "162.158.0.0/15", "104.16.0.0/13", "104.24.0.0/14", "172.64.0.0/13", "131.0.72.0/22",
    "2400:cb00::/32", "2606:4700::/32", "2803:f800::/32", "2405:b500::/32", "2405:8100::/32",
    "2a06:98c0::/29", "2c0f:f248::/32")]


def _client_ip(request: Request) -> str:
    """Client IP for rate limiting that a caller cannot choose."""
    xff = request.headers.getlist("x-forwarded-for") if hasattr(request.headers, "getlist") else [request.headers.get("x-forwarded-for", "")]
    hops = [h.strip() for h in ",".join(x for x in xff if x).split(",") if h.strip()]
    peer = hops[-1] if hops else (request.client.host if request.client else "127.0.0.1")
    try:
        peer_ip = ipaddress.ip_address(peer)
    except ValueError:
        return peer
    if any(peer_ip in net for net in _CLOUDFLARE_NETS):
        cf = (request.headers.get("cf-connecting-ip") or "").strip()
        try:
            return str(ipaddress.ip_address(cf))
        except ValueError:
            pass
    return str(peer_ip)


# ------------------------------------------------------------------ security headers
# Inline scripts/handlers and Tailwind's browser build need 'unsafe-inline'; the policy still
# blocks scripts from other sites, sending data to other origins, plugins and framing.
# Cloudflare (already in front of every request) injects its Web Analytics beacon.
_CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com "
        "https://static.cloudflareinsights.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self' https://cloudflareinsights.com; object-src 'none'; "
        "base-uri 'self'; form-action 'self'; frame-ancestors 'none'")
_SECURITY_HEADERS = {
    "Content-Security-Policy": _CSP,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Cross-Origin-Opener-Policy": "same-origin",
}


@app.middleware("http")
async def _security_headers(request: Request, call_next):
    response = await call_next(request)
    for k, v in _SECURITY_HEADERS.items():
        response.headers.setdefault(k, v)
    # Pages must be re-checked on every visit, or browsers keep showing the pre-deploy app
    # (no Cache-Control lets them reuse it heuristically). Unchanged pages cost a 304.
    if response.headers.get("content-type", "").startswith("text/html"):
        response.headers.setdefault("Cache-Control", "no-cache")
    return response

def require_admin(request: Request):
    """Admin routes fail closed unless an operator configures a bearer token."""
    token = os.environ.get("SIMGENT_ADMIN_TOKEN", "")
    if not token:
        raise HTTPException(status_code=503, detail="Admin API is disabled")
    authorization = request.headers.get("Authorization", "")
    if not secrets.compare_digest(authorization.encode(), ("Bearer " + token).encode()):
        raise HTTPException(status_code=401, detail="Admin authentication required",
                            headers={"WWW-Authenticate": "Bearer"})


STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)

# -------------------------------------------------------------
# Data API Endpoints
# -------------------------------------------------------------

HISTORIC_SEASON_HIGHLIGHTS = {
    2026: "Active Aero & 50/50 Hybrid (Current)",
    2025: "Ground Effect Finale",
    2024: "Verstappen 4th Title · McLaren WCC",
    2023: "Red Bull 21-Win Sweep",
    2022: "Ground Effect Era Intro",
    2021: "Verstappen vs Hamilton Title Duel",
    2020: "Hamilton 7th World Title",
    2016: "Rosberg World Championship",
    2014: "V6 Turbo-Hybrid Dawn",
    2012: "7 Different Winners in 7 Races",
    2010: "4-Way Abu Dhabi Title Fight",
    2008: "Hamilton Maiden Crown (Interlagos)",
    2007: "Räikkönen 1-Point Miracle",
    2004: "Schumacher 13 Wins V10 Apex",
    1998: "Häkkinen vs Schumacher (Spa)",
    1994: "Schumacher Adelaide Title",
    1991: "Senna Triple World Champion",
    1988: "Senna vs Prost McLaren 15/16",
    1976: "Hunt vs Lauda (Rush)",
    1950: "Inaugural World Championship",
}

@app.get("/api/seasons")
async def api_seasons():
    seasons = []
    for y in range(datetime.date.today().year, 1949, -1):
        lbl = HISTORIC_SEASON_HIGHLIGHTS.get(y)
        seasons.append({
            "year": y,
            "label": f"{y} · {lbl}" if lbl else f"{y} Season",
            "highlight": y in HISTORIC_SEASON_HIGHLIGHTS
        })
    return seasons

@app.get("/api/races")
async def api_races(year: int = Query(2026)):
    year = int(year)
    return get_season_races(year)

@app.get("/api/drivers")
async def api_drivers(session_key: int = Query(9558)):
    return get_session_drivers(session_key)

@app.get("/api/circuit")
async def api_circuit(circuit_key: str = Query("silverstone")):
    blueprint = TRACK_BLUEPRINTS.get(circuit_key.lower(), TRACK_BLUEPRINTS["silverstone"])
    spline = generate_circuit_spline(circuit_key.lower())
    return {
        "metadata": blueprint,
        "spline": spline
    }

@app.get("/api/race_control")
async def api_race_control(session_key: int = Query(9558)):
    return get_race_control(session_key)

@app.get("/api/standings")
async def api_standings(year: int = Query(2026)):
    year = int(year)
    data = race_replay.standings(year)
    if data["drivers"]:
        return data
    return STANDINGS_2024 if year == 2024 else {"year": year, "source": "unavailable", "drivers": [], "constructors": []}

@app.get("/api/latest_race")
async def api_latest_race():
    """The newest data on the calendar: a race weekend under way (opened on its newest
    session with results) or else the most recent completed Grand Prix."""
    this_year = datetime.date.today().year
    for y in range(this_year, this_year - 3, -1):
        races = race_replay.season_races(y)
        completed = [r for r in races if r.get("completed")]
        live = [r for r in races if r.get("in_progress")]
        if live and (not completed or live[-1]["round"] > completed[-1]["round"]):
            latest = live[-1]
            session = [s for s in race_replay.WEEKEND_ORDER if s in latest["available"]][-1]
        elif completed:
            latest, session = completed[-1], "race"
        else:
            continue
        return {
            "year": y,
            "round": latest["round"],
            "session": session,
            "race_name": latest["race_name"],
            "circuit_id": latest.get("circuit_id"),
            "date": latest.get("date"),
        }
    return {"year": 2026, "round": 16, "race_name": "Bahrain Grand Prix", "circuit_id": "bahrain"}

@app.get("/api/season")
async def api_season(year: int = Query(2026)):
    """Real calendar for a season, flagged with which rounds are replayable."""
    year = int(year)
    return race_replay.season_races(year)

@app.get("/api/health")
async def api_health():
    """Diagnostic health check verifying cache files and server readiness."""
    cache_dir = os.path.join(PROJECT_ROOT, "data", "cache", "jolpica")
    cached_count = len(os.listdir(cache_dir)) if os.path.exists(cache_dir) else 0
    return {
        "status": "healthy",
        "cache_files_present": cached_count,
        "environment": os.environ.get("K_SERVICE", "local"),
        "timestamp": time.time(),
    }

@app.get("/api/replay_model")
async def api_replay_model(
    year: int = Query(2026),
    round: int = Query(1),
    session: str = Query("race"),
    circuit: Optional[str] = Query(None, max_length=64, pattern=r"^[a-z0-9_]+$")
):
    year = int(year)
    round = int(round)
    start_time = time.time()
    cid = circuit if isinstance(circuit, str) else None
    if session not in {"race", "qualifying", "sprint", "sprint_qualifying"}:
        raise HTTPException(status_code=422, detail="Unsupported session")
    logger.info("Replay model requested")
    try:
        model = race_replay.build_replay(year, round, session_type=session, circuit_override=cid)
    except Exception as e:
        logger.error("Replay model generation failed")
        try:
            logger.info("Trying race replay fallback")
            model = race_replay.build_replay(year, round, session_type="race", circuit_override=cid)
        except Exception:
            model = None

    elapsed_ms = (time.time() - start_time) * 1000
    if model is None:
        logger.warning("Replay data unavailable")
        raise HTTPException(status_code=404, detail="Telemetry archives for this session are not yet loaded.")

    driver_count = len(model.get("drivers", []))
    track_name = model.get("meta", {}).get("race_name", "Unknown Track")
    logger.info("Replay model served")
    return model

@app.get("/api/llm/status")
async def api_llm_status():
    """Returns status of the multi-provider router."""
    return llm_router.get_provider_status()

@app.get("/api/regulations")
async def api_regulations():
    return F1_REGULATIONS_ERAS

@app.get("/api/eval", dependencies=[Depends(require_admin)])
async def api_eval(
    year: int = Query(2026),
    round: int = Query(16),
    circuit: str = Query("bahrain"),
    remediate: bool = Query(False),
    offline: bool = Query(True)
):
    """
    Executes the 7-pillar offline data evaluation suite across static cache, timing tower,
    starting grids, replay physics, circuit geometry, driver registry, and Pit Wall agent factuality.
    """
    year = int(year)
    round = int(round)
    from app.tools.offline_eval import OfflineDataEval
    eval_suite = OfflineDataEval(offline=offline, remediate_on_failure=remediate)
    return eval_suite.run_full_eval(year=year, round_num=round, circuit_id=circuit)


@app.post("/api/eval/remediate", dependencies=[Depends(require_admin)])
async def api_eval_remediate(
    year: int = Query(2026),
    round: int = Query(16),
    circuit: str = Query("bahrain")
):
    """
    Triggers the autonomous remediation agent to repair and heal any data or memory discrepancies.
    """
    year = int(year)
    round = int(round)
    from app.tools.offline_eval import OfflineDataEval
    eval_suite = OfflineDataEval(offline=True, remediate_on_failure=True)
    return eval_suite.run_full_eval(year=year, round_num=round, circuit_id=circuit)



@app.get("/api/replay")
async def api_replay(
    progress: float = Query(0.65, ge=0.0, le=1.0),
    circuit_key: str = Query("silverstone"),
    session_key: int = Query(9558)
):
    cars = get_replay_frame(lap_progress=progress, circuit_key=circuit_key, session_key=session_key)
    return {
        "progress": progress,
        "circuit": circuit_key,
        "session_key": session_key,
        "cars": cars
    }

@app.get("/api/telemetry")
async def api_telemetry(driver_1: int = Query(1), driver_2: int = Query(4)):
    return get_telemetry_trace(driver_1=driver_1, driver_2=driver_2)

# Bounds keep one request from monopolising the single Cloud Run instance (real races are
# <= 200 laps; the UI uses a few hundred iterations at most).
class SimulationRequest(BaseModel):
    pit_lap: int = Field(35, ge=0, le=200)
    target_compound: str = Field("H", max_length=16)
    disruption: str = Field("Normal", max_length=32)
    target_driver: Optional[str] = Field(None, max_length=64)
    rival_driver: Optional[str] = Field(None, max_length=64)
    circuit_name: Optional[str] = Field(None, max_length=64)
    total_laps: Optional[int] = Field(None, ge=1, le=200)

@app.post("/api/simulate")
async def api_simulate(req: SimulationRequest):
    return simulate_undercut(
        pit_lap=req.pit_lap,
        target_compound=req.target_compound,
        disruption=req.disruption,
        target_driver=req.target_driver,
        rival_driver=req.rival_driver,
        circuit_name=req.circuit_name,
        total_laps=req.total_laps
    )

class WhatIfRequest(BaseModel):
    circuit_key: str = Field("bahrain", max_length=64)
    total_laps: Optional[int] = Field(None, ge=1, le=200)
    driver_1: Optional[Dict[str, Any]] = None
    driver_2: Optional[Dict[str, Any]] = None
    sc_lap: int = Field(0, ge=0, le=200)
    iterations: int = Field(200, ge=1, le=1000)

    @field_validator("driver_1", "driver_2")
    @classmethod
    def _bounded_driver(cls, v):
        if v is not None:
            if len(json.dumps(v, default=str)) > 4000:
                raise ValueError("driver strategy too large")
            if len(v.get("stints") or []) > 10:
                raise ValueError("at most 10 stints")
        return v

@app.get("/api/strategy/what_if/presets")
async def api_what_if_presets():
    """Returns curated iconic historical What-If tactical race scenarios."""
    return get_what_if_presets()

@app.post("/api/strategy/what_if")
async def api_what_if(req: WhatIfRequest):
    """Executes full-distance What-If race battle simulation between two strategies."""
    return simulate_what_if_battle(
        circuit_key=req.circuit_key,
        total_laps=req.total_laps,
        driver_1=req.driver_1,
        driver_2=req.driver_2,
        sc_lap=req.sc_lap,
        iterations=req.iterations
    )

class ChatMessage(BaseModel):
    query: str = Field(..., max_length=500, description="Natural language telemetry or race query (max 500 chars)")
    context: Optional[Dict[str, Any]] = None
    history: Optional[list] = Field(None, max_length=50, description="Recent conversation turns for multi-turn conversational context")

    @field_validator("context")
    @classmethod
    def _bounded_context(cls, v):
        # The app sends a few hundred bytes (race, session, top-10 order); refuse anything far larger.
        if v is not None and len(json.dumps(v, default=str)) > 4000:
            raise ValueError("context too large")
        return v

@app.post("/api/chat")
async def api_chat(msg: ChatMessage, request: Request):
    client_ip = _client_ip(request)
    # Separate rate buckets per test client exist only in test runs (CI's browser suite);
    # in production the header would let anyone mint fresh buckets.
    test_hdr = request.headers.get("x-test-client") if os.environ.get("SIMGENT_TRUST_TEST_CLIENT_HEADER") == "1" else None
    rate_key = f"{client_ip}:{test_hdr}" if test_hdr else client_ip
    if not rate_limiter.is_allowed(rate_key):
        raise HTTPException(
            status_code=429,
            detail="Pit Wall Radio rate limit exceeded (max 60 queries/min). Please wait a moment."
        )

    # 1. Sanitize user input & strip non-printable characters
    clean_query = sanitize_input(msg.query, max_chars=500)
    if not clean_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    # 2. Check all security, safety, domain, and data scope guardrails
    blocked, guardrail_resp = evaluate_all_guardrails(clean_query, msg.context)
    if blocked and guardrail_resp:
        return guardrail_resp

    # Sanitize and bound multi-turn conversation history (prevent token stuffing and injection smuggling)
    safe_history = []
    if msg.history and isinstance(msg.history, list):
        for turn in msg.history[-10:]:
            if isinstance(turn, dict):
                r = "user" if turn.get("role") == "user" else "assistant"
                c = sanitize_input(str(turn.get("content") or turn.get("text") or ""), max_chars=1000)
                is_inj, _ = check_prompt_injection(c)
                is_dang, _ = check_dangerous_content(c)
                if not is_inj and not is_dang and c:
                    entry = {"role": r, "content": c}
                    view = turn.get("view")
                    if isinstance(view, str) and re.fullmatch(r"\d{4}-\d{1,2}", view):
                        entry["view"] = view  # race on screen when the turn happened
                    safe_history.append(entry)

    # Only turns asked while the current race was on screen count as context.
    safe_history = race_agent.scope_history_to_view(safe_history, msg.context)

    start_t = time.perf_counter()

    # 0. Check Grounded RAG Memory Subsystem (Ground Truth & Verified Feedback)
    # Turn context-dependent follow-ups ("what about 2025?", "which lap was that on?")
    # into self-contained questions before any lookup, so memory, the LLM and the engine
    # all answer the question the user actually meant.
    resolved_query = race_agent.resolve_follow_up(clean_query, safe_history)

    # Result/standings questions skip stored memory so the official data always wins.
    mem_resp = memory_manager.retrieve(resolved_query, msg.context, history=safe_history, defer_to_data=True)
    if mem_resp:
        latency = round((time.perf_counter() - start_t) * 1000, 2)
        mem_resp["latency_ms"] = latency
        mem_resp["query"] = clean_query
        mem_resp["context_received"] = msg.context or {}
        mem_resp["cost"] = "Curated memory lookup (no external model call)"
        mem_resp["tokens_billed"] = 0
        if "tier" not in mem_resp:
            mem_resp["tier"] = "Verified Memory Bank"
        if mem_resp.get("a2ui_card"):
            mem_resp["a2ui_card"] = sanitize_a2ui_card(mem_resp["a2ui_card"])
        return mem_resp

    # Optional model provider query (provider-specific pricing and quotas)
    llm_resp = llm_router.query(resolved_query, msg.context, history=safe_history)
    if llm_resp:
        latency = round((time.perf_counter() - start_t) * 1000, 2)
        llm_resp["latency_ms"] = latency
        llm_resp["query"] = clean_query
        llm_resp["context_received"] = msg.context or {}
        llm_resp["cost"] = "Telemetry Feed Active"
        llm_resp["tokens_billed"] = 0
        if "tier" not in llm_resp:
            llm_resp["tier"] = "External LLM Copilot"
        if llm_resp.get("a2ui_card"):
            llm_resp["a2ui_card"] = sanitize_a2ui_card(llm_resp["a2ui_card"])
        return llm_resp

    # Fallback to the deterministic telemetry engine (no external model call)
    resp = race_agent.answer_race_engineer_query(resolved_query, msg.context, history=safe_history)
    latency = round((time.perf_counter() - start_t) * 1000, 2)
    resp["latency_ms"] = latency
    resp["provider"] = "Pit Wall Telemetry Engine"
    resp["tier"] = "Local In-Memory Transponder"
    resp["cost"] = "Telemetry Feed Active"
    resp["tokens_billed"] = 0
    resp["query"] = clean_query
    resp["context_received"] = msg.context or {}
    if resp.get("a2ui_card"):
        resp["a2ui_card"] = sanitize_a2ui_card(resp["a2ui_card"])
    return resp


class FeedbackRequest(BaseModel):
    query: str = Field(..., max_length=500, description="The user query that generated the response")
    response_text: str = Field(..., max_length=5000, description="The assistant response text")
    rating: str = Field(..., description="User rating: 'up' or 'down'")
    comment: Optional[str] = Field(None, max_length=2000, description="Optional user correction or explanation")
    context: Optional[Dict[str, Any]] = None


@app.post("/api/feedback")
async def api_feedback(req: FeedbackRequest, request: Request):
    if not rate_limiter.is_allowed(_client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many feedback submissions. Please wait a moment.")
    clean_query = sanitize_input(req.query, max_chars=500)
    clean_comment = sanitize_input(req.comment or "", max_chars=2000) if req.comment else None
    res = memory_manager.record_feedback(
        query=clean_query,
        response_text=req.response_text,
        rating=req.rating,
        comment=clean_comment,
        context=req.context
    )
    return res


@app.get("/api/memory/stats")
async def api_memory_stats():
    from app.tools.agent_memory import DEFAULT_MEMORIES
    return {"status": "success", "stats": memory_manager.get_stats(),
            "memories": DEFAULT_MEMORIES}


@app.get("/api/memory", dependencies=[Depends(require_admin)])
async def api_memory():
    return {
        "status": "success",
        "memories": memory_manager.load_memories(),
        "stats": memory_manager.get_stats(),
        "recent_feedback": memory_manager.load_feedback()[-20:]
    }


@app.post("/api/memory/review", dependencies=[Depends(require_admin)])
async def api_memory_review():
    review_res = memory_manager.review_all_pending_feedback()
    return {
        "status": "success",
        "review_results": review_res,
        "stats": memory_manager.get_stats()
    }


# Mount static directory

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon_ico():
    ico_path = os.path.join(STATIC_DIR, "favicon.ico")
    if os.path.exists(ico_path):
        return FileResponse(ico_path, media_type="image/x-icon")
    raise HTTPException(status_code=404)

@app.get("/favicon.svg", include_in_schema=False)
async def favicon_svg():
    svg_path = os.path.join(STATIC_DIR, "favicon.svg")
    if os.path.exists(svg_path):
        return FileResponse(svg_path, media_type="image/svg+xml")
    raise HTTPException(status_code=404)

@app.get("/apple-touch-icon.png", include_in_schema=False)
async def apple_touch_icon():
    icon_path = os.path.join(STATIC_DIR, "apple-touch-icon.png")
    if os.path.exists(icon_path):
        return FileResponse(icon_path, media_type="image/png")
    raise HTTPException(status_code=404)

@app.get("/")
async def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "SimGent API Ready."}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    is_prod = os.environ.get("ENV") == "production"
    uvicorn.run("frontend.main:app", host="0.0.0.0", port=port, reload=not is_prod)
