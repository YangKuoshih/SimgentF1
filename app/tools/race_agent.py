"""
SimGent - Pit Wall Race Engineer AI Agent
Answers queries grounded in real session telemetry, classifications, lap-by-lap timing,
Race Control events, driver retirements, pit strategies, championship standings,
and FIA technical regulations. Returns authoritative text plus rich A2UI cards.
"""

import datetime
import logging
import os
import re
import contextvars
from typing import Dict, Any, List, Optional, Tuple
from app.agent import content as _content
from app.tools import race_replay, f1_telemetry, f1_history
from app.tools import jolpica_sync as J
from app.tools.agent_memory import memory_manager

logger = logging.getLogger("simgent.agent")

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
    # A reply to a clarifying question ("the second one", "Ralf") -> the option's full question
    from app.agent.gate import match_clarification
    picked = match_clarification(query, history) if _depth == 0 else None
    if picked:
        return picked
    return _resolve_follow_up(query, history, _depth)


def _resolve_follow_up(query: str, history: Optional[List[Dict[str, Any]]], _depth: int = 0) -> str:
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
        f"> *Source: {year} final standings data (Jolpica-F1).*"
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
    # Full race names first, longest first: "the 1976 United States Grand Prix" is Watkins Glen,
    # not the "United States Grand Prix West" that the word "united" also matches
    for r in sorted(races, key=lambda x: -len(x.get("race_name", ""))):
        rn = r.get("race_name", "").lower()
        if len(rn) >= 6 and re.search(r'\b' + re.escape(rn) + r'\b', q):
            return r["round"]
    # Then: direct check of race tokens in query
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


# Curated retirement write-ups live in content/retirements/*.md, with their sources; the
# laps they state are checked against Jolpica-F1 in tests/test_content.py.
CURATED_RETIREMENTS = _content.retirements()



_SESSION_NAMES = {"sprint_qualifying": "Sprint Qualifying", "sprint": "Sprint", "qualifying": "Qualifying"}
# Race-data tools that still give a useful general answer without a race (e.g. how an
# undercut works); everything else in _RACE_DATA_TOOLS needs the race's result.
_GENERAL_WITHOUT_A_RACE = {"pit_strategy_explanation"}
# Set by _answer_core when the race in question has no result yet (year, schedule entry).
_NO_RACE_RESULT: contextvars.ContextVar = contextvars.ContextVar("no_race_result", default=None)


def _race_not_run(year: int, r: Dict[str, Any]) -> Dict[str, Any]:
    """Reply for a Grand Prix with no result yet (instead of answering from another race)."""
    name = r.get("race_name", "Grand Prix")
    have = [_SESSION_NAMES[x] for x in race_replay.WEEKEND_ORDER if x in (r.get("available") or []) and x in _SESSION_NAMES]
    so_far = (f" Results so far this weekend: **{', '.join(have)}** — switch the session or ask about "
              f"{'it' if len(have) == 1 else 'them'} directly (e.g. \"who took {'sprint ' if 'Sprint Qualifying' in have else ''}pole?\").") if have else ""
    when = f" (race day {r['date']})" if r.get("date") else ""
    return {
        "role": "assistant",
        "text": f"There's no race result for the **{year} {name}** yet{when}, so I can't answer that from the Grand Prix.{so_far}",
        "tool": "race_not_run",
        "intent": f"{year} {name} — no race result yet",
        "a2ui_card": None,
    }


def _sprint_weekends_text(year: int) -> str:
    sprints = [r for r in race_replay.season_races(year) if r.get("has_sprint")]
    if not sprints:
        return f"There were no Sprints in {year}."
    return f"Sprint weekends in {year}: " + ", ".join(
        f"R{r['round']} {re.sub(r' Grand Prix', '', r.get('race_name', ''))}" for r in sprints) + "."


