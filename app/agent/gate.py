"""Answer gate: every pit wall answer is checked before it is returned.

1. Ambiguity: when a question fits two races, two drivers or two intents, ask which one is meant
   (a clarifying question with options), at most once per question.
2. Race match: an answer must be about the race the question names; one retry, then decline.
3. Facts: winner, pole, fastest lap, laps, circuit and champion are checked against F1DB
   (data/f1db_facts.json); a wrong fact is replaced by F1DB's.
4. Numbers: a lap time that isn't in the data for that race is removed.

Each verdict is counted for the live score (no question text is kept). Deterministic and
in-process: no model and no network, so it adds milliseconds and costs nothing.
SIMGENT_GATE=off turns it off (the golden eval measures the engine with it off).
"""

import collections
import glob
import json
import os
import re
import threading
import time
import unicodedata
from functools import lru_cache
from typing import Any, Callable, Dict, List, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FACTS = os.path.join(ROOT, "data", "f1db_facts.json")

# Answers the gate leaves alone: refusals, declines and statements already checked elsewhere
SKIP_TOOLS = {"security_guardrail", "out_of_scope_redirect", "unsupported_data_notice", "season_out_of_range",
              "race_not_run", "no_sprint_weekend", "qualifying_not_in_data", "sprint_not_in_data",
              "sprint_qualifying_not_in_data", "clarify", "free_practice_telemetry_lookup",
              "pit_strategy_explanation"}
FALLBACK_TOOLS = {"session_telemetry_briefing", ""}


# ---------------------------------------------------------------- live score
_lock = threading.Lock()
_counts: collections.Counter = collections.Counter()
_by_check: collections.Counter = collections.Counter()
_started = time.time()


def _count(verdict: str, check: str = "") -> None:
    with _lock:
        _counts[verdict] += 1
        if check:
            _by_check[f"{verdict}:{check}"] += 1


def stats() -> Dict[str, Any]:
    """Verdicts since this server process started (Cloud Run instances restart when idle)."""
    with _lock:
        total = sum(_counts.values())
        return {"since": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(_started)), "answers": total,
                "verdicts": dict(_counts), "by_check": dict(_by_check)}


# ---------------------------------------------------------------- text helpers
def _norm(text: str) -> str:
    text = unicodedata.normalize("NFD", text or "")
    return re.sub(r"[^a-z0-9 ]", " ", "".join(c for c in text if unicodedata.category(c) != "Mn").lower())


def _tokens(text: str) -> List[str]:
    return _norm(text).split()


@lru_cache(maxsize=1)
def _facts() -> Dict[str, Any]:
    try:
        with open(FACTS, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"races": {}, "champions": {}, "season_drivers": {}, "notable_drivers": []}


def _schedule(year: int) -> List[Dict[str, Any]]:
    from app.tools import jolpica_sync as J
    try:
        return J.schedule(year, net=False) or []
    except Exception:
        return []


STOP = set("the grand prix gp who won win winner was what which where how many laps lap pole position fastest set "
           "at in of for on did race circuit track hosted held f1 formula a an and to it is from by start started "
           "do does go went finish finished took take".split())
YEAR = re.compile(r"\b(19[5-9]\d|20[0-3]\d)\b")


def races_named(question: str, year: int) -> List[Tuple[int, Dict[str, Any]]]:
    """Races of that season the question names: an exact race name wins outright; otherwise every
    race sharing the most distinctive words (name, circuit, place). Several = ambiguous."""
    q = " " + " ".join(_tokens(question)) + " "
    races = _schedule(year)
    for r in sorted(races, key=lambda x: -len(x["raceName"])):
        if f" {' '.join(_tokens(r['raceName']))} " in q:
            return [(int(r["round"]), r)]
    words = set(q.split()) - STOP - {str(year)}
    scored = []
    for r in races:
        loc = r["Circuit"]["Location"]
        names = set(_tokens(" ".join([r["raceName"], r["Circuit"]["circuitName"], loc["locality"], loc["country"]]))) - STOP
        hits = len(words & names)
        if hits:
            scored.append((hits, int(r["round"]), r))
    if not scored:
        return []
    top = max(s[0] for s in scored)
    return [(rnd, r) for hits, rnd, r in scored if hits == top]


