"""
F1 Simgent - Security & Agent Guardrails
Provides input sanitization, prompt injection detection, rate limiting,
schema enforcement, and output safety for the Pit Wall AI Agent.
"""

import re
import html
import time
from collections import defaultdict, deque
from typing import Dict, Any, Optional, Tuple


# 1. PROMPT INJECTION & JAILBREAK PATTERNS
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"(?i)\b(ignore|disregard|forget|override)\s+(all\s+)?(previous|prior|above|system)\s+(instructions|prompts|rules|commands|directives)\b"),
    re.compile(r"(?i)\b(reveal|display|output|show|print|leak)\s+(the\s+)?(system\s+prompt|initial\s+prompt|developer\s+mode|secrets?|[a-z0-9_]*api[_\s-]?keys?|instructions)\b"),
    re.compile(r"(?i)\b(you\s+are\s+now|act\s+as|pretend\s+to\s+be)\s+(DAN|unrestricted|developer\s+mode|jailbroken|god\s+mode)\b"),
    re.compile(r"(?i)\b(jailbreak|bypass\s+safety|disable\s+guardrails|unfiltered\s+mode)\b"),
    re.compile(r"(?i)<\s*(script|iframe|object|embed|style)\b"),
    re.compile(r"(?i)\b(javascript:|vbscript:|data:text\/html)"),
]

SAFE_REFUSAL_MESSAGE = (
    "🛡️ **Pit Wall Security Guardrail**\n\n"
    "• **Radio Link Protected**: Transponder frequencies are secured against prompt injection, jailbreaking, and unauthorized command overrides.\n"
    "• Zero system instructions, secrets, or API keys are disclosed.\n"
    "• Telemetry link re-centered on Grand Prix pit wall operations."
)


# 2. DANGEROUS & HARMFUL CONTENT PATTERNS
DANGEROUS_CONTENT_PATTERNS = [
    re.compile(r"(?i)\b(how\s+to\s+(make|build|create|manufacture|assemble|construct)|synthesize|produce)\s+(an?\s+)?(weapons?|bombs?|explosives?|explosive\s+devices?|firearms?|guns?|grenades?|missiles?|ieds?|landmines?|ammunitions?|bullets?|poisons?|cyanide|ricin|anthrax)\b"),
    # Broadened: catch build/make-a-weapon phrasings regardless of the "how to" prefix
    re.compile(r"(?i)\b(make|making|build|building|create|creating|construct|constructing|assemble|assembling|manufacture|synthesi[sz]e|produce|detonate|set\s+off)\b[\w\s]{0,25}\b(bombs?|explosives?|explosive\s+devices?|ieds?|grenades?|dirty\s+bomb|pipe\s+bomb|molotov|nerve\s+agent|sarin|chemical\s+weapons?|biological\s+weapons?|anthrax|ricin|poison\s+gas)\b"),
    re.compile(r"(?i)\b(how\s+to\s+manufacture\s+firearms)\b"),
    re.compile(r"(?i)\b(make|building|create|creating|synthesizing)\s+(an?\s+)?(dirty\s+bomb|pipe\s+bomb|molotov|car\s+bomb|biological\s+weapon|chemical\s+weapon)\b"),
    re.compile(r"(?i)\b(assassinate|murder|kill|torture|shoot\s+up|attack)\s+(someone|people|president|politician|driver|crowd)\b"),
    re.compile(r"(?i)\b(how\s+to\s+(hack|infiltrate|ddos|exploit|crack|steal|keylog)|write\s+(malware|ransomware|keylogger|spyware|trojan|rootkit))\b"),
    re.compile(r"(?i)\b(how\s+to\s+(commit\s+suicide|kill\s+myself|cut\s+myself|hang\s+myself)|suicide\s+methods)\b"),
]

