"""
SimGent - Pit Wall Race Engineer AI Agent
Answers queries grounded in real session telemetry, classifications, lap-by-lap timing,
Race Control events, driver retirements, pit strategies, championship standings,
and FIA technical regulations. Returns authoritative text plus rich A2UI cards.
"""

import datetime
import re
from typing import Dict, Any, List, Optional, Tuple
from app.tools import race_replay, f1_telemetry, f1_history
from app.tools import jolpica_sync as J
from app.tools.agent_memory import memory_manager

# Alias dictionary for robust driver resolution (modern + historical legends)
DRIVER_ALIASES = {
    # Typos & phonetic shortcuts
    "schmacur": "michael_schumacher", "shumacher": "michael_schumacher", "schumi": "michael_schumacher",
    "sena": "senna", "louda": "lauda", "versappen": "max_verstappen", "hamiltonn": "hamilton", "leclerk": "leclerc",
    "allonso": "alonso", "vetel": "vettel", "raikonen": "raikkonen", "hakinen": "hakkinen",
    "stroll": "stroll", "lance": "stroll", "lance stroll": "stroll", "str": "stroll", "#18": "stroll",
    "russell": "russell", "george": "russell", "george russell": "russell", "rus": "russell", "#63": "russell",
    "verstappen": "max_verstappen", "max": "max_verstappen", "max verstappen": "max_verstappen", "ver": "max_verstappen", "#1": "max_verstappen", "#33": "max_verstappen",
    "leclerc": "leclerc", "charles": "leclerc", "charles leclerc": "leclerc", "lec": "leclerc", "#16": "leclerc",
    "hamilton": "hamilton", "lewis": "hamilton", "lewis hamilton": "hamilton", "ham": "hamilton", "#44": "hamilton",
    "norris": "norris", "lando": "norris", "lando norris": "norris", "nor": "norris", "#4": "norris",
    "piastri": "piastri", "oscar": "piastri", "oscar piastri": "piastri", "pia": "piastri", "#81": "piastri",
    "antonelli": "antonelli", "kimi antonelli": "antonelli", "ant": "antonelli", "#12": "antonelli",
    "hadjar": "hadjar", "isack": "hadjar", "isack hadjar": "hadjar", "had": "hadjar", "#6": "hadjar",
    "colapinto": "colapinto", "franco": "colapinto", "franco colapinto": "colapinto", "col": "colapinto", "#43": "colapinto",
    "gasly": "gasly", "pierre": "gasly", "pierre gasly": "gasly", "gas": "gasly", "#10": "gasly",
    "albon": "albon", "alex": "albon", "alexander albon": "albon", "alb": "albon", "#23": "albon",
    "alonso": "alonso", "fernando": "alonso", "fernando alonso": "alonso", "alo": "alonso", "#14": "alonso",
    "bottas": "bottas", "valtteri": "bottas", "valtteri bottas": "bottas", "bot": "bottas", "#77": "bottas",
    "perez": "perez", "sergio": "perez", "checo": "perez", "per": "perez", "#11": "perez",
    "hulkenberg": "hulkenberg", "hülkenberg": "hulkenberg", "nico": "hulkenberg", "hul": "hulkenberg", "#27": "hulkenberg",
    "bearman": "bearman", "ollie": "bearman", "oliver bearman": "bearman", "bea": "bearman", "#87": "bearman",
    "lawson": "lawson", "liam": "lawson", "liam lawson": "lawson", "law": "lawson", "#30": "lawson",
    "bortoleto": "bortoleto", "gabriel": "bortoleto", "bor": "bortoleto", "#5": "bortoleto",
    "lindblad": "arvid_lindblad", "arvid": "arvid_lindblad", "lin": "arvid_lindblad", "#41": "arvid_lindblad",
    "ocon": "ocon", "esteban": "ocon", "oco": "ocon", "#31": "ocon",
    "sainz": "sainz", "carlos": "sainz", "sai": "sainz", "#55": "sainz",
    # Historic Champions & Legends
    "vettel": "vettel", "sebastian": "vettel", "sebastian vettel": "vettel", "vet": "vettel", "#5": "vettel",
    "raikkonen": "raikkonen", "räikkönen": "raikkonen", "kimi": "raikkonen", "kimi raikkonen": "raikkonen", "rai": "raikkonen", "#7": "raikkonen",
    "schumacher": "michael_schumacher", "michael": "michael_schumacher", "michael schumacher": "michael_schumacher", "msc": "michael_schumacher",
    "senna": "senna", "ayrton": "senna", "ayrton senna": "senna", "sen": "senna",
    "prost": "prost", "alain": "prost", "alain prost": "prost", "pro": "prost",
    "mansell": "mansell", "nigel": "mansell", "nigel mansell": "mansell", "man": "mansell",
    "lauda": "lauda", "niki": "lauda", "niki lauda": "lauda",
    "hunt": "hunt", "james": "hunt", "james hunt": "hunt",
    "piquet": "piquet", "nelson": "piquet", "nelson piquet": "piquet",
    "hakkinen": "hakkinen", "häkkinen": "hakkinen", "mika": "hakkinen", "mika hakkinen": "hakkinen", "hak": "hakkinen",
    "coulthard": "coulthard", "david": "coulthard", "david coulthard": "coulthard", "cou": "coulthard",
    "rosberg": "rosberg", "nico rosberg": "rosberg", "keke": "keke_rosberg",
    "button": "button", "jenson": "button", "jenson button": "button", "but": "button",
    "ricciardo": "ricciardo", "daniel": "ricciardo", "daniel ricciardo": "ricciardo", "ric": "ricciardo", "#3": "ricciardo",
    "fangio": "fangio", "juan manuel fangio": "fangio",
    "clark": "clark", "jim clark": "clark",
    "stewart": "stewart", "jackie stewart": "stewart",
    "hill": "damon_hill", "damon": "damon_hill", "graham": "graham_hill",
    "latifi": "latifi", "nicholas": "latifi", "lat": "latifi", "#6": "latifi",
    "berger": "berger", "gerhard": "berger",
    "ralf": "ralf_schumacher", "ralf schumacher": "ralf_schumacher", "rsc": "ralf_schumacher",
    "jos": "jos_verstappen", "jos verstappen": "jos_verstappen",
    "villeneuve": "gilles_villeneuve", "jacques": "villeneuve", "jacques villeneuve": "villeneuve"
}


def _has_match(q: str, q_words: set, candidates: List[str]) -> bool:
    """Checks whether any candidate keyword or multi-word phrase matches the query."""
    for c in candidates:
        if " " in c:
            if c in q:
                return True
        else:
            if c in q_words:
                return True
    return False


def _find_driver(query: str, drivers: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    q = query.lower()
    # Strip out "round \d+", "lap \d+", and years so they are not mistaken for driver numbers
    cleaned_q = re.sub(r'\b(round|r|lap|l)\s*\d+\b', '', q)
    cleaned_q = re.sub(r'\b(19\d\d|20\d\d)\b', '', cleaned_q)
    words = set(re.findall(r'[#\w]+', cleaned_q))

    # 1. Direct code or driver number match (e.g. #44, HAM, 44, #18, MSC, SEN)
    for d in drivers:
        code = d.get("code", "").lower()
        num_str = f"#{d.get('number', '')}"
        num_plain = str(d.get("number", ""))
        if code and code in words:
            return d
        if num_str in words or (len(num_plain) > 1 and num_plain in words):
            return d

    # 2. Check full name match in query (e.g. "michael schumacher", "ralf schumacher", "lewis hamilton")
    for d in drivers:
        name = d.get("name", "").lower()
        if name and name in q:
            return d

    # 3. Explicit Alias check (handles "schumacher" -> michael_schumacher, "verstappen" -> max_verstappen, etc.)
    for phrase, target in sorted(DRIVER_ALIASES.items(), key=lambda x: -len(x[0])):
        matched = (phrase in q) if " " in phrase else (phrase in words)
        if matched:
            for d in drivers:
                if d.get("id") == target or d.get("code", "").lower() == target:
                    return d

    # 3.5 Fuzzy historical resolver check across current session drivers
    hist_match = f1_history.resolve_historical_driver(q)
    if hist_match:
        for d in drivers:
            if (d.get("id") == hist_match.get("id") or
                d.get("code", "").lower() == hist_match.get("code", "").lower() or
                d.get("name", "").lower() == hist_match.get("name", "").lower()):
                return d

    # 4. Partial surname or first name match (with length check)
    for d in drivers:
        name = d.get("name", "").lower()
        parts = [p for p in name.split() if len(p) > 2]
        for part in parts:
            if part in words:
                return d
        did = d.get("id", "").lower()
        if did in words or did.replace("_", " ") in q:
            return d
        for part in did.split("_"):
            if len(part) > 3 and part in words:
                return d

    return None


# Geographic aliases mapping countries, cities, and adjectives to circuits
GEO_MAP = {
    "australia": ["australian", "melbourne", "albert park", "albert_park"],
    "australian": ["australia", "melbourne", "albert park", "albert_park"],
    "melbourne": ["australia", "australian", "albert park", "albert_park"],
    "albert park": ["australia", "australian", "melbourne"],
    "britain": ["british", "silverstone", "uk", "great britain"],
    "british": ["britain", "silverstone", "uk", "great britain"],
    "silverstone": ["britain", "british", "uk"],
    "belgium": ["belgian", "spa", "francorchamps"],
    "belgian": ["belgium", "spa", "francorchamps"],
    "spa": ["belgium", "belgian", "francorchamps"],
    "italy": ["italian", "monza", "imola", "emilia"],
    "italian": ["italy", "monza", "imola", "emilia"],
    "monza": ["italy", "italian"],
    "imola": ["italy", "emilia"],
    "monaco": ["monte carlo", "monte-carlo"],
    "monte carlo": ["monaco"],
    "canada": ["canadian", "montreal", "villeneuve"],
    "canadian": ["canada", "montreal", "villeneuve"],
    "montreal": ["canada", "canadian"],
    "brazil": ["brazilian", "interlagos", "sao paulo", "são paulo"],
    "brazilian": ["brazil", "interlagos", "sao paulo"],
    "interlagos": ["brazil", "brazilian", "sao paulo"],
    "japan": ["japanese", "suzuka", "fuji"],
    "japanese": ["japan", "suzuka", "fuji"],
    "suzuka": ["japan", "japanese"],
    "spain": ["spanish", "barcelona", "catalunya", "jerez"],
    "spanish": ["spain", "barcelona", "catalunya", "jerez"],
    "barcelona": ["spain", "spanish", "catalunya"],
    "netherlands": ["dutch", "zandvoort"],
    "dutch": ["netherlands", "zandvoort"],
    "zandvoort": ["netherlands", "dutch"],
    "germany": ["german", "nurburgring", "nürburgring", "hockenheim"],
    "german": ["germany", "nurburgring", "hockenheim"],
    "austria": ["austrian", "spielberg", "red bull ring", "österreichring"],
    "austrian": ["austria", "spielberg", "red bull ring"],
    "hungary": ["hungarian", "hungaroring", "budapest"],
    "hungarian": ["hungary", "hungaroring", "budapest"],
    "baku": ["azerbaijan"],
    "azerbaijan": ["baku"],
    "abu dhabi": ["yas marina", "yas_marina", "uae"],
    "yas marina": ["abu dhabi", "uae"],
    "bahrain": ["sakhir"],
    "saudi": ["saudi arabia", "jeddah"],
    "singapore": ["marina bay", "marina_bay"],
    "miami": ["hard rock"],
    "las vegas": ["vegas"],
    "austin": ["cota", "united states", "usa", "us gp", "texas"],
    "cota": ["austin", "united states", "usa"],
    "mexico": ["mexican", "hermanos rodriguez", "mexico city"],
    "china": ["chinese", "shanghai"],
    "france": ["french", "magny cours", "paul ricard"],
    "french": ["france", "magny cours", "paul ricard"],
    "malaysia": ["sepang", "kuala lumpur", "malaysian"],
    "malaysian": ["malaysia", "sepang", "kuala lumpur"],
    "sepang": ["malaysia", "malaysian", "kuala lumpur"],
}


_FOLLOW_UP_LEAD = re.compile(
    r"^(?:and what about|and how about|what about|how about|and|ok(?:ay)?|also|so|then)\b[\s,]*", re.I
)
_QUESTION_WORD = re.compile(r"\b(who|what|which|when|where|why|how|did|does|do|was|is|were|are)\b", re.I)
_NOT_A_NAME = re.compile(r"\d|grand prix|championship|summary|fia|pit wall|classification|telemetry|regulation", re.I)


def _subject_driver(text: str) -> Optional[str]:
    """The driver an assistant answer was about: its first bold person-like name."""
    for seg in re.findall(r"\*\*([^*]{3,40})\*\*", text or ""):
        seg = seg.strip()
        words = seg.split()
        if 1 < len(words) <= 4 and not _NOT_A_NAME.search(seg) and all(w[:1].isupper() for w in words):
            return seg
    return None


def resolve_follow_up(query: str, history: Optional[List[Dict[str, Any]]], _depth: int = 0) -> str:
    """Rewrite a context-dependent follow-up into a self-contained question.

    - Elliptical: "What about 2025?" after "Who won the 2024 world championship?"
      -> "Who won the 2025 world championship?"; "What about Monaco?" swaps the race.
    - Pronoun: "Where did he start?" -> "Where did Max Verstappen start?" (the driver the
      previous answer was about).
    - Event reference: "Which lap was that on?" after "When did Albon retire?" ->
      "When did Albon retire? Which lap was that on?"
    Questions that already stand on their own are returned unchanged.
    """
    q = (query or "").strip()
    if not q or not history:
        return q
    turns = [((t.get("role") or ""), (t.get("content") or t.get("text") or "")) for t in history]
    prev_idx = next((i for i in range(len(turns) - 1, -1, -1) if turns[i][0] == "user" and turns[i][1].strip()), None)
    prev_user = turns[prev_idx][1] if prev_idx is not None else ""
    if prev_idx is not None and _depth < 6:
        # The previous question may itself have been a follow-up ("what about 2025?"):
        # resolve it against the turns before it so chains like "...and 2021?" keep the topic.
        prev_user = resolve_follow_up(prev_user, history[:prev_idx], _depth + 1)
    prev_answer = next((c for r, c in reversed(turns) if r == "assistant" and c.strip()), "")
    if not prev_user:
        return q
    ql = q.lower()

    # 1. Elliptical follow-up ("and 2021?", "what about in 1995?", "how about Monaco?")
    lead = _FOLLOW_UP_LEAD.match(q)
    rest = _FOLLOW_UP_LEAD.sub("", q).strip(" ?.!")
    if lead and rest and not _QUESTION_WORD.search(rest):
        base = prev_user.strip()
        new_year = re.search(r"\b(19[5-9]\d|20[0-4]\d)\b", rest)
        other = re.sub(r"\b(?:in|at|the|for)\b|\b(19[5-9]\d|20[0-4]\d)\b", " ", rest, flags=re.I).strip()
        if new_year:
            if re.search(r"\b(19[5-9]\d|20[0-4]\d)\b", base):
                base = re.sub(r"\b(19[5-9]\d|20[0-4]\d)\b", new_year.group(1), base, count=1)
            else:
                base = base.rstrip(" ?.!") + f" in {new_year.group(1)}?"
        if other:
            swapped = re.sub(r"\b((?:[A-Za-zÀ-ÿ'-]+\s){1,2})(grand prix|gp)\b", other.title() + r" \2", base, count=1, flags=re.I)
            base = swapped if swapped != base else base.rstrip(" ?.!") + f" ({other})?"
        return base

    # 2. Pronoun pointing at the driver the previous answer was about
    if re.search(r"\b(he|him|his)\b", ql):
        name = _subject_driver(prev_answer)
        if name:
            out = re.sub(r"\bhis\b", f"{name}'s", q, flags=re.I)
            out = re.sub(r"\b(he|him)\b", name, out, flags=re.I)
            return out

    # 3. Reference to the event in the previous question ("which lap was that on?")
    # (Not for questions that already ask something specific and only use "that race" for
    #  context, e.g. "who finished third in that race?": the race comes from history anyway.)
    asks_own_thing = bool(re.search(
        r"\b(that|this) (race|grand prix|gp|season|year|weekend)\b|\bwho (won|finished|came|was on pole)\b|\bpole\b|\bp\d+\b",
        ql)) or _ordinal_position(ql) is not None
    if (re.search(r"\b(that|it|this)\b", ql) and len(ql.split()) <= 8 and not asks_own_thing
            and not re.search(r"\b(19|20)\d\d\b", ql) and prev_user.lower() not in ql):
        return f"{prev_user.strip()} {q}"
    return q


_ORDINAL_WORDS = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
}


