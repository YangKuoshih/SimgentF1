"""Semantic router: which intent (and so which tools) a question is asking for.

Intents and their example questions live in agent/intents.toml. Every example is embedded once
with the static embedding model (app/agent/embedding.py); a question goes to the intent with
the closest example, unless the match is weak or too close to call, in which case the router
abstains. Without the model files it scores the same examples lexically (BM25), so the agent
still works on a fresh clone.

Step 1 of docs/AGENT_ARCHITECTURE.md: the router runs in shadow mode, measured against the
current engine by tests/eval_router.py; it does not change answers yet.
"""

import math
import os
import re
import tomllib
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

import numpy as np

from app.agent.embedding import StaticEmbedder

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INTENTS_FILE = os.path.join(ROOT, "agent", "intents.toml")

# Step 3a: when the engine's answer doesn't fit a confident route, the engine is asked again in
# the intent's canonical phrasing. Overriding a *specific* engine answer (another intent's tool)
# needs this much more confidence than replacing a generic fallback.
OVERRIDE_MIN_SCORE = 0.60
OVERRIDE_MARGIN = 0.10
FALLBACK_TOOLS = {"session_telemetry_briefing", ""}  # curated memory answers are specific, not fallbacks
# Correct statements, never overridden: the weekend had no sprint, the session isn't in the data,
# the season is before 1950 or not run yet (the router's canonical phrasing drops the year).
DEFINITIVE_TOOLS = {"no_sprint_weekend", "qualifying_not_in_data", "sprint_not_in_data",
                    "sprint_qualifying_not_in_data", "season_out_of_range"}
# "No race result yet" is definitive for questions about the Grand Prix itself, not for
# qualifying, standings, careers or rules ("who got bounced in the first session?").
RACE_INTENTS = {"session_result", "finishing_position", "driver_result", "podium_check", "starting_grid",
                "retirements", "driver_retirement", "fastest_lap", "pit_strategy", "safety_car", "race_story"}
_SESSION_WORDS = re.compile(r"\b(sprint qualifying|sprint shootout|sprint|qualifying|quali|shootout|grand prix|gp|race)\b")

# Tuned on tests/eval_router.py and its held-out paraphrases (docs/AGENT_ARCHITECTURE.md)
LEX_WEIGHT = 0.3   # share of the score from BM25 keyword overlap (catches exact terms: Q1, pole, DNF)
TOP_K = 2          # an intent scores the mean of its best TOP_K examples (one lucky example is not enough)
MIN_SCORE = float(os.environ.get("SIMGENT_ROUTER_MIN_SCORE", "0.40"))
MARGIN = float(os.environ.get("SIMGENT_ROUTER_MARGIN", "0.02"))

_WORD = re.compile(r"[a-z0-9]+")
_NAME_FIELDS = re.compile(r'"(givenName|familyName|code|raceName|circuitName|locality|country)"\s*:\s*"([^"]+)"')
# Words that appear in race or circuit names but carry the question's meaning; never masked.
_KEEP = {"the", "grand", "prix", "gp", "circuit", "street", "park", "new", "de", "del", "di", "la", "le",
         "of", "and", "van", "von", "st", "san", "international", "autodromo", "ring", "race", "speed"}
# ("city", as in Mexico City, is masked like any place name)
_YEAR = re.compile(r"\b(19[5-9]\d|20[0-4]\d)\b")
_POSITION = re.compile(r"\bp\s*\d{1,2}\b|\b\d{1,2}(?:st|nd|rd|th)\b|\brunner[- ]?up\b|\b(?:first|second|third|fourth|fifth|"
                       r"sixth|seventh|eighth|ninth|tenth|eleventh|twelfth|thirteenth|fourteenth|fifteenth|sixteenth|"
                       r"seventeenth|eighteenth|nineteenth|twentieth|last)\b")
_PRONOUN = re.compile(r"\b(he|him|his|she|her|they|them|their)\b")
_SEGMENT = re.compile(r"\bs?q[123]\b")


@lru_cache(maxsize=1)
def _vocab() -> Tuple[frozenset, frozenset]:
    """(driver name words, place name words) from the cached data."""
    import glob
    drivers, places = set(), set()
    for path in glob.glob(os.path.join(ROOT, "data", "cache", "jolpica", "*.json")):
        with open(path, encoding="utf-8") as f:
            for key, value in _NAME_FIELDS.findall(f.read()):
                words = {w for w in re.findall(r"[a-z\u00c0-\u024f]+", value.lower()) if len(w) > 2}
                (drivers if key in ("givenName", "familyName", "code") else places).update(words)
    return frozenset(drivers - _KEEP), frozenset(places - _KEEP)


def driver_tokens() -> frozenset:
    return _vocab()[0]


@lru_cache(maxsize=1)
def name_tokens() -> frozenset:
    """Driver, race, circuit and country name words, for masking: the router should learn the
    shape of a question, not who or where it is about."""
    return _vocab()[0] | _vocab()[1]