def _no_sprint_reply(year: int, round_no: Optional[int]) -> Dict[str, Any]:
    """A Sprint question about a weekend (or season) with no Sprint: say so and ask which one."""
    if year < 2021:
        text = (f"There were no Sprints in **{year}**: Formula 1 introduced Sprint races in **2021**. "
                f"Which year and race do you mean? (e.g. \"Who won the sprint at the 2026 Singapore GP?\")")
        intent = f"{year} — no Sprints"
    elif round_no is None:
        first = next((r for r in race_replay.season_races(year) if r.get("has_sprint")), None)
        place = re.sub(r" Grand Prix", "", first.get("race_name", "")) if first else "Singapore"
        text = (f"Which Sprint do you mean? {_sprint_weekends_text(year)} "
                f"Name the race (and year), e.g. \"Who won the {year} {place} sprint?\"")
        intent = f"{year} Sprint — which race?"
    else:
        r = next((x for x in race_replay.season_races(year) if x.get("round") == round_no), {})
        name = r.get("race_name") or f"Round {round_no}"
        text = (f"The **{year} {name}** (Round {round_no}) had **no Sprint**, so there's no Sprint result to give. "
                f"{_sprint_weekends_text(year)} Which one do you mean?")
        intent = f"{year} {name} — no Sprint"
    return {"role": "assistant", "text": text, "tool": "no_sprint_weekend", "intent": intent, "a2ui_card": None}


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
    "incident_investigation": "race", "dnf_summary_lookup": "race", "fastest_lap_lookup": "race", "race_length_lookup": "race",
    "sprint_classification_lookup": "sprint", "sprint_grid_lookup": "sprint",
    "sprint_qualifying_lookup": "sprint_qualifying", "qualifying_pole_lookup": "qualifying",
}


