"""Answer questions about the session on screen (Grand Prix, Sprint, Qualifying, Sprint Qualifying).

The UI sends what the viewer is looking at with every question (year, round, session). This
follows the ADK session-state pattern: the on-screen view is the default scope, and anything
the question states explicitly (another race, "the sprint", "qualifying", "the grand prix")
overrides it.

  resolve_scope(query, context, history) -> scope dict or None
  answer_in_session(query, scope, context, history) -> response or None (not a session question)
  scope_label(scope) / with_scope(response, scope, note) -> attach what the answer is based on
"""

import re
from typing import Any, Dict, List, Optional

from app.tools import race_replay

SESSIONS = ("race", "sprint", "qualifying", "sprint_qualifying")
_LABEL = {"race": "Race", "sprint": "Sprint", "qualifying": "Qualifying", "sprint_qualifying": "Sprint Qualifying"}
_UI_SESSION = {"race": "race", "grand_prix": "race", "gp": "race", "sprint": "sprint", "qualifying": "qualifying",
               "sprint_qualifying": "sprint_qualifying", "sprint_shootout": "sprint_qualifying", "sq": "sprint_qualifying"}

_YEAR = re.compile(r"\b(19\d\d|20\d\d)\b")


def explicit_session(q: str) -> Optional[str]:
    """Session the question names itself, if any."""
    if re.search(r"\bsprint (?:qualifying|quali|shootout|pole)\b|\bsq[123]?\b", q):
        return "sprint_qualifying"
    if re.search(r"\bsprint\b", q):
        return "sprint"
    if re.search(r"\b(qualifying|qualify|quali|qualified|pole|q[123])\b", q):
        return "qualifying"
    if re.search(r"\b(grand prix|gp|main race|feature race|sunday)\b", q):
        return "race"
    return None


def _names_a_race(text: str, default_year: int) -> bool:
    """True when the text points at a specific race other than 'the one on screen'."""
    from app.tools.race_agent import _match_race_round
    t = text.lower()
    if re.search(r"\b(?:round|r)\s*\d+\b|\b(latest|last|recent|current) race\b|\btoday\b", t):
        return True
    ym = _YEAR.search(t)
    year = int(ym.group(1)) if ym else default_year
    if not 1950 <= year <= default_year + 1:
        return False
    return ym is not None or _match_race_round(t, race_replay.season_races(year)) is not None