SAFE_DANGEROUS_REFUSAL = (
    "⛔ **Pit Wall Safety Guardrail Notice**\n\n"
    "• **Safety Protocol Active**: Inquiries concerning weapons, explosives, harmful materials, cyberattacks, violence, self-harm, or illicit activities are strictly prohibited.\n"
    "• The Pit Wall Agent operates under strict ethical and safety directives.\n"
    "• Transponder radio link is restricted strictly to competitive motorsport telemetry."
)


# 3. OUT-OF-SCOPE PATTERNS (GENERAL NON-MOTORSPORT TOPICS)
OUT_OF_SCOPE_PATTERNS = [
    # General non-motorsport weather (forecasts for cities outside race context)
    re.compile(r"(?i)\b(what('s|\s+is)\s+the\s+weather|current\s+weather|weather\s+(in|for|tomorrow|today|this\s+week)|forecast\s+for|is\s+it\s+raining\s+(outside|in\s+[a-z]+|today))\b"),
    # Non-motorsport sports
    re.compile(r"(?i)\b(super\s*bowl|nfl|quarterback|touchdown|nba|lebron|lakers|slam\s*dunk|mlb|home\s*run|baseball|premier\s+league|champions\s+league|uefa|fifa|world\s*cup\s*(soccer|football)?|messi|ronaldo|tennis|wimbledon|nadal|djokovic|pga\s+tour|golf|nhl|stanley\s*cup)\b"),
    # General trivia / politics / geography
    re.compile(r"(?i)\b(who\s+is\s+the\s+president\s+of|capital\s+of\s+[a-z]+|who\s+is\s+the\s+prime\s+minister|how\s+tall\s+is\s+mount\s+everest|who\s+wrote\s+[a-z]+|who\s+discovered\s+america)\b"),
    # Creative writing, recipes, homework, generic coding
    re.compile(r"(?i)\b(write\s+(a\s+)?(poem|song|essay|short\s+story|fan\s*fiction)|recipe\s+for|how\s+to\s+bake|homework|calculus|algebra|geometry|math\s+problem|solve\s+(my|this)?\s*(equation|math|calculus|integral)|write\s+a\s+(python|javascript|java|c\+\+)\s+(function|script|code)\s+to\s+(sort|invert|reverse))\b"),
    # Financial / Crypto advice
    re.compile(r"(?i)\b(should\s+i\s+(buy|invest\s+in|sell)\s+(bitcoin|crypto|ethereum|stocks?|shares|doge)|crypto\s+price\s+prediction|stock\s+market\s+advice)\b"),
    # Medical advice
    re.compile(r"(?i)\b(symptoms\s+of\s+(covid|flu|pneumonia|cancer|infection)|how\s+to\s+cure\s+(a\s+headache|flu|cold)|medical\s+diagnosis)\b"),
]

# Words that indicate a race/motorsport context that should OVERRIDE the out-of-scope filter
MOTORSPORT_CONTEXT_OVERRIDE = re.compile(
    r"(?i)\b(f1|formula\s*1|grand\s+prix|gp|race|raced|racing|circuit|track|monaco|silverstone|spa|monza|suzuka|interlagos|bahrain|jeddah|leclerc|verstappen|hamilton|norris|piastri|russell|sainz|alonso|schumacher|schmacur|schumi|senna|prost|lauda|fangio|clark|stewart|mansell|piquet|vettel|raikkonen|hakkinen|hunt|ferrari|red\s*bull|mclaren|mercedes|aston\s*martin|williams|sauber|haas|alpine|rb|vcarb|lap|stint|pit\s*stop|undercut|overcut|tyre|tire|intermediate|full\s*wet|slick|soft|medium|hard|apex|telemetry|pole|qualifying|sprint|points|wdc|wcc|championship|championships|2026\s*regulations|active\s*aero|z-mode|x-mode|drs|mgu-k|mgu-h|power\s*unit|era|eras|career|champion|champions|titles|victories|podiums)\b"
)

