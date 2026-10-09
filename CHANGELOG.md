# Changelog

## Unreleased

### Added
- The Pit Wall Agent answers for the session on screen. A question that doesn't name a race or session ("Who won?", "How did Hamilton do?", "Who was P3?") is answered from the Race, Sprint, Qualifying or Sprint Qualifying being viewed; anything the question names (another race, "the sprint", "the grand prix") overrides it. Qualifying "winner" questions name the pole-sitter and note that qualifying has no winner (`app/tools/session_scope.py`).
- Race-data answers end with the race and session they are based on (e.g. *2026 Miami Grand Prix · Sprint Qualifying*), and say so when a question had to be answered from the Grand Prix instead.
- `tests/eval_session_scope.py`: every cached sprint weekend, each session, checked against the source files (runs in CI and the data sync).

### Changed
- Sprint Qualifying / Sprint Shootout sessions (2023 on) now come from the free OpenF1 API (`app/tools/openf1_sync.py`, cached under `data/cache/openf1/`, CC BY-NC-SA 4.0). All 23 cached sessions match the previous data on every position, time and lap count. The scheduled sync fetches new sessions every 6 hours and the app fetches an uncached session on demand.

### Removed
- All data and tooling sourced from the official F1 results website, including its cache, the scrapers that fetched it and the admin `/api/verify` endpoint. Cached data now comes only from Jolpica and OpenF1.

## v1.2.0

### Added
- Sprint data for every sprint weekend (2021–2026): sprint results and official sprint grids from Jolpica, and Sprint Qualifying / Sprint Shootout sessions (2023–2026). The Pit Wall Agent answers sprint, sprint-grid and sprint-qualifying questions.
- Verified-data pipeline (see `docs/DATA_PIPELINE.md`):
  - `data/cache/MANIFEST.json` records the source URL, fetch time and SHA-256 of every cached file (`app/tools/data_manifest.py`).
  - `app/tools/revalidate.py` re-checks cached seasons against Jolpica and replaces files that drifted.
  - `tests/check_data_integrity.py` gate: standings vs results, real grids, real lap timing, pit stops vs classification, manifest.
- Agent evals across all eras (`tests/eval_cross_era.py`) and multi-turn conversations (`tests/eval_multi_turn.py`), run in CI.

### Changed
- Scheduled sync runs every 6 hours (races from the last 21 days are re-fetched), re-checks all seasons weekly, and only commits data that passes the integrity gate and evals.

### Fixed
- 2026 data: qualifying rounds 2–15 (driver ID, Q2/Q3 fields), round 14 starting grid, driver standings, now match Jolpica exactly.
- Integrity checks compare driver standings against race results instead of a hard-coded total.
- Multi-turn follow-ups, standings and career totals, curated history, and the round 16 Bahrain GP (held at Sepang) answers.

## v1.1.0

### Added
- Pit Wall Agent: a "Brief & control log" toggle above the session brief collapses the brief and race control log, giving the chat the full panel height. The choice is remembered in each browser.

### Fixed
- Pit Wall Agent header: the brief toggle is icon-only, so the panel collapse arrow stays visible at every width.

## v1.0.0

- Initial public release: F1 telemetry and 2D race-replay cockpit, Pit Wall Agent, and the Monte Carlo strategy simulator (1950–2026).
