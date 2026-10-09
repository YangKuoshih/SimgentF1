# Public repository and application audit — October 8, 2026

This is a maintainer audit with automated evidence, not a security certification
or an independent penetration test. The project is suitable for public cloning
and testing within the limitations below. AI-assisted implementation does not
replace review, operational testing, or maintainership.

## Public clone and history

Published branches and v1.0.0–v1.2.0 tags were rewritten to remove historical
feedback, learned memory, and the local workshop guide. A fresh ordinary clone
contains none of those paths in reachable history. Curated seed memory remains
public; runtime feedback and learned corrections are excluded from Git, Docker,
and Cloud uploads. Local agent/cloud configuration and generated artifacts are
excluded consistently.

Old clones and forks retain their copies. GitHub still resolves an old commit
when given its SHA; pull-request refs and cached views require server-side cleanup.
A GitHub Support sensitive-data cleanup request has been submitted. Server-side
cleanup still depends on GitHub; this report does not certify that all cached copies are erased. Re-clone and
do not merge old history into this repository. The rewrite does not erase copies
held by others. No sensitive records or original backups are included in this report.

## Six release-process improvements

| Area | Implemented control | Limit |
| --- | --- | --- |
| Main protection | Required PR/check policy in `MAIN_PROTECTION.json` | No administrator bypass; check GitHub Rules for live enforcement |
| Code review | Policy requires one approval, stale approvals dismissed, latest push reviewed, conversations resolved | The sole maintainer needs another collaborator for independent approval; historical direct commits cannot gain retrospective review |
| Release provenance | Signed source archives and signature bundles for cleaned v1.0.0–v1.2.0 tags | Signatures identify archive source and publishing workflow; Git tags are unsigned and earlier releases were not retrospectively reviewed |
| Fuzz testing | Synthetic corpus and bounded Atheris runs in Linux CI | A 60-second run is not exhaustive fuzzing |
| Dependency pinning | Hash-locked application, audit/fuzz tools, and budget-alert tool; Docker digest and Actions commit pins | Locks need reviewed maintenance and new advisories can appear |
| Advisory discrepancy | Traced to loose budget-tool dependencies resolving to Starlette 0.52.1; separate lock now resolves 1.7.0 and is included in CI audits | Main-only audits would miss this separate tool |

## Runtime upgrade

The application environment, full CI, data-sync job and Docker base target Python 3.14.8. Node tooling targets stable Current 26.11.1 and npm 12.2.0; Node 24.21.0 is the LTS alternative. The supported Python minimum is now 3.11. Atheris fuzzing and the separate budget Cloud Function retain Python 3.11 for tool/provider compatibility. Python and npm locks, the non-root image build, browser tests and static analysis are checked by the [current PR verification](https://github.com/YangKuoshih/SimgentF1/actions). Review the exact commit and check results; the version pins themselves are not evidence that an audit passed.

## Verification evidence

- Before the October 2026 move to this repository, full Python, accuracy,
  data-integrity and Playwright browser checks passed, and a Linux fuzz run
  completed 196,031 executions without a crash. Current results are on the
  [Actions page](https://github.com/YangKuoshih/SimgentF1/actions).
- Exact application and budget-tool locks each passed pip-audit with no known
  vulnerabilities. The older OSV scanner used by Scorecard also reports no findings
  after the budget-tool lock fix.
- GitHub CodeQL and Dependabot showed zero open alerts at audit time.
- All three downloaded release archives passed cryptographic signature verification.
  The v1.2.0 statement's source commit matches the cleaned tag exactly.
- Deployed public pages and curated memory statistics respond successfully;
  protected memory/admin endpoints return 503 when no admin token is configured.

## Operational limits

Runtime storage is ephemeral and instance-local on Cloud Run. In-memory rate limits
are also instance-local. Durable private storage, sustained load testing, monitoring,
and an independent security review are needed before broad production reliance.
Upstream data availability and correctness can change after these tests.

The budget-alert tool now uses documented service-level manual scaling with zero
instances rather than setting a revision's maximum to zero. Its regression tests
mock the Cloud API; they do not shut down the live service. Budget notifications
can be delayed and do not guarantee a hard spending cap. See
[Google's manual-zero shutdown documentation](https://docs.cloud.google.com/run/docs/configuring/services/manual-scaling#disable-service).
Verify deployment and operator IAM configuration separately before relying on it.