def slots(question: str) -> Dict[str, bool]:
    """What the question names, for intents that require it."""
    q = question.lower()
    tokens = re.findall(r"[a-z\u00c0-\u024f]+", q)
    names = [t for t in tokens if t in driver_tokens()]
    return {"driver": bool(names) or bool(_PRONOUN.search(q)), "position": bool(_POSITION.search(q)),
            "year": bool(_YEAR.search(q)), "segment": bool(_SEGMENT.search(q))}


def mask(question: str) -> str:
    """The question without names and years."""
    q = _YEAR.sub(" ", question.lower())
    return " ".join(t for t in re.findall(r"[a-z0-9\u00c0-\u024f']+|[?]", q) if t not in name_tokens())


@dataclass
class Intent:
    name: str
    description: str
    tools: List[str]
    examples: List[str]
    not_examples: List[str] = field(default_factory=list)
    requires: List[str] = field(default_factory=list)
    excludes: List[str] = field(default_factory=list)
    canonical: Optional[str] = None


_SEGMENT_WORDS = re.compile(r"\b(first|second|third|final|last)\s+(?:segment|session|part|phase)\b")
_SEGMENT_NUMBER = {"first": 1, "second": 2, "third": 3, "final": 3, "last": 3}
_SUBJECT = re.compile(r"\b(he|she|they)\b")
_POSSESSIVE = re.compile(r"\b(his|her|their)\b")


def _name_groups(words: List[str], vocab: frozenset) -> List[str]:
    """Consecutive words from the vocabulary, as phrases ("max verstappen", "abu dhabi")."""
    groups, cur = [], []
    for w in words:
        if w in vocab:
            cur.append(w)
        elif cur:
            groups.append(" ".join(cur))
            cur = []
    if cur:
        groups.append(" ".join(cur))
    return groups


def slot_values(question: str) -> Dict[str, str]:
    """The question's own words for each slot, to fill an intent's canonical phrasing."""
    q = question.lower()
    words = re.findall(r"[a-z\u00c0-\u024f]+", q)
    drivers = _name_groups(words, driver_tokens())
    places = [g for g in _name_groups(words, name_tokens() - driver_tokens()) if g]
    out: Dict[str, str] = {}
    if drivers:
        out["driver"] = drivers[0]
        out["driver_poss"] = drivers[0] + "'s"
        if len(drivers) > 1:
            out["driver2"] = drivers[1]
    else:
        subj, poss = _SUBJECT.search(q), _POSSESSIVE.search(q)
        if subj or poss:
            out["driver"] = subj.group(1) if subj else "he"
            out["driver_poss"] = poss.group(1) if poss else "his"
    pos = _POSITION.search(q)
    if pos:
        out["position"] = pos.group(0)
    seg = _SEGMENT.search(q)
    if seg:
        out["segment"] = seg.group(0)
    else:
        w = _SEGMENT_WORDS.search(q)
        if w:
            out["segment"] = ("sq" if "sprint" in q else "q") + str(_SEGMENT_NUMBER[w.group(1)])
    year = _YEAR.search(q)
    if year:
        out["year"] = year.group(1)
    race = ([year.group(1)] if year else []) + places
    if race:
        out["race"] = "in the " + " ".join(race) + (" grand prix" if places else " season")
    out["race_name"] = ("the " + " ".join(race) + " grand prix") if places else "this race"
    return out


