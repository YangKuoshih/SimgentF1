# Security policy

## Reporting a vulnerability

Use GitHub's private vulnerability reporting option on the repository Security tab
if available. Otherwise contact the maintainer privately using the contact listed
in `pyproject.toml`. Do not open a public issue containing credentials, conversation
records, personal data, or an exploit against the live service.

Include affected versions, reproduction steps using synthetic data, and impact.
The current main branch is the maintenance target; no response-time guarantee is offered.

## Operator configuration

`/api/memory`, `/api/memory/review`, `/api/eval`, and `/api/eval/remediate` require `Authorization: Bearer <token>`. Set
`SIMGENT_ADMIN_TOKEN` through the process environment or a hosting secret manager.
Without a token configured these routes return 503; missing or invalid credentials
return 401. Never embed the token in browser code, URLs, logs, or tracked files.
Serve the application over HTTPS.

`/api/memory/stats` exposes only aggregate counts and curated public seed examples.
Public feedback submission queues records for authenticated review; it does not
change shared memory automatically.

## Runtime data

Curated seeds live in `data/seed/agent_memory.json`. Feedback and learned memory
live under `SIMGENT_RUNTIME_DIR` (default `data/runtime/`), excluded from Git,
Cloud uploads, and Docker builds. Use a private writable directory with appropriate
filesystem permissions. Cloud Run container storage is ephemeral and instance-local;
this file-based backend is not durable or coordinated across instances. Use a private
durable backend before relying on long-term retention or multiple instances.

In October 2026 the project moved to this repository with a fresh history. The
previous repository is retired; clones or forks of it are not maintained and should
not be merged into this one. Contact the maintainer privately about any remaining
hosted copies of the old repository.

The app records submitted queries, responses, comments, and context for review.
Limit retention and collection to what your deployment needs; never submit secrets.

See [the public audit and remaining operational limits](docs/SECURITY_AUDIT.md).