def resolve_scope(query: str, context: Optional[Dict[str, Any]],
                  history: Optional[List[Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
    """Which race and session a question is about.

    from_screen is True when nothing in the question (or the conversation since the viewer
    opened this race) names another race, so the on-screen race and session apply."""
    ctx = context or {}
    try:
        year, rnd = int(ctx["year"]), int(ctx["round"])
    except (KeyError, TypeError, ValueError):
        return None
    q = query.lower()
    from app.tools.race_agent import race_from_history
    # The screen applies unless this question, or the conversation's current race, names another
    conv_race = race_from_history(history, year)
    from_screen = not _names_a_race(q, year) and conv_race in (None, (year, rnd))
    named = explicit_session(q)
    screen_session = _UI_SESSION.get(str(ctx.get("session") or "race").lower(), "race")
    # Generic qualifying words ("pole", "where did he qualify?") on the Sprint Qualifying
    # screen mean that session, unless the question says Grand Prix qualifying.
    if (named == "qualifying" and from_screen and screen_session == "sprint_qualifying"
            and not re.search(r"\b(grand prix|gp|main|sunday)\b", q)):
        named = "sprint_qualifying"
    session = named or (screen_session if from_screen else "race")
    return {"year": year, "round": rnd, "session": session, "from_screen": from_screen,
            "session_from_screen": from_screen and named is None, "race": ctx.get("race") or ""}


def scope_label(scope: Dict[str, Any], session_name: Optional[str] = None, race_name: Optional[str] = None) -> str:
    if not race_name and not scope.get("race"):
        race_name = next((r.get("race_name") for r in race_replay.season_races(scope["year"], net=False)
                          if r.get("round") == scope["round"]), None)
    race = race_name or scope.get("race") or f"Round {scope['round']}"
    # Drop a " - subtitle" suffix. One-character \s on each side keeps the search linear
    # (the old \s+-\s+ backtracked quadratically on long runs of spaces from the client).
    cut = re.search(r"\s-\s", race)
    race = (race[:cut.start()] if cut else race).rstrip()
    race = re.sub(r"^\d{4}\s+", "", race)
    return f"{scope['year']} {race} · {session_name or _LABEL[scope['session']]}"


def with_scope(resp: Dict[str, Any], scope: Dict[str, Any], label: str, note: str = "") -> Dict[str, Any]:
    """Attach what the answer is based on (visible footer + structured field)."""
    resp = dict(resp)
    resp["scope"] = {"year": scope["year"], "round": scope["round"], "session": scope["session"],
                     "label": label, "from_screen": scope["from_screen"]}
    footer = f"*{note}{label}*" if note else f"*{label}*"
    resp["text"] = f"{resp.get('text', '').rstrip()}\n\n{footer}"
    return resp


# ------------------------------------------------------------------ session answers
_RESULT_Q = re.compile(
    r"\b(who won|winner|won|who was (?:fastest|quickest|first|top)|fastest|quickest|who topped|top (?:three|3|five|5|ten|10)"
    r"|podium|results?|classification|standings? (?:in|for) (?:this|the) session|front row)\b")
_DRIVER_Q = re.compile(
    r"\b(how did|how was|how'd|where did|what position|which position|finish|finished|place[d]?|result|qualif(?:y|ied)"
    r"|do(?:ing)?|perform(?:ed|ance)?|p\d+|position|best lap|lap ?time|time|gap|delta|knocked out|eliminated)\b")
_POS_Q = re.compile(r"\bwho (?:finished|was|came|placed|qualified)\s+(?:in\s+)?p\s*(\d{1,2})\b|\bp\s*(\d{1,2})\b")


_SEGMENT = re.compile(r"\b(s?q)\s*([123])\b")
_KNOCKED_OUT = re.compile(r"\b(knocked out|eliminated|elimination|dropped out|went out|out in"
                          r"|didn'?t (?:make|get|reach)|did not (?:make|get|reach)|missed (?:the )?cut|failed to (?:make|reach))\b")
_MADE_IT = re.compile(r"\b(made it|make it|made|reached|advanced|through to|got (?:in)?to|went through|progressed)\b")
_FASTEST = re.compile(r"\b(fastest|quickest|top(?:ped)?|best time|p1)\b")
_SET_TIME = re.compile(r"\b(set a time|lap time|time in|best lap|no time|his time|her time|their time)\b")


def _fmt_lap(t: Optional[float]) -> str:
    if not t:
        return "no time"
    m, sec = divmod(t, 60)
    return f"{int(m)}:{sec:06.3f}"


def _segment_answer(q: str, drivers: List[Dict[str, Any]], segments: List[Dict[str, Any]], session: str,
                    session_name: str, label: str, scope: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Answers about the knockout segments (Q1/Q2/Q3 or SQ1/SQ2/SQ3) from per-segment lap times."""
    from app.tools.race_agent import _find_driver
    names = [g["name"] for g in segments]
    m = _SEGMENT.search(q)
    k = int(m.group(2)) - 1 if m else None
    if k is not None and k >= len(segments):
        return None
    reached = lambda d, i: len(d.get("lap_times") or []) > i
    who = lambda ds: ", ".join(f"{d['name']} (P{d.get('finish')})" for d in ds)
    out = lambda tool, text: {"role": "assistant", "text": text, "tool": f"{session}_{tool}",
                              "intent": label, "a2ui_card": None, "label": label}
    driver = _find_driver(q, drivers)

    # One driver in one segment: "did Colapinto set a time in Q2?", "Hamilton's Q1 time?"
    if driver and k is not None:
        if not reached(driver, k):
            return out("segment_driver_lookup",
                       f"**{driver['name']}** didn't take part in **{names[k]}**: knocked out in "
                       f"**{driver.get('eliminated_in')}** and classified **P{driver.get('finish')}**.")
        t = driver["lap_times"][k]
        if not t:
            return out("segment_driver_lookup",
                       f"**{driver['name']}** reached **{names[k]}** but **set no time** there, "
                       f"and was classified **P{driver.get('finish')}**.")
        ranked = sorted((d for d in drivers if reached(d, k) and d["lap_times"][k]), key=lambda d: d["lap_times"][k])
        rank = next(i for i, d in enumerate(ranked) if d is driver) + 1
        gap = t - ranked[0]["lap_times"][k]
        gap_txt = "fastest of anyone" if rank == 1 else f"+{gap:.3f}s to the fastest, {ranked[0]['name']}"
        return out("segment_driver_lookup",
                   f"**{driver['name']}** set **{_fmt_lap(t)}** in **{names[k]}**, the **P{rank}** time "
                   f"of the segment ({gap_txt}).")
    if driver:
        return None  # the driver question handlers answer the session as a whole

    # Knocked out: "who was knocked out in Q1?", "who didn't make Q3?"
    if _KNOCKED_OUT.search(q):
        if k is not None and re.search(r"didn'?t|did not|missed|failed", q):
            k = k - 1  # "didn't make Q3" = knocked out in Q2
        groups = [i for i in range(len(segments) - 1)] if k is None else [k]
        parts = []
        for i in groups:
            if not 0 <= i < len(segments) - 1:
                continue
            gone = sorted((d for d in drivers if len(d.get("lap_times") or []) == i + 1), key=lambda d: d.get("finish") or 99)
            if gone:
                parts.append(f"**{names[i]}** ({len(gone)}): {who(gone)}")
        if not parts:
            return out("segment_lookup", f"Nobody is knocked out in **{names[-1]}**: it decides the top of the grid.")
        return out("segment_lookup", "Knocked out in " + "; ".join(parts) + ".")

    # Made it through: "who made it to Q3?", "how many cars made SQ3?"
    if k is not None and k > 0 and (_MADE_IT.search(q) or re.search(r"how many", q)):
        through = sorted((d for d in drivers if reached(d, k)), key=lambda d: d.get("finish") or 99)
        return out("segment_lookup", f"**{len(through)} drivers** made it to **{names[k]}**: {who(through)}.")

    # Fastest in a segment: "who was fastest in Q2?"
    if k is not None and _FASTEST.search(q):
        ranked = sorted((d for d in drivers if reached(d, k) and d["lap_times"][k]), key=lambda d: d["lap_times"][k])
        if not ranked:
            return None
        best = ranked[0]
        second = (f", {ranked[1]['lap_times'][k] - best['lap_times'][k]:.3f}s ahead of **{ranked[1]['name']}**"
                  if len(ranked) > 1 else "")
        final = "" if k == len(segments) - 1 else (f" (final position P{best.get('finish')})")
        return out("segment_lookup", f"**{best['name']}** was fastest in **{names[k]}** with "
                                     f"**{_fmt_lap(best['lap_times'][k])}**{second}{final}.")
    return None


def _stage_label(session: str, status: str) -> str:
    """'Q3 (+0.345s)' -> 'SQ3 (+0.345s)' for sprint qualifying."""
    return re.sub(r"\bQ([123])\b", r"SQ\1", status) if session == "sprint_qualifying" else status


def _driver_line(d: Dict[str, Any], session: str, session_name: str, knockout: bool = True) -> str:
    pos = d.get("finish")
    status = str(d.get("status") or "")
    if session in ("qualifying", "sprint_qualifying"):
        stage = (d.get("qualifying_stage") or "") if knockout else ""  # no stages in single-session qualifying
        lap = d.get("best_lap")
        delta = d.get("pole_delta") or ""
        stage_txt = f", out in {_stage_label(session, stage)}" if stage and not stage.endswith("3") else (
            f", reaching {_stage_label(session, stage)}" if stage else "")
        lap_txt = f" with a best lap of **{lap}**" if lap and lap not in ("—", "-") else ""
        delta_txt = f" ({delta} to pole)" if delta.startswith("+") else (" — pole position" if pos == 1 else "")
        where = f"**P{pos}**" if isinstance(pos, int) and pos > 0 else f"**{status or 'unclassified'}**"
        return f"**{d['name']}** qualified {where} for {d['team']} in **{session_name}**{stage_txt}{lap_txt}{delta_txt}."
    grid = d.get("grid")
    grid_txt = ""
    if isinstance(grid, int) and grid > 0 and isinstance(pos, int) and pos > 0:
        diff = grid - pos
        move = f"gaining {diff} place{'s' if diff != 1 else ''}" if diff > 0 else (
            f"losing {-diff} place{'s' if diff != -1 else ''}" if diff < 0 else "holding position")
        grid_txt = f" from P{grid} on the grid ({move})"
    pts = d.get("points")
    pts_txt = f", scoring {pts:g} point{'s' if pts != 1 else ''}" if isinstance(pts, (int, float)) and pts else ""
    finished = status in ("Finished",) or status.startswith("+") or "Lap" in status
    if isinstance(pos, int) and pos > 0 and finished:
        return f"**{d['name']}** finished **P{pos}** in the **{session_name}** for {d['team']}{grid_txt}{pts_txt}, completing {d.get('laps')} laps."
    return (f"**{d['name']}** did not finish the **{session_name}** for {d['team']} "
            f"({status or 'not classified'}) after {d.get('laps', 0)} laps.")


def _card(scope, session, title, metrics):
    return {"type": "qualifying_card" if session in ("qualifying", "sprint_qualifying") else "race_summary_card",
            "title": title, "metrics": metrics,
            "action": f"VIEW {_LABEL[session].upper()}",
            "target": {"action_type": "switch_session", "year": scope["year"], "round": scope["round"], "session": session}}


def answer_in_session(query: str, scope: Dict[str, Any], context: Optional[Dict[str, Any]] = None,
                      history: Optional[List[Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
    """Result and driver questions answered from the scoped session's classification.
    Returns None for anything else (strategy, incidents, history...) so the main engine answers."""
    from app.tools.race_agent import _find_driver, _ordinal_position, _DRIVER_BACKREF
    session = scope["session"]
    if session == "race":
        return None
    q = query.lower()
    if re.search(r"\b(career|all-time|championship|standings|title|season|regulation|rule|era|history|strategy|pit|tyre|tire|stint"
                 r"|safety car|incident|crash|retire|dnf|why|weather|lap record|grid penalty)\b", q):
        return None
    model = race_replay.build_replay(scope["year"], scope["round"], session_type=session)
    if not model or not model.get("drivers") or model["meta"].get("session_type") != session:
        return None
    drivers = sorted(model["drivers"], key=lambda d: d.get("finish") if isinstance(d.get("finish"), int) and d["finish"] > 0 else 99)
    meta = model["meta"]
    # Sprint Shootout (2023) vs Sprint Qualifying (2024 on); other sessions use the plain label
    session_name = (meta.get("session_name") or _LABEL[session]) if session == "sprint_qualifying" else _LABEL[session]
    race_name = re.sub(r"\s+-\s+.*$", "", meta.get("race_name", ""))
    label = scope_label(scope, session_name, race_name)
    is_quali = session in ("qualifying", "sprint_qualifying")
    # Grid-order estimates carry no real segments, so no knockout stages are claimed.
    knockout = (not meta.get("times_estimated")
                and any(str(d.get("qualifying_stage", "")).endswith(("2", "3")) for d in drivers))
    if is_quali and meta.get("times_estimated") and (_SEGMENT.search(q) or _KNOCKED_OUT.search(q) or _SET_TIME.search(q)):
        return {"role": "assistant", "tool": f"{session}_not_in_data", "intent": label, "a2ui_card": None, "label": label,
                "text": (f"The {session_name} classification for this race isn't in the data (the replay uses the race "
                         f"grid as an estimate), so I can't say who was knocked out in each segment or quote lap times.")}

    # Knockout segment questions ("who was knocked out in Q1?", "who made SQ3?",
    # "fastest in Q2?", "did Colapinto set a time in Q2?") use the per-segment lap times.
    if is_quali and knockout and meta.get("segments") and not meta.get("times_estimated"):
        seg_answer = _segment_answer(q, drivers, meta["segments"], session, session_name, label, scope)
        if seg_answer:
            return seg_answer

    # A driver question: named in the question, or referred back to ("how did he do?")
    target = _find_driver(q, drivers)
    if not target and _DRIVER_BACKREF.search(q):
        sel = str((context or {}).get("selected") or "").lower()
        target = next((d for d in drivers if sel and sel in (d.get("code", "").lower(), d.get("id", "").lower())), None)
        for turn in reversed(history or []):
            if target:
                break
            target = _find_driver(turn.get("content") or turn.get("text") or "", drivers)
    if target and (_DRIVER_Q.search(q) or len(q.split()) <= 4):
        return {"role": "assistant", "text": _driver_line(target, session, session_name, knockout),
                "tool": f"{session}_driver_lookup", "intent": f"{label} — {target['name']}",
                "a2ui_card": _card(scope, session, f"{target['name']} — {session_name}", [
                    {"label": "Position", "value": f"P{target.get('finish')}" if target.get("finish") else str(target.get("status")), "color": target.get("color", "#FFFFFF")},
                    {"label": "Best Lap" if is_quali else "Grid", "value": str(target.get("best_lap") if is_quali else target.get("grid") or "—"), "color": "#A855F7"},
                    {"label": "Team", "value": target.get("team", ""), "color": target.get("color", "#FFFFFF")},
                    {"label": "Session", "value": session_name, "color": "#00F5D4"},
                ]), "label": label}
    if target:
        return None

    # A specific position ("who was P3?", "who finished third?")
    m = _POS_Q.search(q)
    pos = int(next(g for g in m.groups() if g)) if m else _ordinal_position(q)
    if pos:
        d = next((x for x in drivers if x.get("finish") == pos), None)
        if d:
            return {"role": "assistant", "text": _driver_line(d, session, session_name, knockout),
                    "tool": f"{session}_position_lookup", "intent": f"{label} — P{pos}", "a2ui_card": None, "label": label}

    if not _RESULT_Q.search(q):
        return None
    top = drivers[:3]
    p1 = top[0]
    if re.search(r"\b(top (?:five|5|ten|10)|results?|classification)\b", q):
        n = 10 if re.search(r"ten|10|results?|classification", q) else 5
        rows = ", ".join(f"P{d.get('finish')} {d['name']}" + (f" ({d.get('best_lap')})" if is_quali and d.get("best_lap") else "")
                         for d in drivers[:n])
        text = f"**{session_name} — top {n}:** {rows}."
    elif is_quali:
        pole_kind = "sprint pole" if session == "sprint_qualifying" else "pole position"
        no_winner = (f"{session_name} doesn't have a winner; the fastest driver takes {pole_kind}. "
                     if re.search(r"\b(won|winner|win)\b", q) else "")
        p2 = top[1] if len(top) > 1 else None
        gap = f", {p2.get('pole_delta')} ahead of **{p2['name']}**" if p2 and str(p2.get("pole_delta", "")).startswith("+") else ""
        lap = f" with **{p1.get('best_lap')}**" if p1.get("best_lap") else ""
        rest = ", ".join(f"P{d.get('finish')} {d['name']}" for d in top[1:])
        text = f"{no_winner}**{p1['name']}** took **{pole_kind}** for {p1['team']}{lap}{gap}. Top three: P1 {p1['name']}, {rest}."
    else:
        rest = " and ".join(f"**{d['name']}** (P{d.get('finish')})" for d in top[1:])
        grid = f" from P{p1['grid']} on the grid" if isinstance(p1.get("grid"), int) and p1["grid"] > 0 else ""
        text = f"**{p1['name']}** won the **{session_name}** for {p1['team']}{grid}, ahead of {rest}."
    return {"role": "assistant", "text": text, "tool": f"{session}_classification_lookup", "intent": label,
            "a2ui_card": _card(scope, session, f"{session_name} — {race_name}", [
                {"label": "Pole" if is_quali else "Winner", "value": f"{p1['name']} ({p1['code']})", "color": p1.get("color", "#FFFFFF")},
                {"label": "P2", "value": f"{top[1]['name']} ({top[1]['code']})" if len(top) > 1 else "—", "color": top[1].get("color", "#64748B") if len(top) > 1 else "#64748B"},
                {"label": "P3", "value": f"{top[2]['name']} ({top[2]['code']})" if len(top) > 2 else "—", "color": top[2].get("color", "#64748B") if len(top) > 2 else "#64748B"},
                {"label": "Session", "value": session_name, "color": "#00F5D4"},
            ]), "label": label}