SAFE_OUT_OF_SCOPE_REFUSAL = (
    "🏁 **Pit Wall Radio: Out-of-Scope Query**\n\n"
    "I am the **F1 Simgent Pit Wall Race Engineer**, specialized exclusively in Formula 1 telemetry, race physics, pit strategies, championship archives (1950–2026), and technical regulations.\n\n"
    "I cannot assist with general weather, non-motorsport topics, general trivia, or creative writing.\n\n"
    "**Here is what you can ask me across the pit wall:**\n"
    "• **Replay & Telemetry**: *\"What tires did Verstappen run in Bahrain 2026?\"*, *\"Who had the highest apex speed at Turn 4?\"*\n"
    "• **Race Strategy**: *\"Simulate an undercut for Leclerc against Norris\"*, *\"Why did Hamilton retire in Australia 2024?\"*\n"
    "• **Championship Standings**: *\"Who leads the 2026 Drivers Championship?\"*, *\"How many points did McLaren score in 2024?\"*\n"
    "• **2026 Regulations**: *\"How does the 2026 50/50 hybrid power unit work?\"*, *\"Explain Active Aero X-Mode and Z-Mode\"*"
)


# 4. UNSUPPORTED / UNAVAILABLE F1 DATA PATTERNS
UNSUPPORTED_DATA_PATTERNS = [
    # Free practice lap-by-lap replays (explain indexed data scope)
    re.compile(r"(?i)\b(replay|telemetry\s+for|show\s+me)\s+(fp1|fp2|fp3|free\s+practice\s+[123]|practice\s+session\s+[123])\b"),
    re.compile(r"(?i)\b(fp1|fp2|fp3|free\s+practice)\s+(lap\s+times|replay|telemetry|track\s+data)\b"),
    # Pre-1950 Formula 1
    re.compile(r"(?i)\b(18\d\d|19[0-4]\d)\s*(f1|formula\s*1|grand\s+prix|world\s+championship)\b"),
    # Private / Encrypted team radio
    re.compile(r"(?i)\b(listen\s+to|eavesdrop|unfiltered|encrypted|secret|private)\s+(team\s+radio|pit\s+radio|strategy\s+channel|audio\s+feed)\b"),
    # Proprietary engineering CAD / CFD / blueprints
    re.compile(r"(?i)\b(cad\s+drawings?|cad\s+files?|cfd\s+simulations?|wind\s+tunnel\s+data|secret\s+floor\s+blueprint|secret\s+aero\s+file)\b"),
]

SAFE_UNSUPPORTED_DATA_REFUSAL = (
    "📡 **Pit Wall Telemetry: Data Scope Notice**\n\n"
    "The requested data is outside the official open Formula 1 telemetry feed:\n"
    "• **Free Practice (FP1/FP2/FP3)**: Non-competitive practice telemetry is excluded from our 2D replay engine to limit the indexed data scope (only competitive sessions — Grand Prix, Qualifying, and Sprints — are indexed across 76 seasons).\n"
    "• **Private Radio Channels**: Only official FIA Race Control incident logs and TV-broadcast team radio messages are logged; private internal team radio frequencies are encrypted and confidential.\n"
    "• **Historical Horizon**: Official FIA Formula 1 World Championship telemetry covers 1950 through 2026.\n"
    "• **Proprietary Engineering**: Team CAD/CFD files and wind tunnel sensor data are confidential intellectual property of the constructors."
)


def sanitize_input(text: str, max_chars: int = 500) -> str:
    """
    Sanitizes user input: strips null bytes, removes dangerous control characters,
    normalizes whitespace, and truncates to max_chars to prevent token exhaustion.
    """
    if not text:
        return ""
    # Strip null bytes and non-printable control characters (except newline and tab)
    clean = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)
    # Normalize excessive whitespace
    clean = re.sub(r"[ \t]{3,}", "  ", clean).strip()
    return clean[:max_chars]


def check_prompt_injection(query: str) -> Tuple[bool, Optional[str]]:
    """
    Scans the query for known prompt injection, jailbreaking, or XSS vectors.
    Returns (is_injected, refusal_text).
    """
    clean_q = query.strip()
    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern.search(clean_q):
            return True, SAFE_REFUSAL_MESSAGE
    return False, None


