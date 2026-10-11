"""Stories, eras, retirement write-ups and regulations from content/ (not from code).

Each file in content/<kind>/ is Markdown with TOML front matter between +++ lines:

    +++
    title = "..."
    year = 2021
    sources = ["..."]
    +++
    The body: the text the agent quotes.

Facts that the data can check (laps, rounds, race names) are tested against the cached
Jolpica-F1 data in tests/test_content.py. Content is reviewed like code and is data, never
instructions to a model. See docs/AGENT_ARCHITECTURE.md.
"""

import os
import re
import tomllib
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONTENT_DIR = os.path.join(ROOT, "content")

# The body of each kind fills this field of the structure the agent uses.
BODY_FIELD = {"races": "summary", "eras": "ai_analysis", "retirements": "explanation", "regulations": "text"}
_FRONT = re.compile(r"\A\+\+\+\n(.*?)\n\+\+\+\n(.*)\Z", re.S)


def parse(path: str) -> Tuple[Dict[str, Any], str]:
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    m = _FRONT.match(raw)
    if not m:
        raise ValueError(f"{path}: missing +++ TOML front matter")
    body = m.group(2)
    if body.endswith("\n"):
        body = body[:-1]  # files end with one newline; the body text does not
    return tomllib.loads(m.group(1)), body


def rel(path: str) -> str:
    return os.path.relpath(path, ROOT)


@lru_cache(maxsize=None)
def documents(kind: str) -> List[Dict[str, Any]]:
    """Every document of a kind, as {front matter..., body field: body, "source_file": path},
    in file-name order."""
    folder = os.path.join(CONTENT_DIR, kind)
    out = []
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".md"):
            continue
        path = os.path.join(folder, name)
        meta, body = parse(path)
        doc = {k: v for k, v in meta.items() if k not in ("order", "sources")}
        doc[BODY_FIELD[kind]] = body
        doc["source_file"] = rel(path)
        doc["sources"] = meta.get("sources", [])
        doc["_order"] = meta.get("order", 0)
        out.append(doc)
    out.sort(key=lambda d: d["_order"])
    return out


def _strip(doc: Dict[str, Any], *extra: str) -> Dict[str, Any]:
    return {k: v for k, v in doc.items() if k not in ("source_file", "sources", "_order") + extra}


def race_stories() -> List[Dict[str, Any]]:
    """Iconic race stories (was f1_history.HISTORIC_RACE_STORIES)."""
    return [_strip(d) for d in documents("races")]


def eras() -> Dict[str, Dict[str, Any]]:
    """Technical and regulatory eras keyed by id (was f1_history.HISTORICAL_ERAS)."""
    return {d["id"]: _strip(d) for d in documents("eras")}


def retirements() -> Dict[Tuple[int, str, str], Dict[str, Any]]:
    """Curated retirement write-ups keyed by (year, circuit_id, driver code or id)
    (was race_agent.CURATED_RETIREMENTS)."""
    return {(d["year"], d["circuit_id"], d["driver"]): _strip(d, "year", "circuit_id", "driver")
            for d in documents("retirements")}


def regulation(doc_id: str) -> Optional[Dict[str, Any]]:
    return next((_strip(d) for d in documents("regulations") if d.get("id") == doc_id), None)


def source_of(kind: str, **match: Any) -> Optional[str]:
    """content/ path of the document whose front matter matches, for citing it in answers."""
    for d in documents(kind):
        if all(d.get(k) == v for k, v in match.items()):
            return d["source_file"]
    return None


# ---------------------------------------------------------------- semantic search
# Same scoring as the router: static-embedding cosine blended with BM25 keyword overlap.
# Unlike the router, names are NOT masked: here they are what the question is about.
SEARCH_LEX_WEIGHT = 0.3


@lru_cache(maxsize=None)
def _index(kind: str):
    from app.agent.embedding import StaticEmbedder
    from app.agent.router import _BM25
    docs = documents(kind)
    texts = [" ".join([str(d.get("title", "")), " ".join(d.get("keywords", []) or []), str(d.get("years", "")),
                       str(d.get(BODY_FIELD[kind], ""))]) for d in docs]
    embedder = StaticEmbedder.load()
    vectors = embedder.embed(texts) if embedder else None
    return docs, embedder, vectors, _BM25(texts)


def search(query: str, kind: str, k: int = 3) -> List[Tuple[Dict[str, Any], float]]:
    """Best-matching documents of a kind for a question, with scores (highest first)."""
    docs, embedder, vectors, bm25 = _index(kind)
    lex = bm25.scores(query)
    if embedder is not None:
        cos = vectors @ embedder.embed([query])[0]
        score = (1 - SEARCH_LEX_WEIGHT) * cos + SEARCH_LEX_WEIGHT * lex
    else:
        score = lex
    order = sorted(range(len(docs)), key=lambda i: -float(score[i]))[:k]
    return [(docs[i], round(float(score[i]), 4)) for i in order]