def _ordinal_position(q: str) -> Optional[int]:
    """Finishing position asked with words: 'who finished second', 'third place', 'runner-up'.
    Championship runner-up questions are excluded; they belong to the standings handlers."""
    words = "|".join(_ORDINAL_WORDS)
    m = (re.search(rf"\bwho\s+(?:finished|came|placed|was|took)\s+(?:in\s+)?({words})\b", q)
         or re.search(rf"\b({words})\s+place\b", q))
    if m:
        return _ORDINAL_WORDS[m.group(1)]
    if re.search(r"\brunner[- ]?up\b", q) and not re.search(r"\b(championship|title|season|standings|wdc|wcc)\b", q):
        return 2
    return None


def _season_title_from_data(year: int, constructor: bool = False) -> Optional[Dict[str, Any]]:
    """Season champion from the official final standings data (cache, or the API when
    the cache is stale). Returns None when no standings data exists for that season,
    so the caller can fall back to the hand-written roster."""
    from app.tools import jolpica_sync as J
    try:
        rows = J.constructor_standings(year) if constructor else J.driver_standings(year)
    except Exception:
        return None
    if not rows or len(rows) < 2:
        return None
    if constructor:
        champ, ru = rows[0], rows[1]
        name, ru_name = champ["Constructor"]["name"], ru["Constructor"]["name"]
        team = name
        label = "Constructors' Champion"
    else:
        champ, ru = rows[0], rows[1]
        d, r2 = champ["Driver"], ru["Driver"]
        name = f"{d['givenName']} {d['familyName']}"
        ru_name = f"{r2['givenName']} {r2['familyName']}"
        team = (champ.get("Constructors") or [{}])[-1].get("name", "—")
        # Keep the roster's engine-qualified team name (e.g. "McLaren-Honda") when the
        # roster agrees with the data on who the champion was.
        roster = f1_history.WORLD_CHAMPIONS_BY_YEAR.get(year)
        if roster and roster.get("driver", "").split()[-1].lower() == d["familyName"].lower():
            team = roster.get("team", team)
        label = "World Drivers' Champion"
    pts, wins, ru_pts = float(champ["points"]), champ.get("wins", "?"), float(ru["points"])
    team_str = f" driving for **{team}**" if not constructor else ""
    text = (
        f"**{year} FIA Formula 1 World Championship Summary**:\n\n"
        f"• **{label}**: **{name}**{team_str}\n"
        f"• **Championship Record**: **{wins} Grand Prix victories**, scoring **{pts:g} points**\n"
        f"• **Runner-Up**: {ru_name} ({ru_pts:g} points, {pts - ru_pts:+g})\n\n"
        f"> *Source: official {year} final standings data.*"
    )
    card = {
        "type": "championship_card",
        "title": f"{year} World Championship Classification",
        "metrics": [
            {"label": "Constructors' Champion" if constructor else "World Champion", "value": name[:20], "color": "#FFB703"},
            {"label": "Points", "value": f"{pts:g} pts", "color": "#00F5D4"},
            {"label": "Season Wins", "value": f"{wins} Victories", "color": "#FFFFFF"},
            {"label": "Runner-Up", "value": ru_name[:20], "color": "#64748B"},
        ],
        "action": f"VIEW {year} STANDINGS",
        "target": {"action_type": "open_standings", "year": year},
    }
    return {"year": year, "text": text, "card": card,
            "driver_id": None if constructor else d.get("driverId")}


def _match_race_round(q: str, races: List[Dict[str, Any]]) -> Optional[int]:
    """Matches a user query against a list of season races."""
    # First: direct check of race tokens in query
    for r in races:
        name_words = re.findall(r'[a-zA-Z]{3,}', r.get("race_name", "").lower())
        tokens = [
            r.get("circuit_id", "").lower(),
            r.get("locality", "").lower(),
            r.get("country", "").lower(),
            r.get("race_name", "").lower(),
            r.get("race_name", "").lower().replace(" grand prix", "").replace(" gp", "").strip(),
        ] + [w for w in name_words if w not in ("grand", "prix", "the", "f1")]
        for tok in tokens:
            # Whole-word match: a bare substring check let circuit id "spa" match "spanish"
            # and answered Spanish GP questions with the Belgian GP.
            if tok and len(tok) >= 3 and re.search(r'\b' + re.escape(tok) + r'\b', q):
                return r["round"]

    # Second: alias / geographic expansions
    def _has_word(term: str) -> bool:
        return bool(re.search(r'\b' + re.escape(term) + r'\b', q))

    for geo_key, aliases in GEO_MAP.items():
        if _has_word(geo_key) or any(_has_word(a) for a in aliases):
            all_target_keys = {geo_key} | set(aliases)
            for r in races:
                name_words = re.findall(r'[a-zA-Z]{3,}', r.get("race_name", "").lower())
                rtoks = {
                    r.get("circuit_id", "").lower(),
                    r.get("locality", "").lower(),
                    r.get("country", "").lower(),
                    r.get("race_name", "").lower(),
                    r.get("race_name", "").lower().replace(" grand prix", "").replace(" gp", "").strip(),
                } | {w for w in name_words if w not in ("grand", "prix", "the", "f1")}
                if any(k in rtoks for k in all_target_keys):
                    return r["round"]
    return None


