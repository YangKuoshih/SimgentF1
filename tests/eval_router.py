"""Router shadow eval: would the semantic router pick the same answer as the current engine?

Runs the three agent evals (session scope, multi-turn, cross-era) offline, records every
question with the tool the engine answered with, and routes each question with
app/agent/router.py. A question agrees when the router's intent lists that tool in
agent/intents.toml. Abstentions (weak or close matches) are reported separately; in step 1 the
router never answers on its own, so an abstention just means "keep the current behaviour".

  python tests/eval_router.py                  # summary + disagreements
  python tests/eval_router.py --all            # also list every abstention
  python tests/eval_router.py --paraphrases    # held-out phrasings (tests/router_paraphrases.toml)
  add --gate to exit non-zero below the step 1 bar (CI): agreement >= 95%; paraphrases at
  most 3 wrong and at least 70% correct; the embedding model must be present.
"""
import contextlib
import io
import os
import runpy
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app.tools import jolpica_sync as J, openf1_sync as O  # noqa: E402

J._http = lambda url, retries=4: None   # offline: cache only, never write the cache
O._http = lambda path, retries=4: None

import app.tools.race_agent as A  # noqa: E402
from app.agent.router import get_router  # noqa: E402

EVALS = ["eval_session_scope.py", "eval_multi_turn.py", "eval_cross_era.py"]


def record_eval_questions():
    records = []
    original = A.answer_race_engineer_query

    def recording(query, context=None, history=None):
        resp = original(query, context, history)
        records.append((query, context, list(history or []), resp.get("tool")))
        return resp

    A.answer_race_engineer_query = recording
    argv = sys.argv
    try:
        for name in EVALS:
            path = os.path.join(ROOT, "tests", name)
            sys.argv = [path]  # each eval sees no arguments (they read their own filters)
            with contextlib.redirect_stdout(io.StringIO()):
                try:
                    runpy.run_path(path, run_name="__main__")
                except SystemExit:
                    pass
    finally:
        A.answer_race_engineer_query = original
        sys.argv = argv
    return records


def paraphrases():
    """Held-out phrasings (tests/router_paraphrases.toml): does the router generalise?"""
    import tomllib
    with open(os.path.join(ROOT, "tests", "router_paraphrases.toml"), "rb") as f:
        cases = tomllib.load(f)["cases"]
    router = get_router()
    right = wrong = abstain = 0
    for question, expected in cases.items():
        r = router.route(question)
        got = r.intent or "none"
        if got == expected:
            right += 1
        elif r.intent is None:
            abstain += 1
            print(f"ABSTAIN  {question!r} expected={expected} best={r.best} ({r.score:.2f}, margin {r.margin:.2f})")
        else:
            wrong += 1
            print(f"WRONG    {question!r} expected={expected} router={r.intent} ({r.score:.2f}, next {r.runner_up} +{r.margin:.2f})")
    n = len(cases)
    print(f"paraphrases: {right}/{n} correct = {100 * right / n:.1f}%  (wrong {wrong}, abstained {abstain})")
    return wrong <= 3 and right / n >= 0.70


def main():
    gate = "--gate" in sys.argv
    if gate and get_router().method != "embedding":
        print("FAIL: embedding model missing (run scripts/fetch_models.py)")
        sys.exit(1)
    if "--paraphrases" in sys.argv:
        ok = paraphrases()
        sys.exit(0 if ok or not gate else 1)
    router = get_router()
    by_tool = router.tool_intents()
    seen = set()
    stats = Counter()
    disagreements, abstentions = [], []
    per_intent = defaultdict(lambda: [0, 0])
    for query, ctx, history, tool in record_eval_questions():
        if tool not in by_tool:
            stats["unmapped tool"] += 1
            continue
        question = A.resolve_follow_up(query, A.scope_history_to_view(history, ctx))
        if (question, tool) in seen:
            continue
        seen.add((question, tool))
        route = router.route(question)
        expected = by_tool[tool]
        if route.intent is None:
            stats["abstained"] += 1
            abstentions.append((question, tool, route))
        elif route.intent in expected:
            stats["agree"] += 1
        else:
            stats["disagree"] += 1
            disagreements.append((question, tool, route))
        for e in expected:
            per_intent[e][1] += 1
            per_intent[e][0] += route.intent in expected
    routed = stats["agree"] + stats["disagree"]
    total = routed + stats["abstained"]
    print(f"router: {router.method}, {len(router.intents)} intents")
    print(f"questions: {total} unique (unmapped tools skipped: {stats['unmapped tool']})")
    print(f"agreement when routed: {stats['agree']}/{routed} = {100 * stats['agree'] / max(1, routed):.1f}%")
    print(f"abstained: {stats['abstained']}/{total} = {100 * stats['abstained'] / max(1, total):.1f}%")
    print("by intent (agree/expected):")
    for name, (ok, n) in sorted(per_intent.items(), key=lambda kv: kv[1][0] / kv[1][1]):
        print(f"  {name:24} {ok:>4}/{n:<4}")
    for q, tool, r in disagreements:
        print(f"DISAGREE {q!r} engine={tool} router={r.intent} ({r.score:.2f}, next {r.runner_up} +{r.margin:.2f})")
    if "--all" in sys.argv:
        for q, tool, r in abstentions:
            print(f"ABSTAIN  {q!r} engine={tool} best={r.best} ({r.score:.2f}, margin {r.margin:.2f})")
    if gate and stats["agree"] / max(1, routed) < 0.95:
        print("FAIL: agreement below 95%")
        sys.exit(1)


if __name__ == "__main__":
    main()
