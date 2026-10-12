#!/usr/bin/env bash
# SimGent agent playground (promptfoo): your questions in tests/promptfoo/my_questions.yaml plus
# random questions from every season, checked against F1DB. Results appear in the promptfoo
# dashboard (npx promptfoo@0.124.1 view).
#
#   scripts/agent_playground.sh                 # local code, 30 random questions
#   scripts/agent_playground.sh local 100       # local code, 100 random questions
#   scripts/agent_playground.sh live            # the live site (paced, ~1 question a second)
#   scripts/agent_playground.sh both 20         # local and live side by side
#   PLAYGROUND_SEED=1760300000 scripts/agent_playground.sh   # repeat an earlier random sample
set -euo pipefail
cd "$(dirname "$0")/.."

target="${1:-local}"
export PLAYGROUND_N="${2:-30}"

# promptfoo needs Node 22.22 or newer; use one from nvm if the default is older
if ! node -e 'const [a,b]=process.versions.node.split(".").map(Number); process.exit(a>22||(a===22&&b>=22)?0:1)' 2>/dev/null; then
  for dir in "$HOME"/.nvm/versions/node/v2[2-9]*/bin "$HOME"/.nvm/versions/node/v[3-9]*/bin; do
    [ -x "$dir/node" ] && PATH="$dir:$PATH"
  done
fi

# The local provider runs SimGent in-process: it needs a Python with requirements.txt and
# requirements-eval.txt installed (e.g. the repo's .venv)
if [ -z "${PROMPTFOO_PYTHON:-}" ]; then
  if [ -x .venv/bin/python ]; then PROMPTFOO_PYTHON="$PWD/.venv/bin/python"; else PROMPTFOO_PYTHON="$(command -v python3)"; fi
fi
export PROMPTFOO_PYTHON
if [ "$target" != "live" ] && ! "$PROMPTFOO_PYTHON" -c "import fastapi, httpx" 2>/dev/null; then
  echo "Install the playground's Python packages first:"
  echo "  $PROMPTFOO_PYTHON -m pip install --require-hashes -r requirements.txt -r requirements-eval.txt"
  exit 1
fi

export PROMPTFOO_DISABLE_TELEMETRY=1 PROMPTFOO_DISABLE_UPDATE=1
case "$target" in
  local) filter="^local$"; extra=() ;;
  live)  filter="^live$";  extra=(-j 1) ;;
  both)  filter="^(local|live)$"; extra=(-j 1) ;;
  *) echo "usage: $0 [local|live|both] [random questions]"; exit 2 ;;
esac
npx --yes promptfoo@0.124.1 eval -c tests/promptfoo/playground.yaml --filter-providers "$filter" --no-cache ${extra[@]+"${extra[@]}"} || true
echo
echo "Open the results: npx promptfoo@0.124.1 view   (an open dashboard picks up new runs by itself)"