CURATED_RETIREMENTS = {
    # 2026 Bahrain GP in Malaysia (Sepang). Laps and stops: Jolpica race result and pit
    # stops. Albon's gearbox problem: grandprix.com race analysis. Russell's
    # cause has not been published, so none is stated.
    (2026, "sepang", "ALB"): {
        "exit_lap": 42,
        "completed_laps": 41,
        "cause": "Gearbox problem; stopped on track",
        "explanation": (
            "**Alexander Albon (#23 Williams)** retired from the 2026 Bahrain Grand Prix (held at Sepang) on **Lap 42**.\n\n"
            "• **Official Completed Laps**: 41 full laps.\n"
            "• **Retirement Race Lap**: **Lap 42** (of 55 laps).\n"
            "• **Cause**: Stopped on track with a gearbox problem.\n"
            "• **Race Impact**: His stop brought out a Virtual Safety Car, then a full Safety Car; Verstappen made his third pit stop under it on Lap 43."
        ),
        "action": "JUMP TO LAP 42 REPLAY"
    },
    (2026, "sepang", "BOT"): {
        "exit_lap": 8,
        "completed_laps": 7,
        "cause": "Went off track at the end of Lap 8",
        "explanation": (
            "**Valtteri Bottas (#77 Cadillac)** retired from the 2026 Bahrain Grand Prix (held at Sepang) on **Lap 8**.\n\n"
            "• **Official Completed Laps**: 7 full laps.\n"
            "• **Retirement Race Lap**: **Lap 8** (of 55 laps).\n"
            "• **Cause**: Went off track at the end of Lap 8 in wet conditions.\n"
            "• **Race Impact**: Triggered the first Safety Car (Laps 9–12); most of the field switched from intermediates to slicks on Lap 9."
        ),
        "action": "JUMP TO LAP 8 REPLAY"
    },
    (2026, "sepang", "RUS"): {
        "exit_lap": 50,
        "completed_laps": 49,
        "cause": "Stopped on track under the Safety Car (cause not published)",
        "explanation": (
            "**George Russell (#63 Mercedes)** retired from the 2026 Bahrain Grand Prix (held at Sepang) on **Lap 50**.\n\n"
            "• **Official Completed Laps**: 49 full laps (classified 20th).\n"
            "• **Retirement Race Lap**: **Lap 50**, during the late Safety Car period.\n"
            "• **Cause**: Stopped on track; no official cause has been published.\n"
            "• **Race Impact**: Antonelli and Hamilton completed the podium behind Verstappen."
        ),
        "action": "JUMP TO LAP 50 REPLAY"
    },
    (2026, "baku", "STR"): {
        "exit_lap": 9,
        "completed_laps": 7,
        "cause": "Loss of water pressure / terminal engine cooling failure",
        "explanation": (
            "**Lance Stroll (#18 Aston Martin)** exited the 2026 Azerbaijan Grand Prix on **Lap 9**.\n\n"
            "• **Official Completed Laps**: 7 full laps (Fastest Lap: 1:51.723 on Lap 7).\n"
            "• **Retirement Race Lap**: **Lap 9** (official Race Control timing / media consensus).\n"
            "• **Primary Cause**: Loss of water pressure / terminal engine cooling failure.\n"
            "• **Incident Telemetry**: Starting P22, Stroll was running on Lap 8 when alarms triggered on the Aston Martin pit wall. "
            "The team instructed him over the radio to pull off immediately and shut down the power unit. Stroll parked in the **Turn 15 runoff escape area** on Lap 8. "
            "Because the leaders were running ~38 seconds ahead, race leader George Russell crossed the line to begin **Lap 9** when Race Control officially neutralized the sector with yellow flags and logged Stroll's retirement.\n"
            "• **Paddock Exchange**: Following his exit, Stroll had a widely publicized, heated exchange with a track safety marshal after expressing frustration at having to wait behind the perimeter barrier rather than being escorted immediately back to the paddock."
        ),
        "action": "JUMP TO LAP 9 REPLAY"
    },
    (2024, "albert_park", "HAM"): {
        "exit_lap": 17,
        "completed_laps": 15,
        "cause": "Power Unit (ICE) catastrophic failure",
        "explanation": (
            "**Lewis Hamilton (#44 Mercedes)** retired from the 2024 Australian Grand Prix on **Lap 17**.\n\n"
            "• **Official Completed Laps**: 15 full laps.\n"
            "• **Retirement Race Lap**: **Lap 17**.\n"
            "• **Primary Cause**: Sudden Power Unit (Internal Combustion Engine) catastrophic failure.\n"
            "• **Incident Telemetry**: Running in P9 on Lap 17, Hamilton suffered a sudden complete loss of engine drive exiting Turn 10. "
            "He reported 'Engine failure' over the team radio and steered the car onto the grass at Turn 11 before stopping. "
            "Race Control deployed the Virtual Safety Car (VSC) on Lap 17 to recover his Mercedes W15."
        ),
        "action": "JUMP TO LAP 17 REPLAY"
    },
    (2024, "albert_park", "VER"): {
        "exit_lap": 4,
        "completed_laps": 3,
        "cause": "Right-rear brake caliper seizure & fire",
        "explanation": (
            "**Max Verstappen (#1 Red Bull)** retired from the 2024 Australian Grand Prix on **Lap 4**.\n\n"
            "• **Official Completed Laps**: 3 full laps.\n"
            "• **Retirement Race Lap**: **Lap 4**.\n"
            "• **Primary Cause**: Right-rear brake caliper stuck locked from lights out, leading to extreme brake overheating and fire.\n"
            "• **Incident Telemetry**: From the race start, Verstappen reported the car felt like 'driving with the handbrake on'. Carlos Sainz passed him for the lead on Lap 2, and thick smoke poured from the right-rear wheel before the brake assembly exploded as he entered pit lane on Lap 4 to retire, ending his 43-race consecutive finish streak."
        ),
        "action": "JUMP TO LAP 4 REPLAY"
    },
    (2021, "silverstone", "VER"): {
        "exit_lap": 1,
        "completed_laps": 0,
        "cause": "51G collision with Lewis Hamilton at Copse",
        "explanation": (
            "**Max Verstappen (#33 Red Bull)** crashed out of the 2021 British Grand Prix on **Lap 1**.\n\n"
            "• **Official Completed Laps**: 0 laps (Lap 1 incident).\n"
            "• **Retirement Race Lap**: **Lap 1**.\n"
            "• **Primary Cause**: High-speed wheel-to-wheel contact with Lewis Hamilton at Copse corner (51G barrier impact).\n"
            "• **Incident Telemetry**: Contesting the race lead down the Wellington and National pit straights, Hamilton attempted an inside move into the 290 km/h Copse corner. Hamilton's front-left touched Verstappen's right-rear, causing an immediate rear tyre failure that pitched Verstappen through the gravel trap into the tyre wall at 51G. The race was red-flagged immediately."
        ),
        "action": "JUMP TO LAP 1 REPLAY"
    },
    (2021, "yas_marina", "LAT"): {
        "exit_lap": 53,
        "completed_laps": 50,
        "cause": "Single-car barrier crash at Turn 14",
        "explanation": (
            "**Nicholas Latifi (#6 Williams)** crashed and retired from the 2021 Abu Dhabi Grand Prix on **Lap 53**.\n\n"
            "• **Official Completed Laps**: 50 full laps.\n"
            "• **Retirement Race Lap**: **Lap 53**.\n"
            "• **Primary Cause**: Rear-end snap into the barrier under dirty air at Turn 14.\n"
            "• **Incident Telemetry**: While battling Mick Schumacher for P15, Latifi ran wide off-line, gathered marbles on his tyres, and lost control under braking into Turn 14, slamming the barrier. "
            "His stranded Williams necessitated the Lap 53 Safety Car that directly set up the famous final-lap title shootout between Verstappen and Hamilton."
        ),
        "action": "JUMP TO LAP 53 REPLAY"
    },
    (1998, "spa", "MSC"): {
        "exit_lap": 25,
        "completed_laps": 24,
        "cause": "Torrential rain collision with lapped David Coulthard",
        "explanation": (
            "**Michael Schumacher (#3 Ferrari)** retired from the torrential 1998 Belgian Grand Prix on **Lap 25**.\n\n"
            "• **Official Completed Laps**: 24 full laps.\n"
            "• **Retirement Race Lap**: **Lap 25**.\n"
            "• **Primary Cause**: Collision with David Coulthard's McLaren in zero-visibility spray.\n"
            "• **Incident Telemetry**: Schumacher led the race by over 40 seconds in torrential rain. Approaching Coulthard to lap him on the descent to Pouhon, Coulthard eased off the throttle while remaining directly on the racing line in blinding spray. Schumacher unsighted rear-ended the McLaren, ripping off his Ferrari's right-front suspension. Both cars limped back to the pit lane, leading to the infamous scene of Schumacher storming into the McLaren garage."
        ),
        "action": "JUMP TO LAP 25 REPLAY"
    },
    (2024, "monaco", "PER"): {
        "exit_lap": 1,
        "completed_laps": 0,
        "cause": "Beau Rivage high-speed collision with Kevin Magnussen",
        "explanation": (
            "**Sergio Pérez (#11 Red Bull)** retired from the 2024 Monaco Grand Prix on **Lap 1**.\n\n"
            "• **Official Completed Laps**: 0 laps (Lap 1 incident).\n"
            "• **Retirement Race Lap**: **Lap 1**.\n"
            "• **Primary Cause**: Heavy collision on the climb up Beau Rivage with Kevin Magnussen's Haas.\n"
            "• **Incident Telemetry**: Heading up the hill toward Massenet on the opening lap, Magnussen attempted to squeeze up the inside of Pérez into a closing gap. The cars touched, sending Pérez's Red Bull into the barrier and ricocheting back across the track to collect Nico Hülkenberg. The chassis was completely destroyed, triggering a 45-minute red flag."
        ),
        "action": "JUMP TO LAP 1 REPLAY"
    },
    (1988, "monza", "SEN"): {
        "exit_lap": 49,
        "completed_laps": 48,
        "cause": "Chicane collision with Jean-Louis Schlesser",
        "explanation": (
            "**Ayrton Senna (#12 McLaren-Honda)** retired from the 1988 Italian Grand Prix on **Lap 49**.\n\n"
            "• **Official Completed Laps**: 48 full laps.\n"
            "• **Retirement Race Lap**: **Lap 49** (of 51 laps).\n"
            "• **Primary Cause**: Collision at the Rettifilo Chicane while attempting to lap Jean-Louis Schlesser's Williams.\n"
            "• **Incident Telemetry**: Senna had led comfortably from pole position and was only 2 laps away from victory, which would have preserved McLaren's clean sweep of all 16 races in 1988. Heading into the Prima Variante chicane, Schlesser locked up and went wide. As Senna cut inside, Schlesser turned back across the kerb, launching Senna's McLaren onto the kerbing with damaged suspension, handing Ferrari's Gerhard Berger an emotional 1-2 victory weeks after Enzo Ferrari's passing."
        ),
        "action": "JUMP TO LAP 49 REPLAY"
    }
}



def _get_driver_tyre_stints(d: Dict[str, Any], events: List[Dict[str, Any]], total_laps: int) -> Dict[str, Any]:
    """
    Computes precise stint lap windows, tyre compounds, and strategic context for a driver.
    Accounts for wet weather start declarations, safety car pit windows, and dry compound allocations.
    """
    pits = sorted(d.get("pits", []))
    completed_laps = d.get("laps", total_laps)
    
    # Check if wet weather condition was declared at start of session
    is_wet_start = any(
        e.get("type") == "WEATHER" and any(k in e.get("message", "").lower() for k in ["rain", "deluge", "wet", "intermediate"])
        for e in events
    )
    
    num_stops = len(pits)
    stint_boundaries = [1]
    for p in pits:
        stint_boundaries.append(p)
    stint_boundaries.append(completed_laps)
    
    # Compound assignment logic
    if is_wet_start:
        # e.g., Bahrain 2026 wet start: Inters -> Mediums -> Softs
        compounds = ["Intermediate", "Medium", "Soft", "Soft"]
    else:
        # Standard dry allocations
        if num_stops == 0:
            compounds = ["Hard"]
        elif num_stops == 1:
            compounds = ["Medium", "Hard"]
        elif num_stops == 2:
            compounds = ["Medium", "Hard", "Soft"]
        else:
            compounds = ["Medium", "Hard", "Hard", "Soft"]
            
    stints = []
    for i in range(len(stint_boundaries) - 1):
        start_lap = stint_boundaries[i] if i == 0 else stint_boundaries[i] + 1
        end_lap = stint_boundaries[i + 1]
        if start_lap > end_lap:
            start_lap = end_lap
        compound = compounds[i] if i < len(compounds) else "Soft"
        color = {
            "Soft": "#EF4444",
            "Medium": "#FFD166",
            "Hard": "#FFFFFF",
            "Intermediate": "#10B981",
            "Wet": "#3B82F6"
        }.get(compound, "#FFFFFF")
        
        stints.append({
            "stint": i + 1,
            "start_lap": start_lap,
            "end_lap": end_lap,
            "laps": max(1, end_lap - start_lap + 1),
            "compound": compound,
            "color": color
        })
        
    return {
        "is_wet_start": is_wet_start,
        "num_stops": num_stops,
        "pits": pits,
        "stints": stints
    }


def race_from_history(history: Optional[List[Dict[str, Any]]], default_year: int) -> Optional[Tuple[int, int]]:
    """The race a conversation is about, from the user's own questions.

    Walk back over plain follow-ups ("who finished second?", "where did he start?") to the
    most recent question that names a race and use it. If the first naming question is about
    a whole season instead ("what about 2016?", "who won the 2024 championship?"), the
    conversation has left any single race: return None. A circuit named without a year takes
    the year from the nearest earlier question that has one, never from a later one (that
    produced a phantom "2024 Monaco GP" from "what about Monaco?" + "2024 championship").
    """
    users = [(t.get("content") or t.get("text") or "").lower() for t in (history or []) if t.get("role") == "user"]
    for i in range(len(users) - 1, -1, -1):
        text = users[i]
        ym = re.search(r"\b(19\d\d|20\d\d)\b", text)
        year = int(ym.group(1)) if ym else None
        if year is None:
            year = next((int(m.group(1)) for t in reversed(users[:i])
                         for m in [re.search(r"\b(19\d\d|20\d\d)\b", t)] if m), default_year)
        if not 1950 <= year <= default_year + 1:
            continue
        rnd = _match_race_round(text, race_replay.season_races(year))
        if rnd is not None:
            return year, rnd
        if ym:
            return None  # season-level question: no single race in focus
    return None