def check_dangerous_content(query: str) -> Tuple[bool, Optional[str]]:
    """
    Scans the query for dangerous, harmful, or illicit content.
    Returns (is_dangerous, refusal_text).
    """
    clean_q = query.strip()
    for pattern in DANGEROUS_CONTENT_PATTERNS:
        if pattern.search(clean_q):
            return True, SAFE_DANGEROUS_REFUSAL
    return False, None


def check_out_of_scope(query: str, context: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[str]]:
    """
    Scans the query for general off-topic subjects (weather outside F1, other sports, trivia, homework).
    Checks for motorsport context override so race-relevant questions pass.
    Returns (is_out_of_scope, refusal_text).
    """
    clean_q = query.strip()
    # If the user context already specifies an active race, certain queries may be contextually relevant
    has_race_context = bool(context and (context.get("race") or context.get("round") or context.get("year")))

    for pattern in OUT_OF_SCOPE_PATTERNS:
        if pattern.search(clean_q):
            # Check if motorsport terms or active context override it
            if MOTORSPORT_CONTEXT_OVERRIDE.search(clean_q) or has_race_context and any(w in clean_q.lower() for w in ["rain", "wet", "track", "lap", "temp"]):
                return False, None
            return True, SAFE_OUT_OF_SCOPE_REFUSAL
    return False, None


def check_unsupported_data(query: str) -> Tuple[bool, Optional[str]]:
    """
    Scans for requests regarding unavailable data (FP1/2/3 replays, encrypted team radios, pre-1950 data, CAD files).
    Returns (is_unsupported, refusal_text).
    """
    clean_q = query.strip()
    for pattern in UNSUPPORTED_DATA_PATTERNS:
        if pattern.search(clean_q):
            return True, SAFE_UNSUPPORTED_DATA_REFUSAL
    return False, None


