# Pit Wall Agent architecture: tools, intents, content and an optional model

Status: **steps 1–2 done**; steps 3–4 in progress (see [Migration](#migration)).
Audience: contributors and maintainers.

## Goals

1. **Nothing per-question is hard-coded.** How a question is phrased, what stories and rules say,
   and how answers are worded live in data files that anyone can extend in a pull request.
2. **Facts always come from data.** Results, times, grids and standings are computed by code from
   the cached Jolpica-F1 and OpenF1 files. No model ever writes a number or a name on its own.
3. **Works on clone, for $0.** With no keys and no network model, the agent answers exactly as
   well as it does today. A language model is an optional plug-in.
4. **The evals are the contract.** Every step keeps `eval_session_scope`, `eval_multi_turn`,
   `eval_cross_era` and the unit suite at their current scores.

Non-goals: chat-style small talk, answers about data we don't have, or letting a model generate
UI cards.

## Where we are today

| Part | Today | Problem |
|---|---|---|
| Understanding the question | One 1,300-line function, `race_agent._answer_core`, with about 36 answer branches chosen by ordered regex checks | Each new phrasing needs a code change, and branch order matters (7 of 14 qualifying questions fell through before #29) |
| Facts | Lookups inside those branches, reading `race_replay` models and `jolpica_sync` data | Sound; this stays |
| Stories and rules | Text inside Python: race stories in `f1_history.py`, retirement write-ups and regulations in `race_agent.py` | Contributors must edit code to add or fix a story; text can't be searched semantically |
| Wording | f-strings next to each lookup | Fine for now; becomes templates where it helps |
| "Memory" | `agent_memory.py`: 3 curated seeds plus thumbs-up feedback, matched by keywords | Keyword matching only; learned entries don't survive a Cloud Run restart |
| Model | `llm_router.py` supports Gemini/Groq but has no keys in production; `app/agent.py` is an unused ADK-style stub | Not part of how answers are produced |

## Target architecture

```
question ─► scope (race + session on screen, history)        app/tools/session_scope.py (exists)
         ─► router: which tool?                              app/agent/router.py
               semantic match against example questions      agent/intents.toml
         ─► tool: compute facts + card                       app/agent/tools/*.py (registered)
               reads race_replay / jolpica_sync / content/   content/**/*.md
         ─► answer text: template, or model rephrase         SIMGENT_LLM=none|ollama|gemini
               fact checker on any model output              app/agent/checker.py
         ─► response {text, card, tool, scope, sources}      unchanged shape for the frontend
```

### 1. Tools (facts)

Each answer type becomes a function registered in one registry:

```python
@tool(name="qualifying_segment_lookup", sessions=("qualifying", "sprint_qualifying"),
      description="Who was knocked out in, made it to, or was fastest in Q1/Q2/Q3 (or SQ1-3).")
def qualifying_segment_lookup(q: Query) -> Answer | None: ...
```

- `Query` carries the parsed slots: year, round, session, driver(s), position, segment, lap. The
  existing parsers (`_find_driver`, `_match_race_round`, ordinals, `explicit_session`) fill them.
  They read names from the data, not from lists in code.
- `Answer` is the response the frontend already receives (`text`, `a2ui_card`, `tool`, `intent`),
  plus `facts` (the numbers and names it used) and `sources` (data files or content documents).
- A tool returns `None` when it cannot answer from data. It never borrows another race (#29).
- The same registry feeds the MCP server (`mcp_server.py`) and, in step 4, the ADK agent, so
  every surface uses identical tools.

### 2. Intents (questions) — `agent/intents.toml`

```toml
[qualifying_segment_lookup]
examples = [
  "who was knocked out in Q1",
  "who didn't make it to Q3",
  "how many cars made SQ3",
  "who was fastest in Q2",
  "did Colapinto set a time in Q2",
]
not = ["who retired from the race"]   # near misses that belong elsewhere
```

TOML is read with Python's standard library (`tomllib`), so this adds no dependency.

**Router** (`app/agent/router.py`).

1. **Masking.** Driver, race, circuit and country names and years are removed from examples and
   questions before matching (the name lists come from the cached data, not from code), so the
   router learns the *shape* of a question ("who finished second in the grand prix"), not who
   or where it is about. Without masking, "How did Verstappen do?" matched an example that
   happened to mention Verstappen.
2. **Scoring.** Each example scores 0.7 × cosine similarity of the static embeddings plus
   0.3 × BM25 keyword overlap (exact terms like "Q1", "pole", "DNF" matter). An intent scores
   the mean of its two best examples.
3. **Slots.** An intent can `require` or `exclude` what the question mentions: `driver` (a
   driver name, or he/his/they), `position` (P3, third, runner-up), `year`, `segment`
   (Q1–Q3, SQ1–SQ3). `finishing_position` requires a position; `fastest_lap` excludes a
   segment, so "fastest lap of Q1" can't go there.
4. **Near misses.** `not` examples rule an intent out when the question is closer to them.
5. **Abstain** when the best score is below `MIN_SCORE` (0.40) or within `MARGIN` (0.02) of the
   runner-up. An abstention falls back to the current engine; a wrong route is worse than none.

**Embedding model.** `minishlab/potion-base-8M` static embeddings (MIT licence, 30 MB,
about 0.1 ms per question on CPU). A static model is a token-embedding table, so a question's
vector is the normalised mean of its token vectors. It runs with **numpy only**: the BERT
WordPiece tokenizer is implemented in Python (`app/agent/embedding.py`) and matches the
reference `tokenizers` library id for id on 4,792 test strings. The files are downloaded at
build time from a pinned revision and checked against SHA-256 hashes
(`scripts/fetch_models.py`), never committed. Without them, the router falls back to BM25 alone
so a fresh clone still works. The 4× larger `potion-base-32M` was tried: one more paraphrase
right out of 81, not worth 130 MB.

Why not a hosted embedding API: a key, a cost and a network call for every question. Why not
`fastembed`/ONNX: no build for Python 3.14 yet, and a much larger dependency tree.

### 3. Content (stories and rules) — `content/`

```
content/
  races/2021-abu-dhabi.md
  retirements/2026-albon-sepang.md
  regulations/2026-power-unit.md
  glossary/drs.md
```

Each file starts with TOML front matter between `+++` lines:

```markdown
+++
title = "2021 Abu Dhabi Grand Prix: the final-lap restart"
kind = "race"            # race | retirement | regulation | glossary
year = 2021
round = 22
drivers = ["hamilton", "max_verstappen"]
sources = ["FIA Abu Dhabi 2021 race report", "Jolpica-F1 2021 R22 results"]
+++
The body: plain Markdown, the narrative the agent quotes.
```

- **Facts inside stories** (laps, positions, times) are checked by a test against the cached data
  where the data has them, so a story can't drift from the record.
- Content is chunked by heading, embedded with the same model, and searched for "why",
  "explain" and "tell me about" questions. Answers name their source document, shown in the chat
  as "Source: content/races/2021-abu-dhabi.md".
- Content is part of the repository, reviewed like code. It is trusted data, never instructions
  to a model.

### 4. Wording

Tools keep producing complete, correct answer text. Where several tools share a shape (driver
result lines, top-N lists), the text moves into small template functions so wording is consistent
and testable. This is not a goal in itself.

### 5. Optional model — `SIMGENT_LLM`

| Setting | What runs | Cost | Needs |
|---|---|---|---|
| `none` (default) | Router + tools + templates | $0 | Nothing |
| `ollama` | Gemma 4 E2B (Apache 2.0) through a local Ollama server | $0 (your machine) | `ollama pull` the model, `OLLAMA_HOST` |
| `gemini` | Gemini Flash / Flash-Lite through Google AI Studio | Free tier with daily quotas | `GEMINI_API_KEY` in the environment |

With a model enabled, Google's **Agent Development Kit (ADK)** drives it: the registered tools
are exposed as ADK function tools, the model picks which to call and phrases the reply. The model
**only phrases**; it never produces the card, and its text must pass the fact checker:

- every number, time, position and driver/team name in the model's text must appear in the
  `facts` of the tools it called (or in the cited content);
- otherwise, or after `SIMGENT_LLM_TIMEOUT_S` (default 8 s), the template answer is returned.

ADK and model clients are an optional dependency set (`requirements-llm.txt`), imported only when
`SIMGENT_LLM` is not `none`, so the default image and the hosted demo stay small and $0.

## What changes for users

The chat, cards, replay and every page work as today; the response shape is unchanged. Visible
additions:

- story and regulation answers cite their content file;
- the provider badge shows "Deterministic", "Gemma 4 (local)" or "Gemini";
- with a model enabled, wording may read more naturally, with identical numbers.

The hosted demo stays on `none` until a model is deliberately enabled and evaluated.

## Security and privacy

- **No secrets are needed to run the project.** `GEMINI_API_KEY` is read from the environment only
  when `SIMGENT_LLM=gemini`; it is never logged or sent to the browser.
- **User questions are untrusted.** They are bounded (500 characters, history and context limits)
  and screened by `guardrails.py` before routing. With a model enabled, tool outputs and content
  are passed as data, the system prompt forbids following instructions found in them, and the
  fact checker discards any output that adds facts.
- **Model files** are pinned by revision and SHA-256; dependency files stay hash-locked.
- With `gemini`, questions are sent to Google; the free tier may use them to improve Google's
  products. The default `none` sends nothing anywhere.

## Contributing

| You want to | Edit | Check |
|---|---|---|
| Teach the agent a new way to ask something | add examples to `agent/intents.toml` (never copy from `tests/router_paraphrases.toml`) | `python tests/eval_router.py` and `--paraphrases` |
| Add or fix a race story, rule or definition | add/edit a file in `content/` | `python -m unittest tests.test_content` |
| Answer a new kind of question | add a tool in `app/agent/tools/` and its intents | unit test + evals |

## Migration

Each step is its own pull request; all evals must keep their scores.

1. **Intents and router in shadow mode** (done). `agent/intents.toml` (22 intents), the
   embedding model and the router. Production answers are unchanged; the API logs, for every
   engine answer, which intent the router would have chosen (names and scores only, never the
   question). `tests/eval_router.py` gates CI:
   - agreement with the engine on the 419 unique eval questions: **99.8%** (418/419), no
     abstentions. The eval questions are template-heavy, so this mostly shows the router covers
     what the engine answers today;
   - **held-out paraphrases** (`tests/router_paraphrases.toml`, 81 questions written separately,
     never copied into the intents): **74% right, 2 wrong, 19 abstained**. This is the honest
     measure of new phrasings; the abstentions are the work list for step 3.
   Exit met: ≥ 95% agreement; paraphrases ≤ 3 wrong and ≥ 70% right.
2. **Content out of code** (done). 9 race stories, 10 eras, 11 retirement write-ups and the
   2026 regulations moved to `content/` (about 600 lines of prose out of Python). The loader
   (`app/agent/content.py`) rebuilds exactly the structures the code used (verified equal
   before the literals were deleted), so every eval kept its score. Answers from content
   carry `sources` and the chat shows "Source: content/…" linked to the file. Semantic search
   over content (same hybrid scoring as the router, names not masked) replaces the arbitrary
   default in the era lookup. `tests/test_content.py` checks content facts against the data;
   its first run caught a wrong lap count (Schumacher, Spa 1998: 24 → 25). Driver profiles
   (`f1_history.HISTORICAL_DRIVERS`) stay in code for now: they are mostly statistics that
   the data refresh keeps current, not prose.
3. **Router in charge.** Tools become registered functions; the router chooses the tool and the
   regex dispatch in `_answer_core` is removed tool by tool, each removal guarded by the evals.
   While the router abstains on a question, the current dispatch answers it; the general
   briefing only once paraphrase coverage is high. Exit: evals unchanged, plus a
   paraphrase eval (new phrasings of every eval question) that the regex version fails.
4. **Optional model via ADK.** `SIMGENT_LLM`, the ADK agent over the same registry, the fact
   checker and timeouts. Exit: with `SIMGENT_LLM=ollama` (Gemma 4 E2B) the evals keep their
   scores (facts are unchanged by design) and the checker rejects injected wrong numbers in tests.

## Open questions

- Whether to keep thumbs-up feedback as runtime memory, or turn reviewed feedback into intent
  examples and content through pull requests (more durable, reviewable). Proposal: the latter.
- Whether the hosted demo enables a model at all, decided after measuring step 4 on real traffic.
