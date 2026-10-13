# Changelog

## Unreleased

## v1.6.0 — 2026-10-13

### Added
- **Answer gate** (`app/agent/gate.py`): every answer is checked before it goes out. The checks are deterministic and in-process, with no model and no network.
  - It confirms the answer is about the race named and the race on screen.
  - It checks facts (winner, pole, fastest lap, laps, circuit, champion) against F1DB and replaces wrong ones.
  - It removes lap times that aren't in the data.
  - It asks a clarifying question, with buttons, when a question fits two races, two drivers or two intents. Typed replies such as "the second one" also work.
  - Live score at `/api/agent/gate`; `SIMGENT_GATE=off` turns it off.
- **Comebacks**: "In what race did Antonelli win from the back of the grid?", "biggest comeback win ever", "who gained the most places?".
  - Starting grid against finish for every race since 1950, from F1DB, for a driver, a season, one race or all time.
  - 1950s shared drives are left out; F1DB gives them no grid slot of their own.
- **Every race drawn on the layout actually raced, 1950–2026** (`data/circuit-layouts.json`, `scripts/build_circuit_layouts.py`).
  - F1DB layouts (CC BY 4.0) and f1-circuits-svg outlines (MIT), with the right drawing for each season.
  - OpenStreetMap outlines (ODbL) for Jerez, Fuji, Korea and Reims-Gueux 1950–51.
  - Official turn counts, plus the fastest lap for every year.
  - No more generic ovals or empty Circuit Intel cards.
- **Agent evals.**
  - Golden set (`tests/eval_golden.py`): about 5,900 questions over every Grand Prix since 1950, graded against F1DB, a different source from the agent's Jolpica data. Result: 0 wrong, 0 invented lap times.
  - promptfoo behaviour suite run in CI.
  - promptfoo playground (`npm run playground`): your own questions plus random ones from every season, each checked against F1DB.
- Career totals (wins, poles, podiums, titles) from F1DB for every driver.
- Data credits and licenses in the About box, `NOTICE.md` and the README.

### Changed
- **Nothing shown beyond what the data supports.**
  - The corner "telemetry" modal is now a modelled speed profile labelled "not car telemetry".
  - "LIVE TIMING FEED" is now "LAP TIMING DATA" or "RECONSTRUCTED FROM RESULTS".
  - Invented circuit defaults removed (lap record, throttle %, tyre stress, pit loss).
  - Practice questions say practice isn't in the data, instead of using a template.
  - Tyre compounds are no longer guessed from the stop count.
- With no race on screen, the agent uses the latest completed race (it used a fixed round 15).
- Hourly light data sync on race weekends.

### Fixed
- **Wrong race.**
  - A stored 2026 Bahrain answer appeared on the Singapore replay for "How did VER win this race?". Stored answers now answer only for their own race, and go through the answer gate.
  - "In what race did…" questions fell back to the race on screen.
- **Wrong person.**
  - Graham Hill career questions answered with Damon Hill.
  - Winners were presented as pole sitter when qualifying data was missing.
  - The winner's best lap was presented as the race's fastest lap.
  - "1976 United States GP" got the US GP West.
- **Wrong or one-sided content.**
  - Every safety-car answer mentioned Baku.
  - When results were incomplete, the winner alone was presented as the whole race.
- **Grid questions.** "Who started from the pit lane?" now says who did, or that nobody did. "Who started last?" is answered.
- **Circuits.**
  - Marina Bay and Paul Ricard animated backwards.
  - The Indy 500 oval ran in the wrong direction.
  - Silverstone's start line was misplaced before 2011.
  - Estoril, Indianapolis and Jacarepaguá showed other layouts of those circuits.
  - Montreal 1991–93 showed the 1988–90 drawing.
- Card text was double-escaped ("&amp;").
- 1949 and 2027 questions got the 2026 race on screen.

## v1.5.0 — 2026-10-11