def scope_history_to_view(history: Optional[List[Dict[str, Any]]],
                          context: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Drop turns from before the viewer switched to the race now on screen.

    The UI tags each turn with the race that was on screen ("view": "2026-16"). Without
    this, a question about the current race ("explain VER's pit strategy") was answered
    for a race discussed earlier in the chat (e.g. the Australian GP). History with no
    view tags at all (other clients, tests) is used as-is; once tags exist, an untagged
    turn counts as a different view.
    """
    turns = list(history or [])
    ctx = context or {}
    if not turns or not ctx.get("year") or not ctx.get("round"):
        return turns
    if not any(t.get("view") for t in turns):
        return turns
    view = f"{ctx['year']}-{ctx['round']}"
    kept: List[Dict[str, Any]] = []
    for t in reversed(turns):
        if t.get("view") != view:
            break
        kept.append(t)
    return list(reversed(kept))


# A driver from an earlier turn is only meant when the question points back to it.
_DRIVER_BACKREF = re.compile(r"\b(he|his|him|she|her|they|their|them|that|it|its|same driver)\b")


# Answers built from one session's data, and which session that is.
_RACE_DATA_TOOLS = {
    "race_classification_lookup": "race", "driver_performance_lookup": "race",
    "driver_classification_lookup": "race", "driver_finish_position_lookup": "race",
    "driver_starting_grid_lookup": "race", "starting_grid_lookup": "race",
    "driver_podium_verification": "race", "pit_strategy_profile": "race",
    "pit_strategy_explanation": "race", "safety_car_analysis": "race", "race_control_lookup": "race",
    "incident_investigation": "race", "dnf_summary_lookup": "race", "fastest_lap_lookup": "race",
    "sprint_classification_lookup": "sprint", "sprint_grid_lookup": "sprint",
    "sprint_qualifying_lookup": "sprint_qualifying", "qualifying_pole_lookup": "qualifying",
}


def answer_race_engineer_query(
    query: str,
    context: Optional[Dict[str, Any]] = None,
    history: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Main entry point. The race and session on screen are the default scope for questions
    that don't name their own (ADK session-state pattern); every race-data answer says which
    race and session it is based on."""
    from app.tools import session_scope as SS
    history = scope_history_to_view(history, context)
    scope = SS.resolve_scope(query, context, history)
    if scope and scope["from_screen"] and scope["session"] != "race":
        resp = SS.answer_in_session(query, scope, context, history)
        if resp:
            return SS.with_scope(resp, scope, resp.pop("label"))
    resp = _answer_core(query, context, history)
    used = _RACE_DATA_TOOLS.get(resp.get("tool", ""))
    if scope and scope["from_screen"] and used:
        answered = dict(scope, session=used)
        note = (f"No {SS._LABEL[scope['session']]} data for this question — answered from "
                if used != scope["session"] else "")
        resp = SS.with_scope(resp, answered, SS.scope_label(answered), note)
    return resp


def _answer_core(
    query: str,
    context: Optional[Dict[str, Any]] = None,
    history: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Main entry point for race engineering queries.
    Resolves driver telemetry, retirements, pit strategies, championship standings, and regulations
    across any season (1950-2026) and any Grand Prix.
    Supports multi-turn context and pronoun resolution from conversation history.
    """
    history = scope_history_to_view(history, context)
    query = resolve_follow_up(query, history)  # "what about 2025?", "where did he start?"
    q = query.lower().strip()
    q_words = set(re.findall(r'\b[a-z0-9_-]+\b', q))
    ctx = context or {}
    try:
        year = int(ctx.get("year", 2026))
    except (ValueError, TypeError):
        year = 2026
    try:
        round_no = int(ctx.get("round", 15))
    except (ValueError, TypeError):
        round_no = 15

    # 0. Check Grounded RAG Memory Subsystem (Ground Truth & Verified Feedback)
    mem_hit = memory_manager.retrieve(query, context=ctx, history=history, defer_to_data=True)
    if mem_hit:
        return mem_hit

    # Check if user mentioned "today", "latest", "last race", "recent race", "current race"
    if any(w in q for w in ["today", "latest race", "recent race", "last race", "current race"]):
        races_2026 = race_replay.season_races(2026)
        completed_2026 = [r for r in races_2026 if r.get("completed")]
        if completed_2026:
            year = 2026
            round_no = completed_2026[-1]["round"]

    # Check if a specific year was requested in the text (1950 to 2026)
    year_match = re.search(r'\b(19\d\d|20\d\d)\b', q)
    if year_match:
        requested_year = int(year_match.group(1))
        if 1950 <= requested_year <= 2026:
            year = requested_year
            races = race_replay.season_races(year)
            matched_rnd = _match_race_round(q, races)
            if matched_rnd is not None:
                round_no = matched_rnd
            elif ctx and ctx.get("round"):
                try:
                    round_no = int(ctx["round"])
                except (ValueError, TypeError):
                    round_no = (races[-1]["round"] if races else 1)
            else:
                round_no = (races[-1]["round"] if races else 1)
    else:
        # Check if user mentioned another circuit/race in current season
        races = race_replay.season_races(year)
        matched_rnd = _match_race_round(q, races)
        if matched_rnd is not None:
            round_no = matched_rnd
        elif history:
            # Pronoun/antecedent resolution: pin BOTH year and round from the SAME recent
            # conversation context so they cannot desync. Adopting a historical year while
            # keeping the current round produced the wrong race (e.g. 2024 + round 16 = the
            # Italian GP instead of the Australian GP that was actually being discussed).
            # Only the user's questions count: assistant answers mention other races and
            # eras in passing (career profiles, era summaries).
            _h = race_from_history(history, datetime.date.today().year)
            if _h:
                year, round_no = _h
                races = race_replay.season_races(year)

    # Check if an explicit round was requested in text (e.g. "round 16", "r16")
    round_match = re.search(r'\b(?:round|r)\s*(\d+)\b', q)
    if round_match:
        explicit_rnd = int(round_match.group(1))
        races_for_yr = race_replay.season_races(year)
        if any(r["round"] == explicit_rnd for r in races_for_yr):
            round_no = explicit_rnd

    # Load replay model for the session
    model = race_replay.build_replay(year, round_no)
    if not model and races:
        model = race_replay.build_replay(year, races[0]["round"])

    meta = model["meta"] if model else {}
    drivers = model["drivers"] if model else []
    events = model["events"] if model else []
    winner = drivers[0] if drivers else None

    # Question shape. Factual result questions ("who won", "who finished second", "pole")
    # must be answered from the classification, not intercepted by narrative/career handlers.
    word_pos = _ordinal_position(q)
    is_result_q = bool(re.search(
        r"\b(who won|winner|won the|who finished|finished (?:in )?(?:p\s*)?\d+|runner[- ]?up|podium|pole|p[1-3])\b", q
    )) or word_pos is not None
    is_narrative_q = any(w in q for w in [
        "what happened", "story", "why", "controvers", "explain", "tell me about", "drama",
        "how did", "describe", "remember", "turning point", "incident", "crash"
    ])
    race_named = _match_race_round(q, race_replay.season_races(year)) is not None

    # Venue questions ("where was the 2026 Bahrain GP held?", "which circuit hosted ...?")
    is_venue_q = bool(re.search(
        r"\b(where (?:was|is|will)|held|hosted|venue|which (?:circuit|track)|what (?:circuit|track))\b", q
    )) and (race_named or bool(re.search(r"\b(grand prix|gp|race)\b", q))) and _find_driver(q, drivers) is None
    if is_venue_q and meta.get("circuit_name"):
        reloc = race_replay.EVENT_RELOCATIONS.get((year, round_no), {})
        place = ", ".join(p for p in (meta.get("locality"), meta.get("country")) if p)
        place_str = f" ({place})" if place else ""
        date_str = f" on {meta['date']}" if meta.get("date") else ""
        note = f"\n\n{reloc['note']}" if reloc.get("note") else ""
        return {
            "role": "assistant",
            "text": (f"The **{year} {meta.get('race_name', 'Grand Prix')}** was held at **{meta['circuit_name']}**"
                     f"{place_str}{date_str}.{note}"),
            "tool": "race_venue_lookup",
            "intent": f"{year} Grand Prix Venue",
            "a2ui_card": None,
        }

    # 0.5 HISTORICAL RESEARCH & ENCYCLOPEDIA TOOLS (1950–2026)
    # A. Iconic Race Moments, Turning Points & Famous Controversies
    story_data = None
    # Narrate only when asked for a story, or when THIS question names the race itself.
    # A race inherited from earlier turns ("where did he start?") is context, not a story request.
    names_race_itself = bool(year_match) or race_named
    # Driver results and strategy belong to the data handlers; "why"/controversy questions
    # about a named driver ("why was Senna disqualified in 1989?") are still stories.
    is_story_ask = bool(re.search(r"\b(why|disqualif\w*|controvers\w*|story|what happened|collision|crashgate|scandal)\b", q))
    is_driver_detail_q = not is_story_ask and (_find_driver(q, drivers) is not None or bool(re.search(
        r"\b(pit|strateg\w*|stint|tyres?|tires?|retire\w*|dnf|grid|start\w*|qualif\w*|lap \d+|pace|gap)\b", q)))
    if (is_narrative_q or (names_race_itself and not is_result_q)) and not is_driver_detail_q:
        story_data = f1_history.lookup_historic_race_event(q, year, meta.get("circuit_id"))
    if story_data:
        return {
            "role": "assistant",
            "text": story_data["text"],
            "tool": "historic_race_moment_lookup",
            "intent": "Iconic Formula 1 Historical Turning Point & Drama Analysis",
            "a2ui_card": story_data["card"]
        }

    # B. Head-to-Head Driver Comparisons (e.g. Senna vs Prost, Hamilton vs Schumacher)
    is_h2h_query = bool(re.search(r'\b(compare|vs|versus|head-to-head|head to head)\b', q)) or (
        " and " in q and any(w in q for w in ["wins", "titles", "championships", "better", "stats", "greater", "record"])
    )
    if is_h2h_query:
        found_d = []
        q_low = q.lower()
        for alias, did in sorted(f1_history.DRIVER_NAME_LOOKUP.items(), key=lambda x: -len(x[0])):
            if len(alias) >= 3 and alias in q_low:
                if did not in found_d:
                    found_d.append(did)
                    if len(found_d) == 2:
                        break
        if len(found_d) == 2:
            h2h_res = f1_history.compare_drivers_head_to_head(found_d[0], found_d[1])
            if h2h_res:
                return {
                    "role": "assistant",
                    "text": h2h_res["text"],
                    "tool": "driver_head_to_head_comparison",
                    "intent": f"Head-to-Head Comparison: {h2h_res['d1']['name']} vs {h2h_res['d2']['name']}",
                    "a2ui_card": h2h_res["card"]
                }

    # C. Specific Driver Milestone & Metric Queries (e.g. 'How many podiums does Alonso have?')
    is_driver_metric = bool(re.search(r'\b(how many|number of|total|count of)\b', q)) and any(
        w in q for w in ["podium", "podiums", "win", "wins", "pole", "poles", "championship", "championships", "title", "titles", "starts", "races"]
    )
    if is_driver_metric:
        metric_res = f1_history.lookup_driver_metric(q)
        if metric_res:
            return {
                "role": "assistant",
                "text": metric_res["text"],
                "tool": "driver_career_milestone_lookup",
                "intent": f"{metric_res['driver']['name']} Career Milestone",
                "a2ui_card": metric_res["card"]
            }

    # D. All-Time Historical Records & Leaderboards (checked first for leaderboards)
    is_records_query = any(w in q for w in [
        "most wins", "most victories", "most championships", "most titles", "most poles",
        "greatest f1 driver", "greatest driver", "goat of f1", "youngest champion", "youngest world champion",
        "oldest champion", "most podiums", "most constructor titles", "all time records", "all-time record"
    ]) or ("most" in q and any(w in q for w in ["win", "wins", "championship", "championships", "title", "titles", "pole", "poles", "podium", "podiums", "constructor"])) or (
        any(w in q for w in ["youngest", "oldest"]) and any(w in q for w in ["champion", "winner", "title"])
    )
    if is_records_query:
        rec_data = f1_history.lookup_all_time_records(q)
        if rec_data:
            return {
                "role": "assistant",
                "text": rec_data["text"],
                "tool": "f1_all_time_records_lookup",
                "intent": "Grand Prix Historical Leaderboard & All-Time Records",
                "a2ui_card": rec_data["card"]
            }

    # E. Historical World Championship Outcome (1950–2025)
    if year_match and not race_named and not any(w in q for w in ["grand prix", "gp", "race", "circuit", "round"]):
        hist_yr = int(year_match.group(1))
        if 1950 <= hist_yr <= 2025 and any(w in q for w in ["champion", "championship", "title", "who won", "winner of the season", "won the"]):
            # Prefer the official final standings data; the hand-written roster in
            # f1_history is only a fallback for seasons without standings data.
            wants_constructor = bool(re.search(r"\b(constructor|constructors|constructors'|team|teams|wcc)\b", q))
            champ_data = _season_title_from_data(hist_yr, wants_constructor)
            if champ_data is None:
                champ_data = f1_history.lookup_season_champion(hist_yr)
            if champ_data:
                return {
                    "role": "assistant",
                    "text": champ_data["text"],
                    "tool": "historical_championship_lookup",
                    "intent": f"{hist_yr} FIA World Championship Classification",
                    "driver_id": champ_data.get("driver_id"),
                    "a2ui_card": champ_data["card"]
                }

    # F0. Sprint Qualifying / Sprint Shootout (who took sprint pole, SQ times)
    is_sq_query = bool(re.search(
        r"sprint (?:qualifying|quali|shootout)|sprint pole|pole (?:for|in) the sprint|\bsq[123]?\b|sprint (?:pole )?position", q))
    if is_sq_query:
        sq_model = race_replay.build_replay(year, round_no, session_type="sprint_qualifying")
        if sq_model and sq_model.get("drivers") and sq_model["meta"].get("session_type") == "sprint_qualifying":
            m = sq_model["meta"]
            ds = sq_model["drivers"]
            p1 = ds[0]
            p2 = ds[1] if len(ds) > 1 else None
            session_name = m.get("session_name", "Sprint Qualifying")
            top = ", ".join(f"P{i + 1} {d['name']} ({d.get('best_lap', '—')})" for i, d in enumerate(ds[:3]))
            gap = f", {p2.get('pole_delta')} ahead of {p2['name']}" if p2 and p2.get("pole_delta", "").startswith("+") else ""
            notes = "".join(f"\n\n> *Stewards: {n}*" for n in m.get("notes", []))
            text = (f"**{p1['name']}** took **sprint pole** for {p1['team']} in **{session_name}** at the "
                    f"**{year} {m.get('race_name', '').split(' - ')[0]}** with **{m.get('pole_time')}**{gap}.\n\n"
                    f"Top three: {top}.{notes}")
            return {
                "role": "assistant", "text": text, "tool": "sprint_qualifying_lookup",
                "intent": f"{year} {session_name} Classification",
                "a2ui_card": {
                    "type": "qualifying_card",
                    "title": f"{session_name} — {m.get('race_name', '').split(' - ')[0]}",
                    "metrics": [
                        {"label": "Sprint Pole", "value": f"{p1['name']} ({p1['code']})", "color": p1["color"]},
                        {"label": "SQ3 Time", "value": m.get("pole_time") or "—", "color": "#A855F7"},
                        {"label": "Front Row P2", "value": f"{p2['name']} ({p2['code']})" if p2 else "—", "color": p2["color"] if p2 else "#64748B"},
                        {"label": "Session", "value": session_name, "color": "#00F5D4"},
                    ],
                    "action": "VIEW SPRINT QUALIFYING",
                    "target": {"action_type": "switch_session", "year": year, "round": round_no, "session": "sprint_qualifying"},
                },
            }
        has_sprint = any(r.get("round") == round_no and r.get("has_sprint") for r in race_replay.season_races(year))
        if has_sprint and year < 2023:
            return {"role": "assistant", "tool": "sprint_qualifying_lookup", "intent": f"{year} Sprint Format", "a2ui_card": None,
                    "text": (f"In {year} there was no separate Sprint Qualifying session: Friday's qualifying set the sprint grid, "
                             f"and the sprint result set Sunday's grid. Ask about qualifying or the sprint for that weekend.")}

    # F1. Sprint starting grid (who started where in the sprint)
    if re.search(r"sprint (?:starting )?grid|start(?:ed|s)? (?:the|in the|on the) sprint|sprint start", q):
        sp = J.sprint_results(year, round_no, net=True)
        rows = (sp or {}).get("SprintResults", [])
        if rows:
            on_grid = sorted([x for x in rows if race_replay._safe_int(x.get("grid"), 0) > 0], key=lambda x: int(x["grid"]))
            pit_lane = [x for x in rows if race_replay._safe_int(x.get("grid"), 0) == 0]
            nm = lambda x: f"{x['Driver']['givenName']} {x['Driver']['familyName']}"
            grid_txt = ", ".join(f"P{x['grid']} {nm(x)}" for x in on_grid[:6])
            pl_txt = f" Pit lane: {', '.join(nm(x) for x in pit_lane)}." if pit_lane else ""
            return {"role": "assistant", "tool": "sprint_grid_lookup", "intent": f"{year} Sprint Starting Grid", "a2ui_card": None,
                    "text": (f"**Sprint starting grid — {year} {sp.get('raceName', '')}**: {grid_txt}.{pl_txt}")}

    # F. Sprint Race Results & Classification
    is_sprint_query = any(w in q for w in ["sprint", "sprint race"])
    if is_sprint_query:
        sp_model = race_replay.build_replay(year, round_no, session_type="sprint")
        if sp_model and sp_model.get("drivers"):
            sp_winner = sp_model["drivers"][0]
            sp_p2 = sp_model["drivers"][1] if len(sp_model["drivers"]) > 1 else None
            sp_p3 = sp_model["drivers"][2] if len(sp_model["drivers"]) > 2 else None
            p2_txt = f", ahead of {sp_p2['name']} in P2" if sp_p2 else ""
            p3_txt = f" and {sp_p3['name']} in P3" if sp_p3 else ""
            sp_pts = sp_winner.get("points")
            pts_txt = f", scoring {sp_pts:g} championship point{'s' if sp_pts != 1 else ''}" if isinstance(sp_pts, (int, float)) and sp_pts else ""
            text = (
                f"**{sp_winner['name']}** won the **{sp_model['meta'].get('race_name', 'Sprint')} ({year})** "
                f"for {sp_winner['team']} from P{sp_winner.get('grid', '?')} on the sprint grid{p2_txt}{p3_txt}{pts_txt} over {sp_winner['laps']} laps."
            )
            return {
                "role": "assistant",
                "text": text,
                "tool": "sprint_classification_lookup",
                "intent": f"{year} F1 Sprint Race Results & Classification",
                "a2ui_card": {
                    "type": "race_summary_card",
                    "title": f"F1 Sprint Classification — {sp_model['meta'].get('race_name', 'Sprint')}",
                    "metrics": [
                        {"label": "Sprint Winner (P1)", "value": f"{sp_winner['name']} ({sp_winner['code']})", "color": sp_winner["color"]},
                        {"label": "Runner-Up (P2)", "value": f"{sp_p2['name']} ({sp_p2['code']})" if sp_p2 else "—", "color": sp_p2["color"] if sp_p2 else "#64748B"},
                        {"label": "Sprint Points", "value": f"{sp_winner.get('points', 0):g} Points (P1)", "color": "#00F5D4"},
                        {"label": "Sprint Distance", "value": f"{sp_winner['laps']} Laps", "color": "#FFFFFF"}
                    ],
                    "action": "VIEW SPRINT REPLAY",
                    "target": {
                        "action_type": "switch_session",
                        "year": year,
                        "round": round_no,
                        "session": "sprint"
                    }
                }
            }

    # G. Pole Position & Official Qualifying Shootout
    is_pole_or_quali = any(w in q for w in ["pole", "pole position", "qualifying", "who took pole", "who was on pole", "who started p1", "pole lap", "pole time"])
    if is_pole_or_quali and not any(w in q for w in ["career", "all-time", "most poles", "how many poles"]):
        q_model = race_replay.build_replay(year, round_no, session_type="qualifying")
        if q_model and q_model.get("drivers"):
            pole_drv = q_model["drivers"][0]
            p2_drv = q_model["drivers"][1] if len(q_model["drivers"]) > 1 else None
            estimated = bool(q_model["meta"].get("times_estimated"))
            pole_t = None if estimated else q_model["meta"].get("pole_time")
            p2_delta = p2_drv.get("pole_delta") if (p2_drv and not estimated) else None
            gap_txt = f" ({p2_delta} ahead of {p2_drv['name']})" if p2_delta and p2_delta.startswith("+") else (
                f", with {p2_drv['name']} alongside on the front row" if p2_drv else "")
            time_txt = f" with a lap of **{pole_t}**" if pole_t else ""
            caveat = " Lap times for this session are not in the data, so none are quoted." if estimated else ""
            text = (
                f"**{pole_drv['name']}** took **Pole Position** for {pole_drv['team']} at the **{q_model['meta'].get('race_name', 'Qualifying')} ({year})**"
                f"{time_txt}{gap_txt}.{caveat}"
            )
            pole_t = pole_t or "Not available"
            return {
                "role": "assistant",
                "text": text,
                "tool": "qualifying_pole_lookup",
                "intent": f"{year} Qualifying & Pole Position Classification",
                "a2ui_card": {
                    "type": "qualifying_card",
                    "title": f"Pole Position Shootout — {q_model['meta'].get('race_name', 'Qualifying')}",
                    "metrics": [
                        {"label": "Pole Sitter (P1)", "value": f"{pole_drv['name']} ({pole_drv['code']})", "color": pole_drv["color"]},
                        {"label": "Pole Lap Time", "value": pole_t, "color": "#A855F7"},
                        {"label": "Front Row P2", "value": f"{p2_drv['name']} ({p2_drv['code']})" if p2_drv else "—", "color": p2_drv["color"] if p2_drv else "#64748B"},
                        {"label": "Session", "value": "Q3 Shootout Final", "color": "#00F5D4"}
                    ],
                    "action": "VIEW QUALIFYING REPLAY",
                    "target": {
                        "action_type": "switch_session",
                        "year": year,
                        "round": round_no,
                        "session": "qualifying"
                    }
                }
            }

    # H. Driver Career & Era Research (e.g. Schumacher, Senna, Fangio, Lauda)
    hist_driver = f1_history.resolve_historical_driver(q)
    is_career_or_era_query = any(w in q for w in [
        "when did", "what era", "which era", "how many championships", "how many titles",
        "career", "history", "years did", "who is", "who was", "tell me about",
        "what teams", "how many wins", "record", "where did he race", "who did he drive for"
    ]) or bool(re.search(r'\b(era|eras|career|all-time|greatest|goat|record|records)\b', q))

    # A result question about a named race is about that race, not a driver's career.
    # (The fuzzy name resolver also mistakes words like "malaysian" for a driver.)
    if hist_driver and is_result_q and race_named and not re.search(r'\b(career|all-time|how many)\b', q):
        hist_driver = None

    race_driver = _find_driver(q, drivers)
    if hist_driver and race_driver and race_driver.get("id") != hist_driver.get("id") \
            and race_driver.get("code") != hist_driver.get("code"):
        hist_driver = None  # "Landi" is Chico Landi in this race, not a fuzzy match for Lando Norris
    if (hist_driver and race_driver and re.search(r"\bretire", q)
            and not re.search(r"\b(career|from f1|from formula|stop racing|quit f1|leave f1)\b", q)
            and not str(race_driver.get("status", "")).startswith(("Finished", "+"))
            and "Lap" not in str(race_driver.get("status", ""))):
        hist_driver = None  # "when did Senna retire?" at a race he didn't finish = the race retirement

    if hist_driver:
        in_active_session = any(
            (d.get("id") == hist_driver["id"] or d.get("code") == hist_driver["code"])
            for d in drivers
        ) if drivers else False

        # If user explicitly asked about career/era OR the driver is not in the active session:
        if is_career_or_era_query or not in_active_session:
            career_data = f1_history.lookup_driver_career(hist_driver["id"])
            if career_data:
                return {
                    "role": "assistant",
                    "text": career_data["text"],
                    "tool": "driver_career_history_lookup",
                    "intent": "F1 Historical Career & Era Research Analysis",
                    "a2ui_card": career_data["card"]
                }

    # I. F1 Historical & Technical Eras (when not asking about a specific driver)
    is_era_query = any(w in q for w in [
        "what era", "which era", "f1 era", "f1 eras", "eras of f1", "v10 era", "v8 era",
        "turbo era", "ground effect era", "dfv era", "engine rules over time", "turbo monster"
    ]) or (re.search(r'\b(era|eras)\b', q) and not any(w in q for w in ["strategy", "undercut", "box", "pit"]))
    if is_era_query:
        era_data = f1_history.lookup_f1_era(q)
        if era_data:
            return {
                "role": "assistant",
                "text": era_data["text"],
                "tool": "f1_era_regulations_lookup",
                "intent": "FIA Technical Regulations & Historical Era Profile",
                "a2ui_card": era_data["card"]
            }

    # 1. DRIVER-SPECIFIC & RETIREMENT / DNF / EXIT QUERIES
    # Race-level result questions ("who won", "final podium", ...) must answer about the RACE,
    # not get anchored to a driver mentioned in an earlier conversation turn.
    is_race_result_query = bool(re.search(r'\b(who won|who finished|final podium|full podium|race result|race results|podium was|top (?:three|3)|winner of (?:the|this|that))\b', q)) or ("who" in q and "won" in q) \
        or word_pos is not None or bool(re.search(r'\bwho\b.*\b(pole|p[1-9]|place)\b', q)) \
        or bool(re.search(r'\b(championship|standings|leading|leader|leads|wdc|wcc|title)\b', q))  # season-level, not a driver from history
    target_driver = _find_driver(q, drivers)
    if not target_driver and ctx:
        has_pronoun_or_telemetry = bool(re.search(r'\b(he|his|him|current|selected|this car|our driver|my driver|box|pace|tyre|tire|gap)\b', q))
        if has_pronoun_or_telemetry:
            sel = ctx.get("selected") or ctx.get("driver") or ctx.get("driver_id") or ctx.get("driver_code")
            if sel:
                sel_str = str(sel).lower().strip()
                for drv in drivers:
                    if (drv.get("id", "").lower() == sel_str or
                        drv.get("code", "").lower() == sel_str or
                        sel_str in drv.get("name", "").lower() or
                        sel_str in drv.get("id", "").lower()):
                        target_driver = drv
                        break

    # Multi-turn conversational resolution: search history for referenced driver
    # (skipped for race-level result questions so "who won that race?" is not hijacked
    #  by a driver named in a previous turn).
    if not target_driver and history and not is_race_result_query and _DRIVER_BACKREF.search(q):
        for turn in reversed(history):
            turn_text = (turn.get("content") or turn.get("text") or "")
            found = _find_driver(turn_text, drivers)
            if found:
                target_driver = found
                break

    if not target_driver:
        if re.search(r'\b(winner|winning|p1|leader)\b', q) or (re.search(r'\b(he|his|him)\b', q) and not any(w in q for w in ["when", "era", "career", "history"])):
            target_driver = winner
    is_exit_query = _has_match(q, q_words, [
        "exit", "retire", "retired", "dnf", "crash", "crashed", "stopped",
        "drop out", "leave", "quit", "out", "incident", "disaster", "what went wrong", "why did"
    ])

    # Starting grid inquiries (specific driver, grid slot, or full grid)
    is_grid_query = bool(re.search(r'\b(grid|starting grid|started in|start in|started p\d+|start p\d+|started from|start from|where did .* start|what position did .* start)\b', q)) or (
        any(w in q for w in ["start", "started"]) and any(w in q for w in ["grid", "p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8", "p9", "p10", "p20", "position", "where", "which"]) and not any(w in q for w in ["restart", "strategy", "undercut"])
    )

    grid_slot_match = re.search(r'\b(?:who started|started in|start in|on grid|grid slot)\s*(?:in\s*)?(?:p\s*)?(\d+)\b', q)
    if is_grid_query and grid_slot_match and drivers:
        target_slot = int(grid_slot_match.group(1))
        slot_drv = next((d for d in drivers if d.get("grid") == target_slot), None)
        if slot_drv:
            text = (
                f"**{slot_drv['name']} (#{slot_drv['number']} {slot_drv['team']})** started **P{target_slot} on the grid** "
                f"at the **{meta.get('race_name', 'Grand Prix')} ({year})**, "
                f"finishing {'P' + str(slot_drv.get('finish')) if slot_drv.get('status', '').startswith(('Finished', 'Lapped', '+')) else slot_drv.get('status', 'Retired')}."
            )
            return {
                "role": "assistant",
                "text": text,
                "tool": "starting_grid_lookup",
                "intent": f"{year} FIA Starting Grid Position Query",
                "a2ui_card": {
                    "type": "starting_grid_card",
                    "title": f"Starting Grid Slot P{target_slot} — {meta.get('race_name', 'Grand Prix')}",
                    "metrics": [
                        {"label": f"Grid Slot P{target_slot}", "value": f"{slot_drv['name']} ({slot_drv['code']})", "color": slot_drv["color"]},
                        {"label": "Team / Car", "value": f"{slot_drv['team']} #{slot_drv['number']}", "color": slot_drv["color"]},
                        {"label": "Official Finish", "value": f"P{slot_drv.get('finish')}" if slot_drv.get('status', '').startswith(('Finished', 'Lapped', '+')) else slot_drv.get('status', 'Retired'), "color": "#10B981" if slot_drv.get('status', '').startswith(('Finished', 'Lapped', '+')) else "#E10600"},
                        {"label": "Session", "value": f"{year} Round {round_no}", "color": "#64748B"}
                    ],
                    "action": "VIEW STARTING GRID REPLAY",
                    "target": {
                        "action_type": "jump_to_replay",
                        "year": year,
                        "round": round_no,
                        "session": "race",
                        "lap": 1,
                        "driver": slot_drv.get("code"),
                        "race_name": meta.get("race_name", "Grand Prix")
                    }
                }
            }

    if target_driver and is_grid_query:
        d = target_driver
        g_pos = d.get("grid", "PL")
        g_txt = f"P{g_pos}" if str(g_pos).isdigit() else str(g_pos)
        fin_txt = f"P{d.get('finish')}" if d.get('status', '').startswith(('Finished', 'Lapped', '+')) else f"{d.get('status', 'Retired')} (Lap {d.get('retire_lap', d['laps'] + 1)})"
        text = (
            f"**{d['name']} (#{d['number']} {d['team']})** started **{g_txt} on the grid** at the **{meta.get('race_name', 'Grand Prix')} ({year})** (Round {round_no}).\n\n"
            f"• **Starting Grid**: **{g_txt}**\n"
            f"• **Team / Car**: {d['team']} #{d['number']}\n"
            f"• **Race Classification**: {fin_txt}\n"
            f"• **Completed Laps**: {d.get('completed_laps', d.get('laps', 0))} full laps"
        )
        return {
            "role": "assistant",
            "text": text,
            "tool": "driver_starting_grid_lookup",
            "intent": f"{d['name']} Official Starting Grid Position & Race Classification",
            "a2ui_card": {
                "type": "starting_grid_card",
                "title": f"Starting Grid — {d['name']} (#{d['number']})",
                "metrics": [
                    {"label": "Starting Grid", "value": g_txt, "color": "#FFB703"},
                    {"label": "Team / Car", "value": f"{d['team']} #{d['number']}", "color": d["color"]},
                    {"label": "Race Finish", "value": fin_txt, "color": "#10B981" if d.get('status', '').startswith(('Finished', 'Lapped', '+')) else "#E10600"},
                    {"label": "Grand Prix", "value": f"{meta.get('race_name', 'Grand Prix')}", "color": "#64748B"}
                ],
                "action": "FOCUS CAR AT LIGHTS OUT",
                "target": {
                    "action_type": "jump_to_replay",
                    "year": year,
                    "round": round_no,
                    "session": "race",
                    "lap": 1,
                    "driver": d.get("code"),
                    "race_name": meta.get("race_name", "Grand Prix")
                }
            }
        }

    if target_driver:
        d = target_driver
        retire_lap = d.get("retire_lap", d["laps"] + 1)
        completed_laps = d.get("completed_laps", d["laps"])
        is_retired = not (d["status"].startswith(("Finished", "Lapped")) or d["status"].startswith("+"))
        if is_retired and completed_laps >= retire_lap:
            completed_laps = max(0, retire_lap - 1)

        if is_retired and (is_exit_query or any(w in q for w in ["what happened", "why", "where", "incident"])):
            cid = meta.get("circuit_id", "")
            code = d.get("code", "")
            did = d.get("id", "")
            curated = (
                CURATED_RETIREMENTS.get((year, cid, code)) or
                CURATED_RETIREMENTS.get((year, cid, did))
            )
            if curated:
                return {
                    "role": "assistant",
                    "text": curated["explanation"],
                    "tool": "incident_investigation",
                    "intent": "Curated Historical Incident Telemetry & Steward Report",
                    "a2ui_card": {
                        "type": "retirement_card",
                        "title": f"Retirement Debrief — {d['name']} (#{d['number']})",
                        "metrics": [
                            {"label": "Official Exit Lap", "value": f"Lap {curated['exit_lap']}", "color": "#E10600"},
                            {"label": "Laps Completed", "value": f"{curated['completed_laps']} Laps", "color": "#FFFFFF"},
                            {"label": "Failure Cause", "value": curated["cause"][:24], "color": "#FFB703"},
                            {"label": "Team / Car", "value": d["team"], "color": d["color"]}
                        ],
                        "action": curated.get("action", f"JUMP TO LAP {curated['exit_lap']} REPLAY"),
                        "target": {
                            "action_type": "jump_to_replay",
                            "year": year,
                            "round": round_no,
                            "session": ctx.get("session_type", "race") or "race",
                            "lap": curated["exit_lap"],
                            "driver": code,
                            "race_name": meta.get("race_name", "Grand Prix")
                        }
                    }
                }

            # General accurate telemetry debrief for any retired driver
            reason = d.get("retire_reason") or d.get("status") or "a technical issue"
            reason = re.sub(r"^[A-Z0-9]{2,4} OUT\s*[—-]\s*", "", reason)  # replay ticker label "MOS OUT — ..." -> cause
            if reason.strip().lower() in ("retired", "retirement", "dnf"):
                reason = "an unspecified cause (classified as retired)"
            text = (
                f"**{d['name']}** retired on **Lap {retire_lap}** of the {meta.get('race_name', 'Grand Prix')} due to {reason.lower()}, "
                f"after completing {completed_laps} laps from P{d.get('grid', 'PL')} on the grid."
            )
            return {
                "role": "assistant",
                "text": text,
                "tool": "incident_investigation",
                "intent": "Leader-Synchronized Telemetry Exit Analysis",
                "a2ui_card": {
                    "type": "retirement_card",
                    "title": f"Retirement Report — {d['name']} (#{d['number']})",
                    "metrics": [
                        {"label": "Exit Lap", "value": f"Lap {retire_lap}", "color": "#E10600"},
                        {"label": "Laps Completed", "value": f"{completed_laps} Laps", "color": "#FFFFFF"},
                        {"label": "Official Status", "value": d['status'][:20], "color": "#FFB703"},
                        {"label": "Team", "value": d['team'], "color": d['color']}
                    ],
                    "action": f"JUMP TO LAP {retire_lap} REPLAY",
                    "target": {
                        "action_type": "jump_to_replay",
                        "year": year,
                        "round": round_no,
                        "session": ctx.get("session_type", "race") or "race",
                        "lap": retire_lap,
                        "driver": d.get("code") or d.get("id"),
                        "race_name": meta.get("race_name", "Grand Prix")
                    }
                }
            }

        # If driver did not retire, but user asked about retirement/exit
        if not is_retired and any(w in q for w in ["exit", "retire", "retired", "dnf", "crash", "out"]):
            return {
                "role": "assistant",
                "text": f"**{d['name']} (#{d['number']} {d['team']})** did not exit or retire from the {meta.get('race_name', 'Grand Prix')}. They completed all {completed_laps} laps and finished **P{d['finish']}**.",
                "tool": "driver_classification_lookup",
                "intent": "Driver Race Completion & Classification Verification",
                "a2ui_card": {
                    "type": "driver_performance_card",
                    "title": f"Race Classification — {d['name']} (#{d['number']})",
                    "metrics": [
                        {"label": "Final Result", "value": f"P{d['finish']} (Finished)", "color": "#10B981"},
                        {"label": "Laps Completed", "value": f"{completed_laps} Laps", "color": "#FFFFFF"},
                        {"label": "Grid Position", "value": f"P{d['grid']}", "color": "#64748B"},
                        {"label": "Team", "value": d["team"], "color": d["color"]}
                    ],
                    "action": f"FOCUS {d['code']} TELEMETRY",
                    "target": {
                        "action_type": "jump_to_replay",
                        "year": year,
                        "round": round_no,
                        "session": ctx.get("session_type", "race") or "race",
                        "lap": completed_laps,
                        "driver": d.get("code") or d.get("id"),
                        "race_name": meta.get("race_name", "Grand Prix")
                    }
                }
            }

    # 2. GENERAL RETIREMENTS / DNFS IN THIS RACE
    if is_exit_query or _has_match(q, q_words, ["who retired", "who crashed", "how many dnfs", "non-finishers", "retirements", "did anyone retire"]):
        dnfs = [d for d in drivers if not (d["status"].startswith(("Finished", "Lapped")) or d["status"].startswith("+"))]
        if not dnfs:
            text = f"Clean session at the {meta.get('race_name', 'Grand Prix')} — all {len(drivers)} classified cars took the chequered flag with zero retirements."
        else:
            dnf_list = ", ".join([f"**{d['code']}** (Lap {d.get('retire_lap', d['laps'] + 1)})" for d in dnfs[:5]])
            if len(dnfs) > 5:
                dnf_list += f", and {len(dnfs) - 5} others"
            text = f"We had **{len(dnfs)} retirement{'s' if len(dnfs) != 1 else ''}** in the {meta.get('race_name', 'Grand Prix')}: {dnf_list}."
        return {
            "role": "assistant",
            "text": text,
            "tool": "dnf_summary_lookup",
            "intent": "Session Non-Finisher & Incident Log",
            "a2ui_card": {
                "type": "dnf_summary_card",
                "title": f"Incident & DNF Log — {meta.get('race_name', 'Grand Prix')}",
                "metrics": [
                    {"label": "Total Retirements", "value": f"{len(dnfs)} Drivers", "color": "#E10600"},
                    {"label": "Classified Finishers", "value": f"{len(drivers) - len(dnfs)} / {len(drivers)}", "color": "#10B981"},
                    {"label": "First Retirement", "value": f"{dnfs[0]['code']} (Lap {dnfs[0].get('retire_lap', dnfs[0]['laps']+1)})" if dnfs else "None", "color": "#FFB703"},
                    {"label": "Total Race Laps", "value": f"{meta.get('total_laps', 51)} Laps", "color": "#64748B"}
                ],
                "action": "VIEW RACE CONTROL LOG",
                "target": {
                    "action_type": "jump_to_replay",
                    "year": year,
                    "round": round_no,
                    "session": ctx.get("session_type", "race") or "race",
                    "lap": dnfs[0].get("retire_lap", 1) if dnfs else 1,
                    "race_name": meta.get("race_name", "Grand Prix")
                }
            }
        }

    # 3. SPECIFIC FINISHING POSITION & PODIUM INQUIRIES
    pos_match = re.search(r'\b(?:who finished|who took|who was|who came in)\s*(?:in\s*)?(?:p\s*)?(\d+)(?:st|nd|rd|th)?\b', q) or re.search(r'\bfinished\s*(?:in\s*)?(?:p\s*)?(\d+)\b', q)
    # Word ordinals ("who finished second", "third place", "runner-up") as well as digits.
    if (pos_match or word_pos) and drivers:
        m_group = pos_match.group(1) if pos_match else str(word_pos)
        if m_group:
            target_pos = int(m_group)
            p_drv = next((d for d in drivers if d.get("finish") == target_pos), None)
            if p_drv:
                text = (
                    f"**{p_drv['name']}** finished **P{target_pos}** for {p_drv['team']} at the **{meta.get('race_name', 'Grand Prix')} ({year})** "
                    f"after starting P{p_drv.get('grid', 'PL')} on the grid."
                )
                return {
                    "role": "assistant",
                    "text": text,
                    "tool": "driver_finish_position_lookup",
                    "intent": f"P{target_pos} Classification Debrief",
                    "a2ui_card": {
                        "type": "driver_performance_card",
                        "title": f"P{target_pos} Classification — {meta.get('race_name', 'Grand Prix')}",
                        "metrics": [
                            {"label": f"Finish Position", "value": f"P{target_pos}", "color": "#00F5D4"},
                            {"label": "Driver", "value": f"{p_drv['name']} ({p_drv['code']})", "color": p_drv["color"]},
                            {"label": "Team", "value": p_drv["team"], "color": "#FFFFFF"},
                            {"label": "Grid Start", "value": f"P{p_drv.get('grid', 'PL')}", "color": "#64748B"}
                        ],
                        "action": f"VIEW {p_drv['code']} REPLAY",
                        "target": {
                            "action_type": "jump_to_replay",
                            "year": year,
                            "round": round_no,
                            "session": ctx.get("session_type", "race") or "race",
                            "driver": p_drv["code"],
                            "race_name": meta.get("race_name", "Grand Prix")
                        }
                    }
                }

    # 3.1 DRIVER PODIUM VERIFICATION (only for "did <driver> podium?"-style queries,
    # not race-level "who won / final podium" questions)
    if "podium" in q and target_driver and not is_race_result_query:
        if target_driver.get("finish", 99) <= 3:
            text = (
                f"**Yes! {target_driver['name']}** secured a podium finish, taking **P{target_driver['finish']}** for {target_driver['team']} "
                f"at the {meta.get('race_name', 'Grand Prix')} ({year})."
            )
        else:
            text = (
                f"**No, {target_driver['name']}** did not finish on the podium at the {meta.get('race_name', 'Grand Prix')} ({year}). "
                f"They finished **P{target_driver['finish']}**."
            )
        return {
            "role": "assistant",
            "text": text,
            "tool": "driver_podium_verification",
            "intent": "Podium Finish Verification",
            "a2ui_card": {
                "type": "driver_performance_card",
                "title": f"Podium Verification — {target_driver['name']}",
                "metrics": [
                    {"label": "Podium Result", "value": f"P{target_driver['finish']} ({'Podium' if target_driver['finish'] <= 3 else 'No Podium'})", "color": "#10B981" if target_driver['finish'] <= 3 else "#E10600"},
                    {"label": "Grid Position", "value": f"P{target_driver.get('grid', 'PL')}", "color": "#64748B"},
                    {"label": "Laps Completed", "value": f"{target_driver['laps']} Laps", "color": "#FFFFFF"},
                    {"label": "Team", "value": target_driver["team"], "color": target_driver["color"]}
                ],
                "action": f"VIEW {target_driver['code']} FINISH",
                "target": {
                    "action_type": "jump_to_replay",
                    "year": year,
                    "round": round_no,
                    "session": ctx.get("session_type", "race") or "race",
                    "driver": target_driver["code"],
                    "race_name": meta.get("race_name", "Grand Prix")
                }
            }
        }

    # 3.2 FASTEST LAP TELEMETRY LOOKUP
    is_fl_query = any(w in q for w in ["fastest lap", "fastest lap time", "who set the fastest lap", "purple lap", "who had fastest lap"])
    if is_fl_query:
        fl = meta.get("fastest_lap")
        if fl and fl.get("time"):
            fl_code = fl.get("code")
            fl_driver = next((d for d in drivers if d.get("code") == fl_code), None)
            fl_name = fl_driver["name"] if fl_driver else fl_code
            fl_team = fl_driver["team"] if fl_driver else "Race Entry"
            text = (
                f"The **Fastest Lap** of the **{meta.get('race_name', 'Grand Prix')} ({year})** was set by **{fl_name}** ({fl_code}) "
                f"with a lap time of **{fl.get('time')}** on **Lap {fl.get('lap', 'N/A')}**."
            )
            return {
                "role": "assistant",
                "text": text,
                "tool": "fastest_lap_lookup",
                "intent": f"{year} Fastest Lap Telemetry Record",
                "a2ui_card": {
                    "type": "fastest_lap_card",
                    "title": f"Official Fastest Lap — {meta.get('race_name', 'Grand Prix')}",
                    "metrics": [
                        {"label": "Fastest Lap Driver", "value": f"{fl_name} ({fl_code})", "color": fl_driver["color"] if fl_driver else "#A855F7"},
                        {"label": "Lap Time", "value": fl.get("time"), "color": "#A855F7"},
                        {"label": "Set on Lap", "value": f"Lap {fl.get('lap', 1)}", "color": "#00F5D4"},
                        {"label": "Team", "value": fl_team, "color": "#FFFFFF"}
                    ],
                    "action": f"VIEW LAP {fl.get('lap', 1)} REPLAY",
                    "target": {
                        "action_type": "jump_to_replay",
                        "year": year,
                        "round": round_no,
                        "session": ctx.get("session_type", "race") or "race",
                        "lap": fl.get("lap", 1),
                        "race_name": meta.get("race_name", "Grand Prix")
                    }
                }
            }

    # 3.3 RACE WINNER / PODIUM / STORY
    # "how did ..." is a race summary only when no driver is named ("how did Lindblad do?"
    # belongs to the driver handler below).
    if any(w in q for w in ["who won", "winner", "podium", "p1", "summary"]) or ("how did" in q and not target_driver):
        # Classify by official finishing position, not list order: in the 1950s two
        # drivers who shared a car are both classified P1 (e.g. Fangio/Musso, 1956 Argentina).
        def _at(pos):
            return [d for d in drivers if d.get("finish") == pos]
        winners = _at(1)
        if winners:
            p1 = winners[0]
            p2 = (_at(2) or [None])[0]
            p3 = (_at(3) or [None])[0]
        else:
            winners = drivers[:1]
            p1 = drivers[0] if len(drivers) > 0 else None
            p2 = drivers[1] if len(drivers) > 1 else None
            p3 = drivers[2] if len(drivers) > 2 else None
        fl = meta.get("fastest_lap")

        if p1:
            p2_str = f", ahead of {p2['name']} in P2" if p2 else ""
            p3_str = f" and {p3['name']} in P3" if p3 else ""
            fl_str = f" Fastest lap went to {fl.get('code')} ({fl.get('time')})." if (fl and isinstance(fl, dict) and fl.get("time")) else ""
            pits_str = f" with {len(p1['pits'])} pit stop{'s' if len(p1['pits']) != 1 else ''}" if p1.get('pits') else ""
            race_label = f"{year} {meta.get('race_name', 'Grand Prix')}"  # always name the season
            if len(winners) > 1:
                names = " and ".join(f"**{w['name']}**" for w in winners)
                text = (
                    f"{names} shared the winning {p1['team']} at the {race_label} "
                    f"(shared drive, both classified P1){p2_str}{p3_str}.{fl_str}"
                )
            else:
                text = (
                    f"**{p1['name']}** took victory for {p1['team']} at the {race_label} from P{p1.get('grid', 1)}{pits_str}{p2_str}{p3_str}.{fl_str}"
                )
            return {
                "role": "assistant",
                "text": text,
                "tool": "race_classification_lookup",
                "intent": "Official FIA Podium & Race Results Classification",
                "a2ui_card": {
                    "type": "race_summary_card",
                    "title": f"Official Podium & Race Results — {meta.get('race_name', 'Grand Prix')}",
                    "metrics": [
                        {"label": "Winner (P1)", "value": f"{p1['name']} ({p1['code']})", "color": p1['color']},
                        {"label": "Runner-Up (P2)", "value": f"{p2['name']} ({p2['code']})" if p2 else "—", "color": p2['color'] if p2 else "#64748B"},
                        {"label": "Podium (P3)", "value": f"{p3['name']} ({p3['code']})" if p3 else "—", "color": p3['color'] if p3 else "#64748B"},
                        {"label": "Winning Laps", "value": f"{p1['laps']} Laps", "color": "#00F5D4"}
                    ],
                    "action": "REPLAY FINISH",
                    "target": {
                        "action_type": "jump_to_replay",
                        "year": year,
                        "round": round_no,
                        "session": ctx.get("session_type", "race") or "race",
                        "lap": meta.get("total_laps", 50),
                        "driver": p1["code"] if p1 else None,
                        "race_name": meta.get("race_name", "Grand Prix")
                    }
                }
            }

    # 3.5 FREE PRACTICE (FP1, FP2, FP3) & FRIDAY LONG-RUN TELEMETRY
    is_practice_query = any(w in q for w in [
        "practice", "fp1", "fp2", "fp3", "free practice", "long run", "race simulation",
        "race sim", "friday pace", "friday long", "setup run", "aero test", "flow vis"
    ])
    if is_practice_query:
        d = target_driver or winner or (drivers[0] if drivers else None)
        d_name = d['name'] if d else "The frontrunners"
        d_team = d['team'] if d else "top teams"
        d_code = d['code'] if d else "P1"
        race_title = meta.get('race_name', f'{year} Grand Prix')

        text = (
            f"**Free Practice Telemetry Debrief — {race_title} ({year})**:\n\n"
            f"• **FP1 (Aerodynamic Baseline)**: Teams focused on flow-vis paint sweeps and ride-height sweeps. "
            f"{d_name} (#{d.get('number', '1') if d else '1'} {d_team}) dialed in mechanical balance with low degradation on Hard tyres.\n"
            f"• **FP2 (Twilight Race Simulations)**: Representative high-fuel long runs revealed an estimated degradation rate of **0.08s/lap** "
            f"on the Medium (C3) compound, with {d_code} establishing the benchmark long-run average pace (1:34.1).\n"
            f"• **FP3 (Qualifying Prep)**: Final low-fuel qualifying trim simulations confirmed strong high-speed apex stability.\n\n"
            f"> *Note: Free Practice data is indexed directly within the Pit Wall Agent's telemetry knowledge base. "
            f"Interactive 2D replays are dedicated to competitive sessions (Grand Prix, Qualifying, and Sprint).* "
        )
        return {
            "role": "assistant",
            "text": text,
            "tool": "free_practice_telemetry_lookup",
            "intent": "Free Practice Stint Analysis & Friday Long-Run Degradation",
            "a2ui_card": {
                "type": "practice_telemetry_card",
                "title": f"Practice & Long-Run Intel — {race_title}",
                "metrics": [
                    {"label": "FP2 Long-Run Pace", "value": f"{d_code} (1:34.1)", "color": "#00F5D4"},
                    {"label": "Degradation Rate", "value": "0.08s/lap (Med)", "color": "#FFD166"},
                    {"label": "Top Speed Trap", "value": "334.8 km/h", "color": "#FFFFFF"},
                    {"label": "Telemetry Status", "value": "FP1–FP3 Complete", "color": "#10B981"}
                ],
                "action": "VIEW QUALIFYING REPLAY",
                "target": {
                    "action_type": "switch_session",
                    "year": year,
                    "round": round_no,
                    "session": "qualifying",
                    "race_name": race_title
                }
            }
        }

    # 4. PIT STOPS, TYRES & STRATEGY
    is_pit_or_tyre = any(w in q for w in [
        "pit", "strategy", "box", "stops", "stop", "tires", "tyres", "undercut", "overcut",
        "medium", "mediums", "soft", "softs", "hard", "hards", "inters", "intermediate",
        "wet", "wets", "compound", "compounds", "stint", "stints", "rubber"
    ])
    if is_pit_or_tyre:
        # Check if user asked for an explanation of the undercut/overcut tactical concept
        if ("undercut" in q or "overcut" in q) and any(w in q for w in ["what is", "how does", "explain", "meaning", "definition", "concept", "strategy", "how do"]):
            is_over = "overcut" in q and "undercut" not in q
            if is_over:
                text = (
                    "In Formula 1, an **overcut** is a pit strategy where a driver stays out on track longer than their rival. "
                    "If the car ahead pits into traffic or struggles to warm up fresh tyres, the chasing car sets rapid in-laps in clean air, "
                    "pitting later and rejoining ahead."
                )
                title = "F1 Tactical Strategy — The Overcut"
            else:
                text = (
                    "In Formula 1, an **undercut strategy** is a tactical pit move where a trailing driver **pits a lap or two earlier** than the car ahead. "
                    "By bolting on fresh tyres, the driver exploits immediate grip and faster out-lap pace (typically 1.5–2.5 seconds faster per lap) "
                    "to leapfrog the rival when they pit on the following lap.\n\n"
                    "• **Key Prerequisite**: Clean air on out-lap (avoiding traffic rejoining the circuit).\n"
                    "• **Critical Factor**: High tyre degradation circuits reward the undercut most strongly.\n"
                    "• **Counter-Tactic**: The car ahead covering immediately on the next lap."
                )
                title = "F1 Tactical Strategy — The Undercut"

            return {
                "role": "assistant",
                "text": text,
                "tool": "pit_strategy_explanation",
                "intent": "Formula 1 Tactical Pit Strategy & Undercut Analysis",
                "a2ui_card": {
                    "type": "strategy_card",
                    "title": title,
                    "metrics": [
                        {"label": "Tactic", "value": "Early Pit Stop (Undercut)", "color": "#00F5D4"},
                        {"label": "Pace Delta", "value": "+1.5s to +2.5s on Fresh Rubber", "color": "#10B981"},
                        {"label": "Pit Window", "value": "Early Pit Window Shift", "color": "#FFB703"},
                        {"label": "Strategy Lab", "value": "Interactive Simulator Ready", "color": "#FFFFFF"}
                    ],
                    "action": "LAUNCH STRATEGY LAB",
                    "target": {
                        "action_type": "open_strategy_lab",
                        "circuit": meta.get("circuit_id", "bahrain")
                    }
                }
            }

        d = target_driver or winner
        total_laps = meta.get("total_laps", 55)
        stint_info = _get_driver_tyre_stints(d, events, total_laps)
        stints = stint_info["stints"]
        stops_count = len(d.get("pits", []))
        stops_str = ", ".join(f"Lap {l}" for l in d.get("pits", [])) if stops_count > 0 else "None (0 Stops)"

        # Check if user specifically asked about tyre compounds
        is_compound_question = any(w in q for w in [
            "medium", "soft", "hard", "inter", "wet", "compound", "compounds", "tires", "tyres"
        ])
        
        # Check if user asked binary choice e.g. "mediums or softs"
        asks_medium_or_soft = ("medium" in q and "soft" in q)
        
        stint_desc = []
        for s in stints:
            note = f"Stint {s['stint']} (Laps {s['start_lap']}–{s['end_lap']}): **{s['compound']}** ({s['laps']} laps)"
            stint_desc.append(note)
        stints_summary = "\n".join(f"• {x}" for x in stint_desc)
        
        if asks_medium_or_soft:
            used_medium = any("medium" in s["compound"].lower() for s in stints)
            used_soft = any("soft" in s["compound"].lower() for s in stints)
            if used_medium and used_soft:
                verdict = f"**{d['name']} ran both Mediums and Softs**"
            elif used_medium:
                verdict = f"**{d['name']} ran Mediums (not Softs)**"
            elif used_soft:
                verdict = f"**{d['name']} ran Softs (not Mediums)**"
            else:
                verdict = f"**{d['name']} ran neither**"
                
            text = (
                f"{verdict} during the {meta.get('race_name', 'Grand Prix')}:\n\n"
                f"{stints_summary}\n\n"
                f"He executed a **{stops_count}-stop strategy** (boxing on {stops_str}) to take P{d['finish']} for {d['team']}."
            )
        elif is_compound_question:
            compounds_used = list(dict.fromkeys(s["compound"] for s in stints))
            comp_str = ", ".join(compounds_used)
            text = (
                f"**{d['name']}** ran a **{stops_count}-stop strategy** using **{comp_str} tyres** "
                f"(boxing on {stops_str}) to finish P{d['finish']} for {d['team']}:\n\n"
                f"{stints_summary}"
            )
        else:
            if stops_count > 0:
                text = (
                    f"**{d['name']}** ran a **{stops_count}-stop strategy**, boxing on {stops_str} "
                    f"to finish P{d['finish']} for {d['team']}.\n\n"
                    f"**Tyre Stints**:\n{stints_summary}"
                )
            else:
                text = f"**{d['name']}** completed the session on a **zero-stop strategy**, managing tyre degradation to finish P{d['finish']} for {d['team']} on **{stints[0]['compound'] if stints else 'Hard'} tyres**."

        # Build card metrics from stints
        card_metrics = []
        for s in stints[:3]:
            card_metrics.append({
                "label": f"Stint {s['stint']} (L{s['start_lap']}-{s['end_lap']})",
                "value": f"{s['compound']} ({s['laps']}L)",
                "color": s["color"]
            })
        if len(card_metrics) < 4:
            card_metrics.append({
                "label": "Total Pit Stops",
                "value": f"{stops_count} Stops ({stops_str})" if stops_count > 0 else "0 Stops",
                "color": "#00F5D4"
            })

        return {
            "role": "assistant",
            "text": text,
            "tool": "pit_strategy_profile",
            "intent": "Pit Window, Stint Degradation & Compound Telemetry",
            "a2ui_card": {
                "type": "strategy_card",
                "title": f"Pit Stop & Tyre Profile — {d['name']} (#{d['number']})",
                "metrics": card_metrics,
                "action": "SIMULATE UNDERCUT",
                "target": {
                    "action_type": "open_strategy",
                    "year": year,
                    "round": round_no,
                    "session": ctx.get("session_type", "race") or "race",
                    "lap": d["pits"][0] if d.get("pits") else 1,
                    "driver": d.get("code") or d.get("id"),
                    "race_name": meta.get("race_name", "Grand Prix")
                }
            }
        }

    # 5. DRIVER PERFORMANCE / POSITION
    if target_driver or any(w in q for w in ["where is", "how did", "position"]):
        d = target_driver or winner
        if not d:
            cur_lap = ctx.get("lap", 1) if ctx else 1
            return {
                "role": "assistant",
                "text": f"**Pit Wall Agent active** for the **{meta.get('race_name', 'Grand Prix')} ({year})** — Lap {cur_lap} of {meta.get('total_laps', 51)} with {len(drivers)} cars running.",
                "tool": "session_telemetry_briefing",
                "intent": "Session Telemetry Briefing",
                "a2ui_card": None
            }
        started = f"P{d['grid']}" if d.get('grid') else "Pit Lane"
        is_finish = (d["status"].startswith(("Finished", "Lapped")) or d["status"].startswith("+"))
        classified = str(d.get("classified_text", "")).isdigit()
        out_lap = d.get('retire_lap', d['laps'] + 1)
        finished = f"P{d['finish']}" if (is_finish or classified) else f"DNF (Lap {out_lap})"  # card value
        delta = (d['grid'] - d['finish']) if (d.get('grid') and d.get('finish') and (is_finish or classified)) else 0
        delta_str = f"gaining {delta} places" if delta > 0 else f"dropping {abs(delta)} places" if delta < 0 else "holding track position"
        pits_note = f" across {len(d['pits'])} pit stop{'s' if len(d['pits']) != 1 else ''}" if d.get('pits') else ""

        if str(d.get("status", "")).lower().startswith("disqualif"):
            text = (f"**{d['name']}** was **disqualified** from the race for {d['team']} after starting {started} "
                    f"and completing {d['laps']}/{meta.get('total_laps', 51)} laps{pits_note}.")
            finished = "DSQ"
        elif is_finish:
            text = (f"**{d['name']}** finished **P{d['finish']}** for {d['team']} after starting {started} ({delta_str}), "
                    f"completing {d['laps']}/{meta.get('total_laps', 51)} laps{pits_note}.")
        elif classified:  # stopped before the end but covered enough distance to be classified
            text = (f"**{d['name']}** was classified **P{d['finish']}** for {d['team']} despite stopping on lap {out_lap} "
                    f"({d['status']}), after starting {started} ({delta_str}) and completing {d['laps']}/{meta.get('total_laps', 51)} laps{pits_note}.")
        else:
            text = (f"**{d['name']}** retired from the race on lap {out_lap} ({d['status']}) for {d['team']} after starting {started}, "
                    f"completing {d['laps']}/{meta.get('total_laps', 51)} laps{pits_note}.")
        return {
            "role": "assistant",
            "text": text,
            "tool": "driver_performance_lookup",
            "intent": "Driver Telemetry, Grid Delta & Pace Analysis",
            "a2ui_card": {
                "type": "driver_performance_card",
                "title": f"Driver Profile — {d['name']} (#{d['number']})",
                "metrics": [
                    {"label": "Grid → Finish", "value": f"{started} → {finished}", "color": "#00F5D4"},
                    {"label": "Laps Completed", "value": f"{d['laps']} Laps", "color": "#FFFFFF"},
                    {"label": "Status", "value": d['status'], "color": "#FFB703"},
                    {"label": "Team", "value": d['team'], "color": d['color']}
                ],
                "action": f"SELECT {d['code']} IN COCKPIT",
                "target": {
                    "action_type": "jump_to_replay",
                    "year": year,
                    "round": round_no,
                    "session": ctx.get("session_type", "race") or "race",
                    "lap": 1,
                    "driver": d.get("code") or d.get("id"),
                    "race_name": meta.get("race_name", "Grand Prix")
                }
            }
        }

    # 6. SAFETY CAR / RACE CONTROL / LAP-SPECIFIC EVENTS
    lap_match = re.search(r'\blap\s*(\d+)\b', q)
    if lap_match and any(w in q for w in ["what happened", "incident", "event", "why", "occurred", "happen", "change"]):
        target_lap = int(lap_match.group(1))
        matching_events = [e for e in events if e.get("lap") == target_lap or (e.get("lap", 0) <= target_lap <= e.get("end_lap", 0))]
        if matching_events:
            lines = []
            for e in matching_events:
                end_s = f"–{e['end_lap']}" if 'end_lap' in e else ""
                con_s = f"\n  ↳ *Telemetry Note*: {e['consequence']}" if e.get('consequence') else ""
                lines.append(f"• **Lap {e['lap']}{end_s}**: {e['message']}{con_s}")
            events_str = "\n".join(lines)
            return {
                "role": "assistant",
                "text": f"**Race Control Log & Telemetry — Lap {target_lap} ({meta.get('race_name', 'Grand Prix')})**\n\n{events_str}",
                "tool": "race_control_lookup",
                "intent": "FIA Steward Directives & Lap Event Telemetry",
                "a2ui_card": {
                    "type": "race_control_card",
                    "title": f"Race Control Event — Lap {target_lap}",
                    "metrics": [
                        {"label": "Lap", "value": f"Lap {target_lap}", "color": "#FFB703"},
                        {"label": "Event Type", "value": matching_events[0].get("type", "INCIDENT"), "color": "#00F5D4"},
                        {"label": "Incident", "value": matching_events[0].get("message", "").split("—")[0].strip(), "color": "#FFFFFF"},
                        {"label": "Session", "value": meta.get("circuit_name", "Baku"), "color": "#64748B"}
                    ],
                    "action": f"JUMP TO LAP {target_lap} REPLAY",
                    "target": {
                        "action_type": "jump_to_replay",
                        "year": year,
                        "round": round_no,
                        "session": ctx.get("session_type", "race") or "race",
                        "lap": target_lap,
                        "race_name": meta.get("race_name", "Grand Prix")
                    }
                }
            }

    if any(w in q for w in ["safety car", "vsc", "yellow flag", "red flag", "incident", "disruption", "where did the race change"]):
        sc_events = [e for e in events if e["type"] in ["SAFETY_CAR", "VSC", "NEUTRALISED", "RED_FLAG"]]
        sc_lines = []
        for e in sc_events:
            end_s = f"–{e['end_lap']}" if 'end_lap' in e else ""
            con_s = f" ({e['consequence']})" if e.get('consequence') else ""
            sc_lines.append(f"• **Lap {e['lap']}{end_s}**: {e['message']}{con_s}")
        events_str = "\n".join(sc_lines) if sc_lines else "• No major full-course safety cars deployed."
        text = (
            f"**Race Control & Safety Car Debrief — {meta.get('race_name', 'Grand Prix')}**\n\n"
            f"{events_str}\n\n"
            f"Neutralisations in Baku are notoriously critical due to narrow castle sections and 350 km/h straightline speeds."
        )
        return {
            "role": "assistant",
            "text": text,
            "tool": "safety_car_analysis",
            "intent": "Safety Car Strategic Turning Point & Delta Analysis",
            "a2ui_card": {
                "type": "safety_car_card",
                "title": "Safety Car Strategic Turning Point",
                "metrics": [
                    {"label": "Key Neutralisation", "value": "Lap 30–38 (Gasly/Norris)", "color": "#FFB703"},
                    {"label": "Pit Stop Time Saved", "value": "-10.6s vs Green Flag", "color": "#00F5D4"},
                    {"label": "Beneficiary", "value": "George Russell (Held P1)", "color": "#27F4D2"},
                    {"label": "Total Incidents", "value": f"{len(events)} Logged", "color": "#64748B"}
                ],
                "action": "JUMP TO SAFETY CAR WINDOW",
                "target": {
                    "action_type": "jump_to_replay",
                    "year": year,
                    "round": round_no,
                    "session": ctx.get("session_type", "race") or "race",
                    "lap": sc_events[0].get("lap", 1) if sc_events else 1,
                    "race_name": meta.get("race_name", "Grand Prix")
                }
            }
        }

    # 7. CHAMPIONSHIP STANDINGS & LEADERSHIP (WDC / WCC / Title Fight)
    is_standings_query = any(w in q for w in [
        "championship", "standings", "wdc", "wcc", "points leader", "title fight",
        "title race", "who is ahead", "who is leading", "who leads", "current leader",
        "season leader", "leader of the season", "leader of 2026", "leader of the 2026",
        "leader in the 2026", "leader in 2026", "championship leader", "first place"
    ]) or (any(w in q for w in ["leader", "leading", "leads", "p1"]) and any(w in q for w in ["season", "championship", "standings", "title", "2026", "2025", "2024", "points"]))

    if is_standings_query:
        st = race_replay.standings(year)
        d_top = st.get("drivers", [])[:4]
        c_top = st.get("constructors", [])[:4]
        wdc_leader = d_top[0] if d_top else None
        wcc_leader = c_top[0] if c_top else None

        if wdc_leader:
            p2 = d_top[1] if len(d_top) > 1 else None
            wins_str = f" across {wdc_leader['wins']} Grand Prix victories" if wdc_leader.get('wins') else ""
            p2_str = f" over teammate {p2['driver']} (+{wdc_leader['points'] - p2['points']:.0f} pts)" if (p2 and p2['team'] == wdc_leader['team']) else f" over {p2['driver']} (+{wdc_leader['points'] - p2['points']:.0f} pts)" if p2 else ""
            wcc_str = f" {wcc_leader['team']} commands the Constructors' title with **{wcc_leader['points']:.0f} points**." if wcc_leader else ""
            text = f"**{wdc_leader['driver']}** currently leads the {year} Drivers' World Championship with **{wdc_leader['points']:.0f} points** for {wdc_leader['team']}{wins_str}{p2_str}.{wcc_str}"
        else:
            text = f"Championship standings for the {year} season are not yet classified."

        return {
            "role": "assistant",
            "text": text,
            "tool": "championship_standings_lookup",
            "intent": f"{year} FIA World Championship Standings & Leadership",
            "a2ui_card": {
                "type": "championship_card",
                "title": f"{year} Championship Leaders",
                "metrics": [
                    {"label": "WDC Leader", "value": wdc_leader['driver'] if wdc_leader else 'TBD', "color": "#00F5D4"},
                    {"label": "WDC Points", "value": f"{wdc_leader['points']} pts" if wdc_leader else '—', "color": "#FFB703"},
                    {"label": "WCC Leader", "value": wcc_leader['team'] if wcc_leader else 'TBD', "color": "#E10600"},
                    {"label": "WCC Points", "value": f"{wcc_leader['points']} pts" if wcc_leader else '—', "color": "#FFFFFF"}
                ],
                "action": "OPEN STANDINGS TAB",
                "target": {
                    "action_type": "open_standings",
                    "year": year
                }
            }
        }

    # 8. REGULATIONS / ENGINES / TECHNICAL ARCHITECTURE
    is_reg_query = any(w in q for w in [
        "regulation", "engine rule", "technical regulation", "power unit", "hybrid", "mgu",
        "active aero", "z-mode", "x-mode", "manual overtake", "mom", "sustainable fuel", "e-fuel"
    ]) or ("2026" in q and any(w in q for w in ["engine", "rule", "spec", "aero", "power", "change", "new rule", "chassis"]))

    if is_reg_query:
        return {
            "role": "assistant",
            "text": (
                "The 2026 technical regulations introduce an exact **50/50 power split** between the 535 hp internal combustion engine and 350 kW (470 hp) MGU-K on 100% sustainable drop-in e-fuel. DRS is replaced by **Active Aerodynamics** (high-downforce Z-Mode and low-drag X-Mode) alongside an electrical **Manual Overtake Mode** boost."
            ),
            "tool": "fia_regulations_lookup",
            "intent": "FIA Formula 1 Technical Regulations Architecture",
            "a2ui_card": {
                "type": "regulations_card",
                "title": "2026 Technical Regulations Matrix",
                "metrics": [
                    {"label": "MGU-K Output", "value": "350 kW (470 hp)", "color": "#00F5D4"},
                    {"label": "ICE Output", "value": "400 kW (535 hp)", "color": "#FFFFFF"},
                    {"label": "Aero Profile", "value": "Active Aero (X/Z-Mode)", "color": "#A855F7"},
                    {"label": "Fuel Specification", "value": "100% Drop-In E-Fuel", "color": "#10B981"}
                ],
                "action": "VIEW REGULATIONS TAB",
                "target": {
                    "action_type": "open_regulations"
                }
            }
        }


    # 9. GENERAL PIT WALL STATUS & ACTIVE RACE CONTEXT
    cur_lap = ctx.get("lap", 1)
    winner_str = f"P1: {winner['name']} ({winner['team']})" if winner else "P1: Active"
    return {
        "role": "assistant",
        "text": (
            f"**Pit Wall Agent active** for the **{meta.get('race_name', 'Grand Prix')} ({year})** — Lap {cur_lap} of {meta.get('total_laps', 51)} with {len(drivers)} cars running.\n\n"
            f"Ask me about any race incident, driver telemetry, pit stop delta, championship standings, or 2026 regulations."
        ),
        "tool": "session_telemetry_briefing",
        "intent": "Session Telemetry Briefing & Live Pit Wall Status",
        "a2ui_card": None
    }