def evaluate_all_guardrails(query: str, context: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Unified evaluator executing all security, safety, domain, and data guardrails in priority order.
    Returns (blocked: bool, guardrail_response: Optional[dict]).
    """
    clean_q = sanitize_input(query, max_chars=500)
    if not clean_q:
        return False, None

    # Priority 1: Dangerous Content (Weapons, Violence, Malware)
    is_danger, danger_msg = check_dangerous_content(clean_q)
    if is_danger:
        return True, {
            "role": "assistant",
            "text": danger_msg,
            "provider": "Pit Wall Safety Guardrail",
            "tier": "Safety Interceptor",
            "tool": "safety_guardrail",
            "intent": "Harmful or Dangerous Content Blocked",
            "cost": "Safety Protocol Active (no external model call)",
            "tokens_billed": 0,
            "latency_ms": 0.2,
            "query": clean_q,
            "context_received": context or {},
            "a2ui_card": None
        }

    # Priority 2: Adversarial Prompt Injection / Jailbreaks
    is_inj, inj_msg = check_prompt_injection(clean_q)
    if is_inj:
        return True, {
            "role": "assistant",
            "text": inj_msg,
            "provider": "Pit Wall Security Guardrail",
            "tier": "Security Interceptor",
            "tool": "security_guardrail",
            "intent": "Adversarial Prompt Injection Blocked",
            "cost": "Local Telemetry Guard (no external model call)",
            "tokens_billed": 0,
            "latency_ms": 0.3,
            "query": clean_q,
            "context_received": context or {},
            "a2ui_card": None
        }

    # Priority 3: Unsupported / Unavailable Data Requests (FP1/2/3 replays, CAD, encrypted radio)
    is_unsupported, unsupp_msg = check_unsupported_data(clean_q)
    if is_unsupported:
        return True, {
            "role": "assistant",
            "text": unsupp_msg,
            "provider": "Pit Wall Telemetry Guardrail",
            "tier": "Data Scope Interceptor",
            "tool": "unsupported_data_notice",
            "intent": "Unavailable Formula 1 Data Limitation",
            "cost": "Telemetry Feed Active (no external model call)",
            "tokens_billed": 0,
            "latency_ms": 0.3,
            "query": clean_q,
            "context_received": context or {},
            "a2ui_card": None
        }

    # Priority 4: Out-of-Scope Non-Motorsport Queries (Weather, other sports, trivia, homework)
    is_oos, oos_msg = check_out_of_scope(clean_q, context)
    if is_oos:
        return True, {
            "role": "assistant",
            "text": oos_msg,
            "provider": "Pit Wall Domain Guardrail",
            "tier": "Domain Interceptor",
            "tool": "out_of_scope_redirect",
            "intent": "Out of Scope Domain Query Redirected",
            "cost": "Domain Filter Active (no external model call)",
            "tokens_billed": 0,
            "latency_ms": 0.3,
            "query": clean_q,
            "context_received": context or {},
            "a2ui_card": None
        }

    return False, None


def sanitize_a2ui_card(card: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Validates and hardens A2UI card schemas before transmitting to client.
    Validates allowed actions and payload fields and escapes displayed text.
    """
    if not card or not isinstance(card, dict):
        return None

    card_type = str(card.get("type", "generic_card"))[:32]
    title = html.escape(str(card.get("title", "Telemetry Card"))[:80])
    action = html.escape(str(card.get("action", ""))[:50]) if card.get("action") else None

    # Sanitize metrics list
    raw_metrics = card.get("metrics") or []
    safe_metrics = []
    if isinstance(raw_metrics, list):
        for m in raw_metrics[:6]:  # Maximum 6 metrics per card
            if isinstance(m, dict):
                lbl = html.escape(str(m.get("label", ""))[:30])
                val = html.escape(str(m.get("value", ""))[:40])
                color = str(m.get("color", "#FFFFFF"))[:16]
                if not re.match(r"^#[0-9a-fA-F]{3,8}$", color):
                    color = "#FFFFFF"
                safe_metrics.append({"label": lbl, "value": val, "color": color})

    # Sanitize navigation target
    raw_target = card.get("target") or {}
    safe_target = {}
    if isinstance(raw_target, dict):
        if "action_type" in raw_target:
            safe_target["action_type"] = str(raw_target["action_type"])[:32]
        if "year" in raw_target and isinstance(raw_target["year"], (int, str)):
            try:
                safe_target["year"] = int(raw_target["year"])
            except ValueError:
                pass
        if "round" in raw_target and isinstance(raw_target["round"], (int, str)):
            try:
                safe_target["round"] = int(raw_target["round"])
            except ValueError:
                pass
        if "session" in raw_target:
            safe_target["session"] = str(raw_target["session"])[:16]
        if "lap" in raw_target and isinstance(raw_target["lap"], (int, str)):
            try:
                safe_target["lap"] = int(raw_target["lap"])
            except ValueError:
                pass
        if "driver" in raw_target:
            safe_target["driver"] = str(raw_target["driver"])[:16]
        if "race_name" in raw_target:
            safe_target["race_name"] = html.escape(str(raw_target["race_name"])[:60])

    return {
        "type": card_type,
        "title": title,
        "metrics": safe_metrics,
        "action": action,
        "target": safe_target
    }


class InMemoryRateLimiter:
    """
    Lightweight, sliding-window rate limiter per client IP.
    Default: 60 requests per minute.
    Requires zero external Redis / database infrastructure.
    """
    def __init__(self, requests_per_minute: int = 60):
        self.rpm = requests_per_minute
        self.history = defaultdict(deque)

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        window_start = now - 60.0
        q = self.history[client_ip]

        # Evict timestamps older than 60 seconds
        while q and q[0] < window_start:
            q.popleft()

        if len(q) >= self.rpm:
            return False

        q.append(now)
        return True


rate_limiter = InMemoryRateLimiter(requests_per_minute=60)