### Added
- **Semantic intent router** (`app/agent/router.py`, `agent/intents.toml`): 22 kinds of question with example phrasings, matched with potion-base-8M static embeddings (numpy only, pinned and SHA-256 checked, about 0.1 ms per question) blended with BM25; names and years are masked so it learns the shape of a question. When it is confident the engine misread a question, the engine is asked again in that intent's canonical phrasing; definitive answers ("no race result yet", "no sprint that weekend") are never replaced. Held-out paraphrases answered correctly end to end: 63% → 75%, none broken (CI gate). See `docs/AGENT_ARCHITECTURE.md`.
- **Content out of code**: race stories, eras, retirement write-ups and the 2026 regulations live in `content/*.md` with sources; answers from them show "Source: content/…" linked to the file. Facts in content are checked against the race data (the first check corrected Schumacher's Spa 1998 lap count to 25).
- **Sprint and Qualifying from OpenF1** until Jolpica publishes, in Jolpica's format; the sprint grid comes from OpenF1's position feed (identical to Jolpica's on every 2026 sprint).
- **Hands-off data pipeline**: verified data is published to `main` by a deploy key limited to the `main` branch and to `data/cache/`, then deployed; deploys also run on every merge to `main`.
- **Race weekends in progress** open on their newest session; sessions that ended without results show "results pending".
- Session picker on phones; weekend summaries.

### Changed
- **Qualifying replays are a knockout**: each segment's cars run one flying lap at their real time, knocked-out drivers leave the track (OUT Q1 / OUT Q2), and the timing tower builds live instead of showing the final order. Seasons before 2006 replay as one session.
- **"Who won this race?" follows the replay**: P1 on qualifying screens, the sprint winner on the sprint; naming the Grand Prix still means the Grand Prix.
- The Pit Wall Agent answers qualifying segment questions (knocked out in Q1, made Q3, fastest in Q2, a driver's time in a segment).

### Fixed
- Questions about a race that has not run no longer get another race's result (the season's first race was used).
- "Who started P3" returned Jackie Stewart's career profile ("started" fuzzy-matched "Stewart").
- The whole starting grid had no answer; free practice questions returned race results.
- Estimated qualifying (grid order when the classification is missing) no longer quotes made-up lap times.
- The 2026 Singapore sprint grid had two cars on P1.
- Unpublished results were re-requested from Jolpica on every page load and chat message.
- Pages are revalidated on every visit, so deploys show without a hard refresh.
- Driver exit questions in qualifying and sprint, readable over-long question errors, no made-up sprints, and three answers found by a 373-question live browser run.

## v1.4.0 — 2026-10-09

### Security
- The live service runs as a dedicated identity with no Google Cloud roles (it only reads public APIs), instead of the default compute account with project Editor.
- Rate limiting keys on an IP the caller can't forge: the rightmost X-Forwarded-For hop added by Google's front end, or Cloudflare's CF-Connecting-IP when the request comes from a Cloudflare edge. The test-only `X-Test-Client` header is honored only when `SIMGENT_TRUST_TEST_CLIENT_HEADER=1` (CI).
- Security headers on every response: Content-Security-Policy (no scripts from other sites except Tailwind's CDN, no requests to other origins except Cloudflare Web Analytics, no framing or plugins), nosniff, X-Frame-Options, Referrer-Policy, Permissions-Policy, HSTS.
- Strategy simulator inputs are bounded (iterations ≤ 1000, laps ≤ 200, small driver payloads) and feedback submissions are rate-limited.
- The Pit Wall Agent's race-label parsing is linear on hostile input (CodeQL `py/polynomial-redos`), and `/api/chat` rejects a `context` over 4 KB or more than 50 history turns with 422.
- GitHub Actions: `actions/checkout` no longer leaves the token on the runner (`persist-credentials: false`) except in the data sync job, which pushes; Dependabot waits 7 days after a release before proposing it.
- `SECURITY.md` links GitHub private vulnerability reporting directly and describes how reports are handled.
- The package metadata no longer lists a personal email address.

### Added
- OpenSSF Scorecard workflow (weekly and on `main`), with results in code scanning and a README badge.
- zizmor workflow that audits the GitHub Actions workflows on every pull request; accepted exceptions are documented in `.github/zizmor.yml`.

### Changed
- Data license stated clearly: the MIT License covers the code only. Cached Jolpica-F1 and OpenF1 data is CC BY-NC-SA 4.0 (attribution, non-commercial, share-alike); see `NOTICE.md` and `data/cache/LICENSE.md`. The README no longer calls the data non-copyrightable, and the license badge shows both.
- The project is called SimGent throughout: the agent's self-introduction, system prompts, docs, CI name and logs no longer say "F1 Simgent".
- Wording: "team-inspired colors" instead of "official team liveries", and answer cards no longer say "Official" (e.g. "Podium & Race Classification", "Fastest Lap"). The trademark notice drops an incorrect statute citation.

## v1.3.0 — 2026-10-09

Moved to this repository with a fresh history (October 2026).

### Added
- The Pit Wall Agent answers for the session on screen. A question that doesn't name a race or session ("Who won?", "How did Hamilton do?", "Who was P3?") is answered from the Race, Sprint, Qualifying or Sprint Qualifying being viewed; anything the question names (another race, "the sprint", "the grand prix") overrides it. Qualifying "winner" questions name the pole-sitter and note that qualifying has no winner (`app/tools/session_scope.py`).
- Race-data answers end with the race and session they are based on (e.g. *2026 Miami Grand Prix · Sprint Qualifying*), and say so when a question had to be answered from the Grand Prix instead.
- `tests/eval_session_scope.py`: every cached sprint weekend, each session, checked against the source files (runs in CI and the data sync).

### Changed
- Sprint Qualifying / Sprint Shootout sessions (2023 on) now come from the free OpenF1 API (`app/tools/openf1_sync.py`, cached under `data/cache/openf1/`, CC BY-NC-SA 4.0). All 23 cached sessions match the previous data on every position, time and lap count. The scheduled sync fetches new sessions every 6 hours and the app fetches an uncached session on demand.

### Removed
- All data scraped from a third-party results website whose terms don't allow reuse, along with its cache, the scrapers and the admin `/api/verify` endpoint. Cached data now comes only from Jolpica and OpenF1.

### Fixed
- After a restart the app opens the newest finished race: the season winners list refreshes while races are recent, and the current year replaces hard-coded 2026 in the season list and latest-race lookup.
- The Pit Wall Agent answers about the race on screen, not one discussed earlier in the chat (chat turns carry the race being viewed); a driver from earlier turns is only used when the question refers back to one.
- "How did <driver> do?" answers about that driver instead of the race winner.
- Accuracy fixes from a 230-turn live multi-turn run across 1950–2026 (now 230/230): race story pages no longer take driver or pit-strategy questions; "When did <driver> retire?" at a race they didn't finish gives the race retirement; drivers in the race beat fuzzy career-name matches; the conversation's race comes from the latest question that names one (no phantom races); classified non-finishers and disqualifications are worded correctly.
- CodeQL runs as a workflow so pull requests (including Dependabot's) get the required checks.

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