def canonical(question: str, intent: "Intent") -> Optional[str]:
    """The intent's canonical phrasing filled with the question's own slot values, or None when
    the intent has none or a slot it needs is missing."""
    if not intent.canonical:
        return None
    values = slot_values(question)
    needed = re.findall(r"\{(\w+)\}", intent.canonical)
    if any(n in ("driver", "driver2", "position") and n not in values for n in needed):
        return None
    text = intent.canonical
    session = _SESSION_WORDS.search(question.lower())
    for n in needed:
        if n in values:
            text = text.replace("{" + n + "}", values[n])
        else:  # drop the empty slot and a preposition left dangling before it
            text = re.sub(r"\b(?:in|at|for|of)\s+\{" + n + r"\}|\{" + n + r"\}", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    # Keep the session the question named ("who won the sprint" must not become "who won")
    if session and not _SESSION_WORDS.search(text.lower()):
        text += f" in the {session.group(1)}"
    return text


@dataclass
class Route:
    intent: Optional[str]        # None = abstain
    best: str                    # closest intent, even when abstaining
    score: float
    runner_up: Optional[str]
    margin: float
    method: str                  # "embedding" or "lexical"
    tools: List[str] = field(default_factory=list)


def load_intents(path: str = INTENTS_FILE) -> List[Intent]:
    with open(path, "rb") as f:
        data = tomllib.load(f)
    out = []
    for name, spec in data.items():
        if not spec.get("examples") or not spec.get("tools"):
            raise ValueError(f"intent {name!r} needs examples and tools")
        out.append(Intent(name, spec.get("description", ""), list(dict.fromkeys(spec["tools"])),
                          spec["examples"], spec.get("not", []), spec.get("requires", []), spec.get("excludes", []),
                          spec.get("canonical")))
    return out


class _BM25:
    """Lexical fallback over the same examples (k1=1.2, b=0.75)."""

    def __init__(self, docs: List[str]):
        self.docs = [Counter(_WORD.findall(d.lower())) for d in docs]
        self.lens = [sum(d.values()) for d in self.docs]
        self.avg = sum(self.lens) / max(1, len(self.lens))
        df = Counter(w for d in self.docs for w in d)
        n = len(self.docs)
        self.idf = {w: math.log(1 + (n - c + 0.5) / (c + 0.5)) for w, c in df.items()}

    def scores(self, query: str) -> np.ndarray:
        words = _WORD.findall(query.lower())
        out = np.zeros(len(self.docs), dtype=np.float32)
        for i, (d, ln) in enumerate(zip(self.docs, self.lens)):
            s = 0.0
            for w in words:
                if w in d:
                    tf = d[w]
                    s += self.idf[w] * tf * 2.2 / (tf + 1.2 * (1 - 0.75 + 0.75 * ln / self.avg))
            out[i] = s
        # squash to 0..1 so the same thresholds roughly apply
        return out / (out.max() + 1e-9) * min(1.0, out.max() / 8.0) if out.max() > 0 else out


class Router:
    def __init__(self, intents: List[Intent], embedder: Optional[StaticEmbedder]):
        self.intents = {i.name: i for i in intents}
        self.embedder = embedder
        self.method = "embedding" if embedder else "lexical"
        self._ex_owner: List[str] = []
        self._ex_text: List[str] = []
        self._not_owner: List[str] = []
        self._not_text: List[str] = []
        for i in intents:
            self._ex_owner += [i.name] * len(i.examples)
            self._ex_text += i.examples
            self._not_owner += [i.name] * len(i.not_examples)
            self._not_text += i.not_examples
        ex, nots = [mask(t) for t in self._ex_text], [mask(t) for t in self._not_text]
        self._bm25 = _BM25(ex)
        self._bm25_not = _BM25(nots) if nots else None
        if embedder:
            self._ex = embedder.embed(ex)
            self._not = embedder.embed(nots) if nots else np.zeros((0, embedder.dim), np.float32)

    def tool_intents(self) -> Dict[str, List[str]]:
        """tool name -> intents that serve it."""
        out: Dict[str, List[str]] = {}
        for i in self.intents.values():
            for t in i.tools:
                out.setdefault(t, []).append(i.name)
        return out

    def _similarities(self, question: str) -> Tuple[np.ndarray, np.ndarray]:
        """Per-example scores: embedding cosine blended with BM25, or BM25 alone without a model."""
        question = mask(question)
        lex = self._bm25.scores(question)
        lex_not = self._bm25_not.scores(question) if self._bm25_not else np.zeros(0)
        if not self.embedder:
            return lex, lex_not
        q = self.embedder.embed([question])[0]
        cos_not = self._not @ q if len(self._not) else np.zeros(0, np.float32)
        return (1 - LEX_WEIGHT) * (self._ex @ q) + LEX_WEIGHT * lex, (1 - LEX_WEIGHT) * cos_not + LEX_WEIGHT * lex_not

    def scores(self, question: str) -> Dict[str, float]:
        """Best example similarity per intent; an intent whose near misses match the question
        better than its examples is ruled out (score 0)."""
        ex, nots = self._similarities(question)
        per: Dict[str, List[float]] = {}
        for owner, s in zip(self._ex_owner, ex):
            per.setdefault(owner, []).append(float(s))
        best = {o: float(np.mean(sorted(v, reverse=True)[:TOP_K])) for o, v in per.items()}
        for owner, s in zip(self._not_owner, nots):
            if float(s) >= best.get(owner, 0.0):
                best[owner] = 0.0
        have = slots(question)
        for name, intent in self.intents.items():
            if any(not have.get(slot, False) for slot in intent.requires) or any(have.get(slot) for slot in intent.excludes):
                best[name] = 0.0
        return best

    def route(self, question: str) -> Route:
        ranked = sorted(self.scores(question).items(), key=lambda kv: -kv[1])
        (top, s1), (second, s2) = ranked[0], ranked[1] if len(ranked) > 1 else (None, 0.0)
        margin = s1 - s2
        chosen = top if (s1 >= MIN_SCORE and margin >= MARGIN) else None
        return Route(chosen, top, round(s1, 4), second, round(margin, 4), self.method,
                     self.intents[chosen].tools if chosen else [])


@lru_cache(maxsize=1)
def get_router() -> Router:
    return Router(load_intents(), StaticEmbedder.load())
