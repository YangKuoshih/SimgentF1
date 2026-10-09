# Building and validating SimGent

SimGent is a Python web application with Node-based browser tests. Running the application does not require Node. Deploy the source checkout as a container; installing a Python wheel is not a supported deployment method.

## Runtime selection

Use Python 3.14.8 for development and deployment parity, pinned in `.python-version` and the container base. `uv python install 3.14.8` followed by `uv venv --seed --python 3.14.8 .venv` selects it explicitly; the system `python3` command may still select an older installation. The supported minimum is 3.11; focused offline security, memory and strategy tests run across 3.11–3.13, while the full integration and browser suite runs on 3.14.8. These checks do not establish every feature on every platform. The dependency-metadata check requires Python 3.11 or newer. The isolated Atheris fuzz job and the budget Cloud Function retain Python 3.11 for their tool/provider compatibility; they are separate from the web application runtime.

Use Node 26.11.1 (stable Current) and npm 12.2.0 for tooling (`nvm install` / `nvm use` reads `.nvmrc` if nvm is installed). Node 24.21.0 is the LTS alternative. CI explicitly installs npm 12.2.0; `packageManager` metadata alone does not switch an installed npm version. Supported tool versions are declared in `package.json`. npm launches Python without shell expansion, using `PYTHON` if specified, then the active virtual environment or `.venv`, then the platform default. This avoids requiring `python3` on Windows. Headed browser tests use a command-line flag rather than shell-specific environment assignment.

## Dependencies

Install Python dependencies with `python -m pip install --require-hashes -r requirements.txt`, then run `python -m pip check`. Runtime requirements in `pyproject.toml` and the compatibility input `requirements.in` must match; CI checks for drift. Regenerate the universal hash lock with the documented uv command in CONTRIBUTING.md. Review dependency changes and run the dependency audits before merging. A lockfile is not a guarantee that dependencies are vulnerability-free.

Install Node tooling with `npm ci`. Playwright is pinned to the version already recorded in the lockfile. Install Chromium with `npx playwright install chromium` (Linux CI uses `--with-deps`). Run `npm test` for the combined suite, or `npm run test:browser` for the four browser suites with an automatically managed server. Direct individual browser commands require a running app.

## Container

`docker build -t f1-simgent .` installs hash-locked dependencies on the existing digest-pinned Python 3.14.8 base. The process runs as UID/GID 10001 and receives termination signals directly through `exec`. The application directory belongs to this user because the existing upstream cache and private runtime storage require write access. Source files are not yet on a read-only filesystem.

CI builds the image, checks the configured user, starts it, checks HTTP health, verifies private memory initialization and cache write permissions, and removes the smoke-test container. Production private runtime files remain ephemeral unless a separate durable store is configured. The image build does not replace vulnerability scanning or independent review.