def category_of(question: str) -> Optional[str]:
    q = question.lower()
    if re.search(r"\b(why|how did|what happened|story|explain|strateg\w*|pit|tyres?|tires?|stops?)\b", q):
        return None  # narrative and strategy answers aren't single facts
    # Sprint and qualifying sessions aren't in the answer key (it holds the Grand Prix): a sprint
    # winner must never be "corrected" to the Grand Prix winner
    if re.search(r"\b(sprint|shootout|sq[123]?|q[123])\b", q):
        return None
    if re.search(r"\bqualif\w*", q) and not re.search(r"\bpole\b", q):
        return None
    if "fastest lap" in q:
        return "fastest_lap"
    if re.search(r"\bpole\b", q):
        return "pole"
    if re.search(r"how many laps|number of laps", q):
        return "laps"
    if re.search(r"which circuit|what track|which track|where was|\bheld\b|hosted|venue", q):
        return "circuit"
    # the answer key has drivers' champions only: constructors' questions are left alone
    if re.search(r"champion|championship|title", q) and not re.search(r"grand prix|\bgp\b|\brace\b|constructor|\bteams?\b|wcc", q):
        return "champion"
    if re.search(r"\bwho won\b|\bwinner\b|\bwho finished first\b", q):
        return "winner"
    return None


NOT_A_NAME = set("fastest lap laps pole position grand prix championship champion summary world drivers driver "
                 "record victories victory points team race sprint qualifying fia formula round circuit session "
                 "result results classification winner stints stint".split())


def _lead_name(answer: str) -> str:
    for m in re.finditer(r"\*\*(.+?)\*\*", answer):
        words = _tokens(m.group(1))
        if words and not re.search(r"\d", m.group(1)) and not (set(words) & NOT_A_NAME):
            return m.group(1)
    return answer.split(".")[0]


def _same(name: str, person: Dict[str, str], shared: List[str]) -> bool:
    have = " " + " ".join(_tokens(name)) + " "
    last = " ".join(w for w in _tokens(person["last"]) if w not in ("jr", "sr", "ii", "iii"))
    if f" {last} " not in have:
        return False
    if person["last"] in shared:
        first = _tokens(person["first"])
        return bool(first) and f" {first[0]} " in have
    return True


LAP_TIME = re.compile(r"(?<![\d:])(\d{1,2}:\d{2}\.\d{1,3})(?!\d|\.\d)")  # a full stop may follow


def _ms(t: str) -> Optional[int]:
    parts = t.split(":")
    try:
        return round((float(parts[-1]) + 60 * int(parts[-2]) + (3600 * int(parts[-3]) if len(parts) > 2 else 0)) * 1000)
    except (ValueError, IndexError):
        return None