def answer_race_engineer_query(
    query: str,
    context: Optional[Dict[str, Any]] = None,
    history: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Main entry point: the engine answers, then the semantic router checks the answer fits
    what was asked (docs/AGENT_ARCHITECTURE.md, step 3a)."""
    resp = _answer_once(query, context, history)
    if os.environ.get("SIMGENT_ROUTER", "on") != "off":
        try:
            resp = _routed(query, context, history, resp)
        except Exception as e:  # the router must never break an answer
            logger.warning(f"router failed: {type(e).__name__}")
    # The answer gate (app/agent/gate.py): checks the answer fits the question and its facts
    # before it goes out; may ask a clarifying question instead
    from app.agent import gate
    try:
        question = resolve_follow_up(query, scope_history_to_view(history, context))
        return gate.check(question, context, history, resp, lambda q, ctx: _answer_once(q, ctx, history))
    except Exception as e:  # the gate must never break an answer
        logger.warning(f"answer gate failed: {type(e).__name__}: {e}")
        return resp


def _routed(query: str, context: Optional[Dict[str, Any]], history: Optional[List[Dict[str, Any]]],
            resp: Dict[str, Any]) -> Dict[str, Any]:
    """If the router is confident the question asks for another intent than the engine
    answered, ask the engine again in that intent's canonical phrasing (with the question's own
    names, position, segment and race) and keep the retry only if it answers with that intent's
    tools. A generic fallback is replaced at normal confidence; a specific answer from another
    intent only at high confidence."""
    from app.agent import router as R
    question = resolve_follow_up(query, scope_history_to_view(history, context))
    router = R.get_router()
    if router.method != "embedding":
        return resp  # keyword-only scores aren't calibrated for overriding answers; shadow only
    route = router.route(question)
    if not route.intent:
        return resp
    intent = router.intents[route.intent]
    tool = resp.get("tool") or ""
    if tool in intent.tools or tool in R.DEFINITIVE_TOOLS:
        return resp
    if tool == "race_not_run" and route.intent in R.RACE_INTENTS:
        return resp
    generic = tool in R.FALLBACK_TOOLS or tool == "race_not_run"
    if not generic and (route.score < R.OVERRIDE_MIN_SCORE or route.margin < R.OVERRIDE_MARGIN):
        return resp
    rewritten = R.canonical(question, intent)
    if not rewritten or rewritten.lower().strip(" ?") == question.lower().strip(" ?"):
        return resp
    retry = _answer_once(rewritten, context, history)
    if retry.get("tool") not in intent.tools:
        return resp
    retry["routed"] = {"intent": route.intent, "score": route.score, "asked_as": rewritten, "engine_tool": tool}
    return retry


def _answer_once(
    query: str,
    context: Optional[Dict[str, Any]] = None,
    history: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """The engine. The race and session on screen are the default scope for questions
    that don't name their own (ADK session-state pattern); every race-data answer says which
    race and session it is based on."""
    from app.tools import session_scope as SS
    out_of_range = _out_of_range_season(query.lower())
    if out_of_range:
        return out_of_range
    # Other ways of asking who won ("who took the chequered flag at ...") were read as safety-car
    # or flag questions; say them the way every handler understands
    query = _WIN_WORDING.sub("who won", query)
    history = scope_history_to_view(history, context)
    # Nothing on screen (API, MCP, first visit): the latest completed race is the default,
    # and the answer's footer says so
    if not (context or {}).get("round"):
        context = {**(context or {}), "year": _CURRENT_SEASON, "round": _latest_round(_CURRENT_SEASON)}
    scope = SS.resolve_scope(query, context, history)
    if scope and not scope["from_screen"] and scope["session"] != "race":
        # "who was knocked out in Q1 in Singapore?": a named race and a named session
        named = _named_race(query.lower(), scope["year"])
        if named:
            target = dict(scope, year=named[0], round=named[1], race="", session_from_screen=False)
            resp = SS.answer_in_session(query, target, None, history)
            if resp:
                return SS.with_scope(resp, target, resp.pop("label"))
    if scope and scope["from_screen"]:
        resp = SS.answer_weekend(query, scope)
        if resp:
            label = resp.pop("label")
            return {**resp, "text": f"{resp['text'].rstrip()}\n\n*{label}*"}
    if scope and scope["from_screen"] and scope["session"] != "race":
        resp = SS.answer_in_session(query, scope, context, history)
        if resp:
            return SS.with_scope(resp, scope, resp.pop("label"))
    token = _NO_RACE_RESULT.set(None)
    try:
        resp = _answer_core(query, context, history)
        no_result = _NO_RACE_RESULT.get()
    finally:
        _NO_RACE_RESULT.reset(token)
    # Only answers that need the Grand Prix result are replaced; qualifying/sprint lookups
    # (e.g. the pole) have their own data.
    if no_result and resp.get("tool") not in _GENERAL_WITHOUT_A_RACE and (
            _RACE_DATA_TOOLS.get(resp.get("tool", "")) == "race" or resp.get("tool") == "session_telemetry_briefing"):
        return _race_not_run(*no_result)
    used = _RACE_DATA_TOOLS.get(resp.get("tool", ""))
    if scope and scope["from_screen"] and used:
        answered = dict(scope, session=used)
        note = (f"No {SS._LABEL[scope['session']]} data for this question — answered from "
                if used != scope["session"] else "")
        resp = SS.with_scope(resp, answered, SS.scope_label(answered), note)
    return resp


_CURRENT_SEASON = 2026
PIT_DATA_FROM = 2011  # Jolpica-F1 has pit stops from 2011


# Questions answerable when only the race winner is known
_PARTIAL_OK = re.compile(r"\b(who won|winner|won the|fastest lap|how many laps|number of laps|race distance|circuit|track|"
                         r"where|held|hosted|venue|what happened|story|why|champion\w*|title|standings|career|"
                         r"regulations?|rules|era|pole|practice|fp[123])\b")

_WIN_WORDING = re.compile(
    r"\bwho (?:took|saw|received|got) the (?:chequered|checkered) flag\b|\bwho (?:finished|came|crossed the line) first\b"
    r"|\bwho was victorious\b|\bwho triumphed\b", re.I)


_COMEBACK_STRONG = re.compile(
    r"\bcome ?backs?\b|\bcame back\b|\bcoming back\b|\b(?:places|positions|spots) gained\b"
    r"|\b(?:gain|gained|gaining|made up|make up) (?:the )?most (?:places|positions|spots)\b|\bthrough the (?:field|pack)\b")
# "from the back", "pit lane": a comeback only with an outcome ("who started from the pit lane" is the grid)
_COMEBACK_START = re.compile(
    r"\bfrom (?:the )?(?:back|rear|last|pit ?lane)\b|\bback of the (?:grid|field|pack)\b|\bfurthest back\b"
    r"|\blowest (?:grid|starting)\b|\bstart(?:ed|ing)? (?:last|at the back)\b")
_COMEBACK_OUTCOME = re.compile(r"\b(?:win|wins|won|winning|victory|victories|podiums?|finish\w*|recover\w*|charge\w*)\b")


class _Comeback:
    @staticmethod
    def search(q: str) -> bool:
        return bool(_COMEBACK_STRONG.search(q) or (_COMEBACK_START.search(q) and _COMEBACK_OUTCOME.search(q)))


_COMEBACK = _Comeback()
# "ever", "career", "which race": search beyond the race on screen
_SEARCH_WIDE = re.compile(r"\b(?:ever|all[- ]time|history|career|in f1|which race|what race|of any race)\b")


def _out_of_range_season(q: str) -> Optional[Dict[str, Any]]:
    """A season before the championship or not yet run. Checked before anything else: otherwise
    the year is ignored and the race on screen answers (a 1949 question got a 2026 result)."""
    m = re.search(r"\b(18\d\d|19\d\d|20\d\d)\b", q)
    if not m or 1950 <= int(m.group(1)) <= _CURRENT_SEASON:
        return None
    asked = int(m.group(1))
    text = (f"The Formula 1 World Championship began in 1950, so there are no championship races from "
            f"**{asked}** in the data." if asked < 1950 else
            f"The **{asked}** season hasn't happened yet. I answer from race results, so I can't predict it; "
            f"ask me about {_CURRENT_SEASON} or any earlier season.")
    return {"role": "assistant", "text": text, "tool": "season_out_of_range", "intent": "Season Out of Range",
            "a2ui_card": None}


def _named_race(q: str, default_year: int) -> Optional[Tuple[int, int]]:
    """(year, round) of the race a question names, or None when it names none."""
    ym = re.search(r"\b(19[5-9]\d|20\d\d)\b", q)
    year = int(ym.group(1)) if ym else default_year
    if not 1950 <= year <= _CURRENT_SEASON:
        return None
    races = race_replay.season_races(year)
    rm = re.search(r"\b(?:round|r)\s*(\d+)\b", q)
    if rm and any(r["round"] == int(rm.group(1)) for r in races):
        return year, int(rm.group(1))
    if re.search(r"\b(latest|last|recent|current) race\b|\btoday\b", q):
        return year, _latest_round(year)
    rnd = _match_race_round(q, races)
    return (year, rnd) if rnd is not None else None


def _latest_round(year: int) -> int:
    """The last completed round of a season (the last round for a past season)."""
    races = race_replay.season_races(year)
    done = [r["round"] for r in races if r.get("completed")]
    return done[-1] if done else (races[-1]["round"] if races else 1)


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
    # No race on screen: default to the latest completed race (it used to be a fixed
    # round 15, so "who was knocked out in Q1?" answered about Baku)
    try:
        year = int(ctx.get("year") or _CURRENT_SEASON)
    except (ValueError, TypeError):
        year = _CURRENT_SEASON
    try:
        round_no = int(ctx["round"]) if ctx.get("round") else _latest_round(year)
    except (ValueError, TypeError):
        round_no = _latest_round(year)

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
        scheduled = next((r for r in races if r.get("round") == round_no), None)
        if scheduled and not scheduled.get("completed"):
            # Never substitute another race: this one hasn't been run, or its result isn't
            # published yet. Questions that don't need it (rules, standings, careers) are
            # answered as usual; race-data answers are replaced by answer_race_engineer_query.
            _NO_RACE_RESULT.set((year, scheduled))
        else:
            model = race_replay.build_replay(year, races[0]["round"])

    meta = model["meta"] if model else {}
    drivers = model["drivers"] if model else []
    events = model["events"] if model else []
    winner = drivers[0] if drivers else None

    # Comebacks: grid against finish across F1DB ("in what race did Antonelli win from the back
    # of the grid?"). Searches a driver's career, a season or all time; scoped to one race only
    # when the question names it or says "this race", or asks about climbing places in general
    # with no driver, year, win/podium or "ever" ("who gained the most places?"). It used to fall
    # through to the race on screen.
    if _COMEBACK.search(q):
        race_scoped = (bool(re.search(r"\b(?:this|today'?s?) (?:race|grand prix|gp)\b", q))
                       or (year_match and _match_race_round(q, race_replay.season_races(year)) is not None)
                       or (not year_match and not _SEARCH_WIDE.search(q)
                           and not re.search(r"\b(?:win|wins|won|winning|victory|victories|podiums?)\b", q)
                           and f1_history._f1db_driver(q) is None))
        cb = f1_history.lookup_comebacks(q, f"{year}_{round_no}" if race_scoped else None)
        if cb:
            return {
                "role": "assistant",
                "text": cb["text"],
                "tool": "comeback_lookup",
                "intent": f"Comebacks{' — ' + cb['driver'] if cb.get('driver') else ''}",
                "a2ui_card": cb["card"],
            }

    # Only the winner is known (results not cached and Jolpica unreachable, e.g. rate-limited):
    # answer what that supports and never present a one-car field as the race (it used to say
    # "all 1 classified cars finished with zero retirements")
    pre_pit_data = year < PIT_DATA_FROM and re.search(r"\b(pit|stops?|strateg\w*|tyres?|tires?|compounds?)\b", q)
    if model and meta.get("results_complete") is False and winner and not _PARTIAL_OK.search(q) and not pre_pit_data:
        return {"role": "assistant", "tool": "race_results_partial", "a2ui_card": None,
                "intent": "Race Results Unavailable",
                "text": (f"I only have the winner of the **{meta.get('race_name', 'race')} ({year})** right now "
                         f"(**{winner['name']}**), not the full results, so I can't answer that reliably. "
                         "Please try again in a moment.")}

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
        r"\b(pit|strateg\w*|stint|tyres?|tires?|retire\w*|dnf|grid|start\w*|qualif\w*|lap \d+|pace|gap"
        r"|fastest lap|how many laps|number of laps|race distance|pole)\b", q)))
    if (is_narrative_q or (names_race_itself and not is_result_q)) and not is_driver_detail_q:
        story_data = f1_history.lookup_historic_race_event(q, year, meta.get("circuit_id"))
    if story_data:
        return {
            "role": "assistant",
            "text": story_data["text"],
            "tool": "historic_race_moment_lookup",
            "intent": "Iconic Formula 1 Historical Turning Point & Drama Analysis",
            "a2ui_card": story_data["card"],
            "sources": [_content.source_of("races", id=story_data["story"]["id"])],
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
    if year_match and not race_named and not any(w in q for w in ["grand prix", "gp", "race", "circuit", "round", "sprint"]):
        hist_yr = int(year_match.group(1))
        if 1950 <= hist_yr <= 2025 and any(w in q for w in ["champion", "championship", "title", "who won", "winner of the season", "won the"]):
            # Prefer the official final standings data; the hand-written roster in
            # f1_history is only a fallback for seasons without standings data.
            wants_constructor = bool(re.search(r"\b(constructor|constructors|constructors'|team|teams|wcc)\b", q))
            champ_data = _season_title_from_data(hist_yr, wants_constructor)
            if champ_data is None:
                champ_data = f1_history.lookup_season_champion(hist_yr)
            if champ_data:
                resp = {
                    "role": "assistant",
                    "text": champ_data["text"],
                    "tool": "historical_championship_lookup",
                    "intent": f"{hist_yr} FIA World Championship Classification",
                    "driver_id": champ_data.get("driver_id"),
                    "a2ui_card": champ_data["card"]
                }
                # "Why did Hamilton lose the 2021 title?": the standings alone don't answer
                # why, so add the story of the race that decided it when content has one
                decider = next((st for st in _content.race_stories()
                                if st["year"] == hist_yr and st.get("decided_title")), None)
                if decider and re.search(r"\b(why|how)\b", q):
                    resp["text"] = (f"{champ_data['text'].rstrip()}\n\n**How it was decided — {decider['title']}**\n\n"
                                    f"{decider['summary']}")
                    resp["sources"] = [_content.source_of("races", id=decider["id"])]
                elif re.search(r"\b(why|how)\b", q):
                    resp["text"] = (f"{champ_data['text'].rstrip()}\n\nI have the final standings for {hist_yr} "
                                    "but no write-up of how the title was decided.")
                return resp

    # Sprint questions about a weekend without a Sprint (or no race named at all) never get
    # another session's result: say so and ask which Sprint is meant.
    if re.search(r"\bsprint\b|\bsq[123]?\b", q) and not re.search(
            r"\b(how many|career|most|all-time|record|rules?|regulations?|format|points? system|what is a sprint|explain)\b", q):
        # The race on screen only counts when the question doesn't name another season.
        screen_race = ctx.get("round") is not None and not (year_match and str(ctx.get("year")) != year_match.group(1))
        race_known = (screen_race or race_named or bool(round_match)
                      or bool(history and race_from_history(history, datetime.date.today().year)))
        weekend = next((r for r in race_replay.season_races(year) if r.get("round") == round_no), None)
        if year < 2021:
            return _no_sprint_reply(year, None)
        if not race_known:
            return _no_sprint_reply(year, None)
        if weekend is not None and not weekend.get("has_sprint"):
            return _no_sprint_reply(year, round_no)

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
        if sp_model and sp_model.get("drivers") and sp_model["meta"].get("session_type") == "sprint":
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
        if not (q_model and q_model.get("drivers") and q_model["meta"].get("session_type") == "qualifying"):
            # No qualifying data: build_replay fell back to the race. Never present the race
            # leader (or the winner of a results-less race) as the pole sitter.
            race_m = q_model if (q_model and q_model["meta"].get("session_type") in (None, "race")) else None
            field = (race_m or {}).get("drivers") or []
            starter = next((d for d in field if d.get("grid") == 1), None) if len(field) > 1 else None
            title = (race_m or {}).get("meta", {}).get("race_name") or f"Round {round_no}"
            if starter:
                text = (f"**{starter['name']}** started from **pole position** (grid P1) for {starter['team']} at the "
                        f"**{title} ({year})**. Qualifying times for this race aren't in the data.")
            else:
                text = (f"I don't have the qualifying results or starting grid for the **{title} ({year})**, "
                        "so I can't say who was on pole.")
            return {"role": "assistant", "text": text, "tool": "qualifying_pole_lookup",
                    "intent": f"{year} Pole Position", "a2ui_card": None}
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
            if year == 2021:
                # 2021 sprint weekends: qualifying set the Sprint grid, the Sprint set the GP grid,
                # and the Sprint winner is credited with pole position
                sp_m = race_replay.build_replay(year, round_no, session_type="sprint")
                if sp_m and sp_m["meta"].get("session_type") == "sprint" and sp_m.get("drivers"):
                    sw = sp_m["drivers"][0]
                    if sw["name"] != pole_drv["name"]:
                        text = (f"**{sw['name']}** started the **{q_model['meta'].get('race_name', 'Grand Prix').split(' - ')[0]} ({year})** "
                                f"from **pole position**: in 2021 the Sprint set the grid and its winner is credited with pole. "
                                f"{pole_drv['name']} was fastest in qualifying{time_txt}.")
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
    if (hist_driver and (race_driver or _NO_RACE_RESULT.get())
            and re.search(r"\b(exit(?:ed)?|leave|left|retire[ds]?|dnf)\b.*\b(this|the) (race|grand prix|gp)\b|\bdnf\b", q)
            and not re.search(r"\b(career|from f1|from formula|stop racing|quit f1)\b", q)):
        hist_driver = None  # "when did Verstappen exit this race?" is about this race, not his career

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
                "a2ui_card": era_data["card"],
                "sources": [_content.source_of("eras", id=era_data["era_id"])],
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
    is_grid_query = bool(re.search(r'\b(grid|starting grid|started in|start in|started p\d+|start p\d+|started from|start from|where did .* start|what position did .* start|front row|started at the back|pit lane start|start(?:ed)? (?:last|from the pit ?lane)|last on the grid)\b', q)) or (
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
                        {"label": "Finish", "value": f"P{slot_drv.get('finish')}" if slot_drv.get('status', '').startswith(('Finished', 'Lapped', '+')) else slot_drv.get('status', 'Retired'), "color": "#10B981" if slot_drv.get('status', '').startswith(('Finished', 'Lapped', '+')) else "#E10600"},
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
            "intent": f"{d['name']} Starting Grid Position & Race Classification",
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

    # The whole grid ("what was the starting grid", "who was on the front row"): no driver or
    # slot named. Grid slots come from the race result (0 = pit lane start).
    if is_grid_query and not target_driver and drivers:
        on_grid = sorted((d for d in drivers if isinstance(d.get("grid"), int) and d["grid"] > 0), key=lambda d: d["grid"])
        pit_lane = [d for d in drivers if d.get("grid") == 0]
        if on_grid:
            race_label = meta.get("race_name", "Grand Prix")
            front = " and ".join(f"**{d['name']}**" for d in on_grid[:2])
            top = ", ".join(f"P{d['grid']} {d['code']}" for d in on_grid[:10])
            back = on_grid[-1]
            pit_txt = f" Pit lane start: {', '.join(d['name'] for d in pit_lane)}." if pit_lane else ""
            # Lead with what was asked: "who started from the pit lane?" used to get the front row
            # and no word on the pit lane when nobody started there
            lead = ""
            if re.search(r"\bpit ?lane\b", q):
                names = " and ".join(f"**{d['name']}**" for d in pit_lane)
                lead = (f"{names} started from the pit lane" if pit_lane else
                        "Nobody started from the pit lane") + f" at the **{race_label} ({year})**.\n\n"
                pit_txt = ""
            elif re.search(r"\b(?:started|start|starting) (?:last|at the back)\b|\blast on the grid\b|\bback of the grid\b", q):
                lead = (f"**{back['name']}** started last on the grid (P{back['grid']}) at the **{race_label} ({year})**"
                        + (f", with {', '.join(d['name'] for d in pit_lane)} starting behind from the pit lane" if pit_lane else "")
                        + ".\n\n")
            return {
                "role": "assistant",
                "text": (f"{lead}Front row for the **{race_label} ({year})**: {front}. Top ten on the grid: {top}. "
                         f"Last on the grid: {back['name']} (P{back['grid']}).{pit_txt}"),
                "tool": "starting_grid_lookup",
                "intent": f"{year} FIA Starting Grid",
                "a2ui_card": {
                    "type": "starting_grid_card",
                    "title": f"Starting Grid — {race_label}",
                    "metrics": [{"label": f"P{d['grid']}", "value": f"{d['name']} ({d['code']})", "color": d.get("color", "#FFFFFF")}
                                for d in on_grid[:4]],
                },
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
                source = (_content.source_of("retirements", year=year, circuit_id=cid, driver=code)
                          or _content.source_of("retirements", year=year, circuit_id=cid, driver=did))
                return {
                    "role": "assistant",
                    "text": curated["explanation"],
                    "sources": [source] if source else [],
                    "tool": "incident_investigation",
                    "intent": "Curated Historical Incident & Steward Report",
                    "a2ui_card": {
                        "type": "retirement_card",
                        "title": f"Retirement Debrief — {d['name']} (#{d['number']})",
                        "metrics": [
                            {"label": "Exit Lap", "value": f"Lap {curated['exit_lap']}", "color": "#E10600"},
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
                "intent": "Retirement Lap Analysis",
                "a2ui_card": {
                    "type": "retirement_card",
                    "title": f"Retirement Report — {d['name']} (#{d['number']})",
                    "metrics": [
                        {"label": "Exit Lap", "value": f"Lap {retire_lap}", "color": "#E10600"},
                        {"label": "Laps Completed", "value": f"{completed_laps} Laps", "color": "#FFFFFF"},
                        {"label": "Status", "value": d['status'][:20], "color": "#FFB703"},
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

    # 3.5 FREE PRACTICE (FP1, FP2, FP3) & FRIDAY LONG-RUN TELEMETRY
    # (before the results handlers: "FP1 lap times" is not a race-result question)
    is_practice_query = any(w in q for w in [
        "practice", "fp1", "fp2", "fp3", "free practice", "long run", "race simulation",
        "race sim", "friday pace", "friday long", "setup run", "aero test", "flow vis"
    ])
    if is_practice_query:
        race_title = meta.get('race_name', f'{year} Grand Prix')

        # No practice data exists in any source SimGent uses (Jolpica-F1 and OpenF1 results). This
        # used to return a template with invented paces, degradation and speed traps.
        text = (
            f"Free Practice sessions aren't in SimGent's data: the results it uses (Jolpica-F1 and OpenF1) "
            f"cover qualifying, sprints and the race, not practice. For the **{race_title} ({year})** I can tell "
            "you about qualifying, the race result, pit stops or retirements."
        )
        return {
            "role": "assistant",
            "text": text,
            "tool": "free_practice_telemetry_lookup",
            "intent": "Free Practice (not in the data)",
            "a2ui_card": None,
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

    # 3.1b RACE LENGTH: "how many laps was it?"
    if re.search(r"\bhow many laps\b|\bnumber of laps\b|\bhow (?:long|far) was (?:the|this|that) race\b|\brace distance\b", q) \
            and not re.search(r"\b(led|lead|leading|completed|did (?:he|she|they)|retire)", q):
        facts = race_replay.race_layout(year, round_no) or {}
        laps = facts.get("laps") or meta.get("total_laps")
        if laps:
            km = facts.get("length_km")
            dist = f" of the {km:g} km circuit, {laps * km:.1f} km" if km else ""
            return {"role": "assistant", "tool": "race_length_lookup", "a2ui_card": None,
                    "intent": f"{year} Race Length",
                    "text": f"The **{meta.get('race_name', 'Grand Prix')} ({year})** ran **{laps} laps**{dist}."}

    # 3.2 FASTEST LAP TELEMETRY LOOKUP
    is_fl_query = any(w in q for w in ["fastest lap", "fastest lap time", "who set the fastest lap", "purple lap", "who had fastest lap"])
    if is_fl_query:
        fl = meta.get("fastest_lap")
        if fl and fl.get("time"):
            fl_code = fl.get("code")
            fl_driver = next((d for d in drivers if d.get("code") == fl_code), None)
            fl_name = fl_driver["name"] if fl_driver else (fl.get("name") or fl_code)
            fl_team = fl_driver["team"] if fl_driver else "Race Entry"
            text = (
                f"**{fl_name}** set the **fastest lap** of the **{meta.get('race_name', 'Grand Prix')} ({year})**: "
                f"**{fl.get('time')}** on lap {fl.get('lap', 'N/A')}."
            )
            return {
                "role": "assistant",
                "text": text,
                "tool": "fastest_lap_lookup",
                "intent": f"{year} Fastest Lap Record",
                "a2ui_card": {
                    "type": "fastest_lap_card",
                    "title": f"Fastest Lap — {meta.get('race_name', 'Grand Prix')}",
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
            fl_who = (fl.get("name") or next((d["name"] for d in drivers if d.get("code") == fl.get("code")), None)
                      or fl.get("code")) if isinstance(fl, dict) else None
            fl_str = f" Fastest lap went to {fl_who} ({fl.get('time')})." if (fl and isinstance(fl, dict) and fl.get("time")) else ""
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
                "intent": "Podium & Race Classification",
                "a2ui_card": {
                    "type": "race_summary_card",
                    "title": f"Podium & Race Results — {meta.get('race_name', 'Grand Prix')}",
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
        pits = sorted(d.get("pits", []))
        stops_count = len(pits)
        stops_str = ", ".join(f"Lap {l}" for l in pits) if pits else "None"
        race_title = meta.get("race_name", "Grand Prix")
        laps_done = d.get("laps") or meta.get("total_laps") or 0
        # Stints from the real pit laps. Tyre compounds are not in the data (Jolpica-F1 records
        # when a car pitted, not what it fitted); they used to be guessed from the stop count.
        bounds = [0] + pits + [laps_done]
        stints = [{"stint": i + 1, "start_lap": bounds[i] + 1, "end_lap": bounds[i + 1],
                   "laps": bounds[i + 1] - bounds[i]} for i in range(len(bounds) - 1) if bounds[i + 1] > bounds[i]]
        is_compound_question = any(w in q for w in [
            "medium", "soft", "hard", "inter", "wet", "compound", "compounds", "tires", "tyres"
        ])
        if year < PIT_DATA_FROM:
            text = (f"Pit stop data starts in {PIT_DATA_FROM}, so I can't describe {d['name']}'s stops at the "
                    f"**{race_title} ({year})**. {d['name']} finished P{d['finish']} for {d['team']}.")
            stints = []
        elif not meta.get("has_pit_data"):
            text = (f"Pit stop data for the **{race_title} ({year})** isn't available right now, so I can't say how "
                    f"many times {d['name']} stopped. {d['name']} finished P{d['finish']} for {d['team']}.")
            stints = []
        elif pits:
            stint_lines = "\n".join(f"• Stint {s['stint']}: laps {s['start_lap']}–{s['end_lap']} ({s['laps']} laps)" for s in stints)
            text = (f"**{d['name']}** made **{stops_count} pit stop{'s' if stops_count != 1 else ''}** ({stops_str}) "
                    f"and finished P{d['finish']} for {d['team']} at the **{race_title} ({year})**.\n\n**Stints**:\n{stint_lines}")
        else:
            text = (f"**{d['name']}** didn't make a pit stop at the **{race_title} ({year})** and finished "
                    f"P{d['finish']} for {d['team']}.")
        if is_compound_question and year >= PIT_DATA_FROM and meta.get("has_pit_data"):
            text += ("\n\nTyre compounds aren't in SimGent's data: Jolpica-F1 records when drivers pitted, "
                     "not which tyres they fitted.")

        card_metrics = [{"label": f"Stint {s['stint']}", "value": f"Laps {s['start_lap']}–{s['end_lap']} ({s['laps']}L)",
                         "color": "#FFFFFF"} for s in stints[:3]]
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
            "intent": "Pit Stops & Stints",
            "a2ui_card": {
                "type": "strategy_card",
                "title": f"Pit Stops — {d['name']} (#{d['number']})",
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
                "intent": "Session Briefing",
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
            "intent": "Driver Result, Grid Delta & Pace Analysis",
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
                con_s = f"\n  ↳ *Note*: {e['consequence']}" if e.get('consequence') else ""
                lines.append(f"• **Lap {e['lap']}{end_s}**: {e['message']}{con_s}")
            events_str = "\n".join(lines)
            return {
                "role": "assistant",
                "text": f"**Race Control Log — Lap {target_lap} ({meta.get('race_name', 'Grand Prix')})**\n\n{events_str}",
                "tool": "race_control_lookup",
                "intent": "FIA Steward Directives & Lap Events",
                "a2ui_card": {
                    "type": "race_control_card",
                    "title": f"Race Control Event — Lap {target_lap}",
                    "metrics": [
                        {"label": "Lap", "value": f"Lap {target_lap}", "color": "#FFB703"},
                        {"label": "Event Type", "value": matching_events[0].get("type", "INCIDENT"), "color": "#00F5D4"},
                        {"label": "Incident", "value": matching_events[0].get("message", "").split("—")[0].strip(), "color": "#FFFFFF"},
                        {"label": "Circuit", "value": meta.get("circuit_name") or "—", "color": "#64748B"}
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
            f"{events_str}"
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
        reg = _content.regulation("2026-technical")  # content/regulations/2026-technical.md
        return {
            "role": "assistant",
            "text": reg["text"],
            "tool": "fia_regulations_lookup",
            "intent": reg["intent"],
            "a2ui_card": reg["card"],
            "sources": [_content.source_of("regulations", id="2026-technical")],
        }


    # 9. GENERAL PIT WALL STATUS & ACTIVE RACE CONTEXT
    cur_lap = ctx.get("lap", 1)
    winner_str = f"P1: {winner['name']} ({winner['team']})" if winner else "P1: Active"
    return {
        "role": "assistant",
        "text": (
            f"**Pit Wall Agent active** for the **{meta.get('race_name', 'Grand Prix')} ({year})** — Lap {cur_lap} of {meta.get('total_laps', 51)} with {len(drivers)} cars running.\n\n"
            f"Ask me about any race incident, driver result, pit stops, championship standings, or 2026 regulations."
        ),
        "tool": "session_telemetry_briefing",
        "intent": "Session Briefing & Pit Wall Status",
        "a2ui_card": None
    }

