# Contributing to SimGent

Start with the setup instructions in [README.md](README.md). Use a feature branch
and submit a pull request describing the problem, the change, and how you tested it.

## Project layout

- `app/`: race engineering, data verification, memory, and simulation logic.
- `frontend/`: FastAPI server and browser interface.
- `data/cache/`: reference race data with provenance in `MANIFEST.json`.
- `data/seed/`: curated public memory examples; no conversations or user corrections.
- `data/runtime/`: private feedback and learned memory; never commit or upload it.
- `tests/`, `docs/`, `gcp/`: verification, documentation, and cloud tooling.

## Verification

Run `python -m unittest discover tests`, `python tests/test_season_robustness.py`,
`python tests/check_data_integrity.py`, `python -m app.tools.data_manifest --check`,
`python tests/eval_cross_era.py`, and `python tests/eval_multi_turn.py`.
After `npm ci` and `npx playwright install chromium`, use `npm test` for the Python
and browser suites with a temporary server. Port 8080 must be available.
Some tests contact external data providers; disclose offline-only validation.

Follow [the data pipeline guide](docs/DATA_PIPELINE.md) to update reference data.
Do not hand-edit cached results to make a test pass.

## Privacy and secrets

Do not commit credentials, real feedback, conversation transcripts, learned user
corrections, local agent configuration, or generated build outputs. Inspect
`git diff --cached` before committing and run `gitleaks git . --redact` when available.
Use synthetic records and temporary storage in tests.

Changes to public seeds must be curated, reviewed, and attributable to reference
sources. Anonymous feedback is recorded privately and never automatically promoted
into shared memory; an authenticated operator must review it.

## Reproducible dependencies and fuzzing

Install runtime dependencies with `pip install --require-hashes -r requirements.txt`.
Edit `requirements.in` and regenerate the cross-platform lock using
`uv pip compile --universal --python-version 3.11 --generate-hashes requirements.in -o requirements.txt`.
Review upgrades and run the dependency audit before merging the lock.
`requirements-fuzz.txt` is a separate hash lock for Atheris on Linux/Python 3.11.
Run `python tests/fuzz/fuzz_boundaries.py --smoke` on any supported platform;
CI additionally runs coverage-guided fuzzing for 60 seconds. Longer local Linux runs
can increase `-max_total_time`. This is a bounded check, not exhaustive assurance.

Scheduled data sync pushes a verified review branch. A maintainer opens its pull
request so ordinary PR CI runs. Require an independent reviewer before merging;
never merge an old clone's history after the October 2026 cleanup.

## Release verification

The Signed release archives workflow archives an existing tag, records its exact
source commit, and signs the archive's provenance with GitHub's workload identity.
Download the `.tar.gz` and `.intoto.jsonl` assets, then run
`gh attestation verify f1-simgent-v1.4.0.tar.gz --bundle f1-simgent-v1.4.0.tar.gz.intoto.jsonl --repo YangKuoshih/SimgentF1 --predicate-type https://github.com/YangKuoshih/SimgentF1/source-archive/v1`.
Use the downloaded bundle because GitHub’s API filter does not accept custom predicate URIs.
Confirm `resolvedDependencies` identifies the intended tag and commit. Historical
archives are produced from rewritten tags; signatures are generated now and do not
claim that the original releases were reviewed or signed. Git tags themselves are
not cryptographically signed.

The budget-alert tool has its own lock at `gcp/kill_switch/requirements.txt`;
audit it separately with `pip-audit --require-hashes -r gcp/kill_switch/requirements.txt`.
Regenerate it from `gcp/kill_switch/requirements.in` using the same universal hash-lock command.

Main's policy in `docs/MAIN_PROTECTION.json` requires pull requests, current CI
checks, resolved review conversations, and one approval with stale approvals
dismissed. There is no administrator bypass. Add another trusted collaborator
for independent approvals: the PR author cannot approve their own changes.
Direct pushes, force pushes, and deletion are blocked.