def _known_times(year: int, rnd: int) -> set:
    from app.tools import jolpica_sync as J
    out = {_ms(t) for t in (_facts()["races"].get(f"{year}_{rnd}") or {}).get("lap_times", [])}
    for base in {str(J.CACHE), os.path.join(ROOT, "data", "cache", "jolpica")}:
        for path in glob.glob(os.path.join(base, f"{year}_{rnd}_*.json")):
            try:
                with open(path, encoding="utf-8") as f:
                    out |= {_ms(t) for t in LAP_TIME.findall(f.read())}
            except OSError:
                pass
    for path in glob.glob(os.path.join(ROOT, "data", "cache", "openf1", f"{year}_{rnd}_*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                out |= {_ms(t) for t in LAP_TIME.findall(f.read())}
        except OSError:
            pass
    return out - {None}


def _who(p: Dict[str, str]) -> str:
    return f"{p['first']} {p['last']}"


# ---------------------------------------------------------------- clarifications
def _clarify(kind: str, text: str, options: List[Dict[str, str]]) -> Dict[str, Any]:
    _count("clarify", kind)
    return {"role": "assistant", "text": text, "tool": "clarify", "intent": "Clarifying question", "a2ui_card": None,
            "clarify": {"kind": kind, "options": options[:4]}, "gate": {"verdict": "clarify", "check": kind}}


def _clarified_last_turn(history: Optional[List[Dict[str, Any]]]) -> bool:
    for turn in reversed(history or []):
        if turn.get("role") == "assistant":
            return bool(turn.get("options"))
    return False


QUESTION_FOR = {
    "winner": "Who won the {race}?", "pole": "Who was on pole for the {race}?",
    "fastest_lap": "Who set the fastest lap at the {race}?", "laps": "How many laps was the {race}?",
    "circuit": "Which circuit hosted the {race}?",
}


def _race_option(question: str, category: Optional[str], year: int, race: Dict[str, Any]) -> Dict[str, str]:
    full = f"{year} {race['raceName']}"
    query = QUESTION_FOR[category].format(race=full) if category in QUESTION_FOR else f"{question.rstrip(' ?')} ({full})?"
    day = time.strftime("%-d %b", time.strptime(race["date"], "%Y-%m-%d")) if race.get("date") else ""
    return {"label": f"{race['raceName']}" + (f" ({day})" if day else ""), "query": query}


def match_clarification(query: str, history: Optional[List[Dict[str, Any]]]) -> Optional[str]:
    """A reply to the options the agent just offered ("the second one", "the anniversary one",
    "Ralf") -> that option's full question; None when the reply isn't picking an option."""
    options = None
    for turn in reversed(history or []):
        if turn.get("role") == "assistant":
            options = turn.get("options")
            break
    if not options:
        return None
    words = _tokens(query)
    if not words or len(words) > 8:
        return None
    # A new question, not a reply: it names its own season or reads as a full question
    if YEAR.search(query) or (len(words) > 3 and words[0] in {"who", "what", "where", "when", "which", "how", "why", "did", "was", "is"}):
        return None
    # The option's own words first ("the anniversary one", "Ralf"), then ordinals ("the second
    # one", "2"); "one/two/three" count as ordinals only on their own or as "option two"
    asked = set(words) - STOP - {"the", "one", "please", "i", "meant", "mean", "option", "number"}
    # label words only: a date in a label ("2 Aug") must not match the reply "2"
    scores = [len(asked & {w for w in _tokens(o["label"]) if not w.isdigit()} - STOP) for o in options]
    best = max(scores) if scores else 0
    if best and scores.count(best) == 1:
        return options[scores.index(best)]["query"]
    ordinal = {"first": 0, "1": 0, "former": 0, "second": 1, "2": 1, "latter": 1, "third": 2, "3": 2,
               "fourth": 3, "4": 3, "last": len(options) - 1}
    if len(words) <= 2 or "option" in words or "number" in words:
        ordinal.update({"one": 0, "two": 1, "three": 2, "four": 3})
    picks = [ordinal[w] for w in words if w in ordinal and ordinal[w] < len(options)]
    if len(set(picks)) == 1:
        return options[picks[0]]["query"]
    return None


def _ambiguous_driver(question: str, year: Optional[int]) -> Optional[Tuple[str, List[Tuple[str, str]]]]:
    """A bare last name that fits several drivers (that season, or all-time drivers with 20+ starts)."""
    facts = _facts()
    pool = facts["season_drivers"].get(str(year)) if year else facts["notable_drivers"]
    if not pool:
        return None
    words = _tokens(question)
    text = " " + " ".join(words) + " "
    by_last = collections.defaultdict(set)
    for first, last in pool:
        by_last[" ".join(_tokens(last))].add(first)
    for last, firsts in by_last.items():
        if len(firsts) > 1 and f" {last} " in text:
            if any(f" {_tokens(f)[0]} " in text for f in firsts if _tokens(f)):
                return None  # first name given
            if not year and _one_dominates(last, firsts):
                return None  # "Senna" is Ayrton, "Verstappen" is Max: no need to ask
            return last, sorted((f, last) for f in firsts)
    return None


def _one_dominates(last: str, firsts: set) -> bool:
    """With no season named, one driver of that name is far better known (titles, then wins,
    then starts) than the rest: Ayrton over Bruno Senna, but not Graham over Damon Hill."""
    weight = {}
    for d in _facts().get("drivers", []):
        if " ".join(_tokens(d["last"])) == last and d["first"] in firsts:
            weight[d["first"]] = d["titles"] * 100 + d["wins"] * 5 + d["starts"] / 10
    ranked = sorted(weight.values(), reverse=True)
    return len(ranked) >= 2 and ranked[0] >= 6 * max(ranked[1], 1)


def _ask_or_assume(history, make_clarify, assume):
    """Ask once; if this question already followed a clarification, take the likeliest reading."""
    return assume() if _clarified_last_turn(history) else make_clarify()


# ---------------------------------------------------------------- the gate
def check(question: str, context: Optional[Dict[str, Any]], history: Optional[List[Dict[str, Any]]],
          resp: Dict[str, Any], ask: Callable[[str, Optional[Dict[str, Any]]], Dict[str, Any]]) -> Dict[str, Any]:
    """The answer to return for this question: resp itself, a corrected or retried answer, a
    clarifying question, or a decline. `ask(question, context)` re-asks the engine."""
    if os.environ.get("SIMGENT_GATE", "on") == "off":
        return resp
    tool = resp.get("tool") or ""
    if tool in SKIP_TOOLS or resp.get("clarify"):
        return resp
    q = question.strip()
    ym = YEAR.search(q)
    year = int(ym.group(1)) if ym else None
    category = category_of(q)

    # 1a. Two drivers with that last name (Michael or Ralf Schumacher)
    amb = _ambiguous_driver(q, year)
    if amb and category not in ("winner", "pole", "fastest_lap", "laps", "circuit"):
        last, people = amb
        surname = next(w for w in re.findall(r"[A-Za-zÀ-ÿ'-]+", q) if _norm(w).strip() == last.split()[-1]) if last else last
        options = [{"label": f"{f} {surname}", "query": re.sub(rf"\b{re.escape(surname)}\b", f"{f} {surname}", q, count=1)}
                   for f, _ in people]

        def assume():
            _count("passed", "assumed_driver")
            return resp
        return _ask_or_assume(history, lambda: _clarify(
            "driver", f"Which {surname} do you mean{f' in {year}' if year else ''}? "
                      + " or ".join(f"**{o['label']}**" for o in options) + "?", options), assume)

    # 1b. Two races fit (Silverstone 2020: British GP and 70th Anniversary GP)
    named = races_named(q, year) if year else []
    if len(named) > 1:
        options = [_race_option(q, category, year, r) for _, r in named]

        def assume():
            first = options[0]
            again = ask(first["query"], context)
            again["text"] = f"*Assuming the {named[0][1]['raceName']}.*\n\n{again.get('text', '')}"
            _count("passed", "assumed_race")
            return again
        return _ask_or_assume(history, lambda: _clarify(
            "race", f"There were {len(options)} races that fit in {year}: "
                    + ", ".join(f"**{o['label']}**" for o in options) + ". Which one do you mean?", options), assume)

    # 1c. The engine fell back to a generic answer and the router is torn between two intents
    if tool in FALLBACK_TOOLS:
        clar = _intent_clarification(q)
        if clar and not _clarified_last_turn(history):
            return clar

    # 2a. "This race" means the race on screen: an answer about another race is replaced by the
    # engine's answer for the race on screen (a stored Bahrain answer once answered "How did VER
    # win this race?" on the Singapore replay)
    ctx_race = None
    if (context or {}).get("year") and (context or {}).get("round"):
        try:
            ctx_race = (int(context["year"]), int(context["round"]))
        except (TypeError, ValueError):
            ctx_race = None
    if ctx_race and not year and re.search(r"\bthis (?:race|grand prix|gp|weekend|session)\b", q.lower()):
        about = _race_in_answer(resp.get("text", ""))
        if about and about != ctx_race:
            again = ask(q, context)
            if _race_in_answer(again.get("text", "")) in (None, ctx_race):
                again["gate"] = {"verdict": "retried", "check": "this_race"}
                _count("retried", "this_race")
                return again
            _count("declined", "this_race")
            return {"role": "assistant", "tool": "gate_declined", "a2ui_card": None, "intent": "Couldn't confirm",
                    "gate": {"verdict": "declined", "check": "this_race"},
                    "text": "I couldn't answer that reliably for the race on screen. Could you rephrase it?"}

    # 2. The answer must be about the race the question names
    target = named[0] if len(named) == 1 else None
    if target and year and not _mentions_race(resp.get("text", ""), year, target[1]):
        full = f"{year} {target[1]['raceName']}"
        retry_q = QUESTION_FOR[category].format(race=full) if category in QUESTION_FOR else f"{q.rstrip(' ?')} ({full})?"
        again = ask(retry_q, context)
        if _mentions_race(again.get("text", ""), year, target[1]):
            resp, tool = again, again.get("tool") or ""
            resp["gate"] = {"verdict": "retried", "check": "race"}
            _count("retried", "race")
        elif category:
            pass  # the fact check below answers from F1DB for the named race
        else:
            _count("declined", "race")
            return {"role": "assistant", "tool": "gate_declined", "a2ui_card": None, "intent": "Couldn't confirm",
                    "gate": {"verdict": "declined", "check": "race"},
                    "text": f"I couldn't match that reliably to the **{full}**. Could you rephrase the question?"}

    # 3. Facts against F1DB
    race_key = None
    scope, ctx = resp.get("scope") or {}, context or {}
    if target and year:
        race_key = (year, target[0])
    elif category and category != "champion":
        # No race in the question ("who won that race?" after talking about 2024 Australia): check
        # the answer against the race it says it is about, not the race on screen
        race_key = _race_in_answer(resp.get("text", ""))
    if not race_key and not target and category and category != "champion":
        if scope.get("year") and scope.get("round") and (scope.get("session") in (None, "race")):
            race_key = (int(scope["year"]), int(scope["round"]))
        elif not year and ctx.get("year") and ctx.get("round") and str(ctx.get("session") or "race") == "race":
            race_key = (int(ctx["year"]), int(ctx["round"]))
    # The answer key holds Grand Prix facts: an answer about a Sprint or Qualifying session ("who
    # won?" on the qualifying screen) is not checked against the Grand Prix winner. Grand Prix
    # pole is a qualifying fact and still checked, but not a Sprint pole.
    session = scope.get("session") or ("sprint" if tool.startswith("sprint") else "qualifying" if tool.startswith("qualifying") else None)
    if session in ("sprint", "sprint_qualifying") or (session == "qualifying" and category != "pole"):
        category = None
    corrected = _fact_check(category, year, race_key, resp)
    if corrected:
        return corrected

    # 4. Lap times that aren't in the data
    if race_key:
        cleaned = _drop_unknown_times(resp, *race_key)
        if cleaned:
            return cleaned

    # 5. A sprint weekend: offer the Sprint alongside a Grand Prix winner answer
    if category == "winner" and race_key and not re.search(r"\b(sprint|grand prix|gp|race)\b", q.lower()):
        resp = _offer_sprint(resp, *race_key)

    resp.setdefault("gate", {"verdict": "passed"})
    _count(resp["gate"]["verdict"], resp["gate"].get("check", ""))
    return resp


def _race_in_answer(text: str) -> Optional[Tuple[int, int]]:
    """(year, round) of the first race an answer names ("... at the 2024 Australian Grand Prix",
    "**Australian Grand Prix (2024)**")."""
    t = " " + " ".join(_tokens(text)) + " "
    for y in dict.fromkeys(int(m) for m in YEAR.findall(text)):
        for r in sorted(_schedule(y), key=lambda x: -len(x["raceName"])):
            if f" {' '.join(_tokens(r['raceName']))} " in t:
                return y, int(r["round"])
    return None


def _intent_clarification(question: str) -> Optional[Dict[str, Any]]:
    try:
        from app.agent import router as R
        router = R.get_router()
        if router.method != "embedding":
            return None
        route = router.route(question)
        if route.intent or not route.runner_up or route.score < 0.30:
            return None
        options = []
        for name in (route.best, route.runner_up):
            intent = router.intents.get(name)
            rewritten = R.canonical(question, intent) if intent else None
            if intent and rewritten:
                options.append({"label": intent.description.split("(")[0].strip(), "query": rewritten[0].upper() + rewritten[1:] + ("" if rewritten.endswith("?") else "?")})
        if len(options) < 2 or options[0]["query"] == options[1]["query"]:
            return None
        return _clarify("intent", "Do you mean " + " or ".join(f"**{o['label'].lower()}**" for o in options) + "?", options)
    except Exception:
        return None


def _mentions_race(text: str, year: int, race: Dict[str, Any]) -> bool:
    """The answer names this race (and not only a longer-named one of that season, e.g. the
    United States Grand Prix West when the question was the United States Grand Prix)."""
    t = " " + " ".join(_tokens(text)) + " "
    names = sorted(_schedule(year), key=lambda r: -len(r["raceName"]))
    found = []
    for r in names:
        n = " " + " ".join(_tokens(r["raceName"])) + " "
        if n in t:
            found.append(r["round"])
            t = t.replace(n, " ")
    return not found or str(race["round"]) in [str(f) for f in found]


def _fact_check(category, year, race_key, resp) -> Optional[Dict[str, Any]]:
    facts = _facts()
    text = resp.get("text", "")
    if not category:
        return None
    declined = re.search(r"\b(i don't have|i only have|isn't in the data|aren't in the data|can't say)\b", text, re.I)
    if category == "champion":
        if not year or str(year) not in facts["champions"]:
            return None
        champ = facts["champions"][str(year)]
        if _same(_lead_name(text), champ, []) or declined:
            return None
        return _corrected(resp, f"**{_who(champ)}** won the **{year}** Drivers' World Championship.", "champion")
    if not race_key:
        return None
    t = facts["races"].get(f"{race_key[0]}_{race_key[1]}")
    if not t:
        return None
    race = next((r for r in _schedule(race_key[0]) if int(r["round"]) == race_key[1]), None)
    title = f"{race_key[0]} {race['raceName']}" if race else f"{race_key[0]} round {race_key[1]}"
    lead, shared = _lead_name(text), t.get("shared_last_names", [])
    if category == "winner":
        if any(_same(lead, w, shared) for w in t["winners"]):
            return None
        names = " and ".join(f"**{_who(w)}**" for w in t["winners"])
        return _corrected(resp, f"{names} won the **{title}**." if len(t["winners"]) == 1 else
                          f"{names} shared the win at the **{title}**.", "winner")
    if category == "pole":
        if declined or any(_same(lead, p, shared) for p in t["pole"]):
            return None
        return _corrected(resp, f"**{_who(t['pole'][0])}** was on pole for the **{title}**.", "pole")
    if category == "fastest_lap" and t.get("fastest_lap"):
        fl = t["fastest_lap"]
        quoted = {_ms(x) for x in LAP_TIME.findall(text)}
        if declined or (_same(lead, fl, shared) and (_ms(fl["time"]) in quoted or fl["time"] in text)):
            return None
        on_lap = f" on lap {fl['lap']}" if fl.get("lap") else ""
        return _corrected(resp, f"**{_who(fl)}** set the fastest lap of the **{title}**: **{fl['time']}**{on_lap}.", "fastest_lap")
    if category == "laps" and t.get("laps"):
        first = re.split(r"(?<=[.!?])\s|\n", text.strip(), maxsplit=1)[0]
        if re.search(rf"\b{t['laps']}\b", first):
            return None
        return _corrected(resp, f"The **{title}** ran **{t['laps']} laps**.", "laps")
    if category == "circuit":
        have = set(_tokens(text))
        names = t["circuit_names"] + ([race["Circuit"]["circuitName"]] if race else [])
        if any(set(_tokens(n)) <= have for n in names):
            return None
        where = race["Circuit"]["circuitName"] if race else t["circuit_names"][0]
        return _corrected(resp, f"The **{title}** was held at **{where}**.", "circuit")
    return None


def _corrected(resp: Dict[str, Any], text: str, check: str) -> Dict[str, Any]:
    _count("corrected", check)
    return {"role": "assistant", "tool": resp.get("tool") or "gate_corrected", "a2ui_card": None,
            "intent": resp.get("intent", ""), "scope": resp.get("scope"),
            "text": f"{text}\n\n*Checked against F1DB.*",
            "gate": {"verdict": "corrected", "check": check, "engine_text": resp.get("text", "")[:400]}}


def _drop_unknown_times(resp: Dict[str, Any], year: int, rnd: int) -> Optional[Dict[str, Any]]:
    text = resp.get("text", "")
    quoted = {_ms(t): t for t in LAP_TIME.findall(text)}
    if not quoted:
        return None
    unknown = [t for m, t in quoted.items() if m is not None and m not in _known_times(year, rnd)]
    if not unknown:
        return None
    kept = [s for s in re.split(r"(?<=[.!?])\s+", text) if not any(t in s for t in unknown)]
    _count("corrected", "lap_time")
    out = dict(resp)
    out["text"] = " ".join(kept).strip() or "I can't confirm the lap time for that from the data."
    out["gate"] = {"verdict": "corrected", "check": "lap_time"}
    return out


def _offer_sprint(resp: Dict[str, Any], year: int, rnd: int) -> Dict[str, Any]:
    from app.tools import jolpica_sync as J
    try:
        sprint = J.sprint_results(year, rnd, net=False)
    except Exception:
        sprint = None
    if not (sprint and sprint.get("SprintResults")):
        return resp
    race = next((r for r in _schedule(year) if int(r["round"]) == rnd), None)
    if not race:
        return resp
    out = dict(resp)
    # a suggestion next to the answer, not a clarifying question (it doesn't count as asking)
    out["suggestions"] = [{"label": "The Sprint winner", "query": f"Who won the sprint at the {year} {race['raceName']}?"}]
    return out
