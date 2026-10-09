# Public beta readiness

SimGent is an open-source educational and portfolio project, currently in public beta. Passing checks demonstrates the behaviors those checks cover; it does not certify all historical data, security, performance, or availability. AI assistance is part of the development process; quality is assessed through reproducible behavior and review.

## Reproducible setup and accurate claims

Install Python dependencies with hashes, use `npm ci`, and install Chromium with `npx playwright install chromium`. Run `npm test` from an activated Python environment. The runner starts and stops its own localhost server and uses temporary private runtime storage. Port 8080 must be available. Data integration tests may contact upstream APIs; this command is not an entirely offline suite. Full CI runs Python 3.14.8 and Node 26.11.1 with npm 12.2.0 and the browser suites on Linux.

Each deployer’s individual configuration, account terms and usage determine costs. SimGent offers no zero-billing guarantee. Scale-to-zero and local model fallback reduce some costs. Neither promises zero billing or uninterrupted service. See the README for provider and Google Cloud pricing references. The hosted demo currently uses the deterministic local engine.

## Remaining work and acceptance criteria

| Area | Next change | Evidence required before claiming completion |
| --- | --- | --- |
| Frontend maintainability | Extract CSS and JavaScript from the large HTML document, then separate replay, chat, simulator and state code in small reviewed changes. | Existing replay, mobile, retirement, starting-grid and chat tests pass; offline source verification resolves extracted assets; visual review confirms the cockpit still behaves correctly. |
| Public traffic capacity | Exercise simultaneous replay loads and chat requests in a staging service; document the intended concurrency and latency targets first. | Recorded load results, error rates and resource usage at those targets, including cold starts. |
| Monitoring and recovery | Add actionable error/latency alerts and document service restoration after the budget shutdown. | A staged alert and recovery drill with verified ownership and instructions. |
| Durable private state | Decide whether feedback should survive revisions; if so, move it to access-controlled durable storage with retention and deletion rules. | Restart/redeploy tests confirm persistence and denied public access; no user feedback enters Git or build artifacts. |
| Independent review | Have another maintainer review changes through protected-main PRs. | Required approvals and checks pass; significant security boundaries receive independent review. |
| Historical data coverage | Record upstream provenance and distinguish cached, verified and synthesized data. | Reproducible cross-era accuracy checks and clear limitations for unsupported or approximate telemetry. |

This list is a work plan, not a claim that these operational checks have already passed. GitHub's support cleanup of historical cached content is tracked separately from normal clone hygiene.
