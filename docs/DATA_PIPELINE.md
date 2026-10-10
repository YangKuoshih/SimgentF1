# How race data gets into SimGent (and stays correct)

Every file under `data/cache/` comes from one of two free, open community APIs and is checked before it is committed.

| Data | Source |
|---|---|
| Race results, starting grid (`grid`), qualifying, sprint results (2021 on), sprint grid, pit stops, lap timing, schedule, winners, standings | [Jolpica](https://github.com/jolpica/jolpica-f1) (Ergast-compatible API), stored exactly as served |
| Sprint Qualifying (2024 on) / Sprint Shootout (2023) | [OpenF1](https://openf1.org) `session_result` + `drivers` (Jolpica does not publish it), cached under `data/cache/openf1/` |

Before 2023 there was no separate sprint qualifying session: the 2021–2022 sprint grids were set by Friday qualifying, which Jolpica publishes.

OpenF1 data is licensed CC BY-NC-SA 4.0 (non-commercial, share-alike, see `data/cache/openf1/LICENSE.md`). Neither source is affiliated with Formula 1.

## The safeguards

1. **Provenance manifest** (`data/cache/MANIFEST.json`). Every fetcher write records the source URL, time and SHA-256 of the file (`app/tools/data_manifest.py`). A file that was hand-edited, generated, or added outside the fetchers fails the integrity gate.
2. **Refresh policy.** `app/tools/jolpica_sync.py` re-fetches races from the last 21 days when the cached copy is older than 6 hours, so late penalties, disqualifications and grid changes are picked up. Schedules refresh daily. Older seasons are re-checked weekly by `app/tools/revalidate.py`, which replaces any file whose content no longer matches Jolpica. `app/tools/openf1_sync.py` fetches each Sprint Qualifying as soon as OpenF1 publishes it and re-fetches sessions from the last 21 days; the weekly run re-fetches every season from 2023. If the app is asked for a sprint qualifying session that is not cached yet, it fetches it from OpenF1 on demand.
3. **Offline integrity gate** (`tests/check_data_integrity.py`). Standings must equal the sum of race + sprint points and wins; sprint grids must be real (not a copy of the finishing order); sprint weekends from 2023 must have a Sprint Qualifying/Shootout file whose drivers match the sprint; lap timing must not be synthetic and must agree with laps completed; pit stops must agree with the classification; winners files must agree with results; every file must match the manifest.

## When it runs

- `sync_data.yml`, every 6 hours: fetch Jolpica → fetch OpenF1 Sprint Qualifying → revalidate → integrity gate → agent evals → commit the verified `data/cache/` files to `main` → deploy to Cloud Run (`deploy.yml`, called only when data changed). A failing step stops the job, so bad data never reaches `main` or the live site. If `main` rejects the push (branch protection), the data goes to an `automation/verified-data-*` review branch instead and nothing is deployed. The commit step refuses to publish anything outside `data/cache/`.
- `sync_data.yml`, Wednesdays (or manual with *full_revalidate*): the same, with every cached season re-checked against Jolpica and every Sprint Qualifying re-fetched from OpenF1.
- `ci.yml`, every push and PR: integrity gate, manifest check and both agent evals (`eval_cross_era.py`, `eval_multi_turn.py`).

## Running it by hand

```bash
python -m app.tools.jolpica_sync 2026 --laps            # fetch Jolpica
python -m app.tools.openf1_sync 2026                    # fetch Sprint Qualifying (add --refresh to re-fetch)
python -m app.tools.revalidate 2026 2025 --budget 400    # re-check against Jolpica (add --laps for lap timing)
python tests/check_data_integrity.py
python -m app.tools.data_manifest --check
```

Never edit files under `data/cache/` by hand. If a source is wrong, record the correction in the curated layer (`app/tools/f1_history.py`) instead, so the cached data stays an exact copy of its source.
