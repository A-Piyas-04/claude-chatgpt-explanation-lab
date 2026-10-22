#!/usr/bin/env bash
# One-shot local setup. Safe to re-run.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

echo "ExplanationLab setup"
echo "===================="

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example."
  echo "   No API keys set, so the app will start in DEMO MODE (no spend)."
else
  echo "Using existing .env."
fi

echo
echo "[1/4] Python environment"
cd apps/api
if [ ! -d .venv ]; then
  python -m venv .venv
fi
# Windows Git Bash puts the interpreter in Scripts/, POSIX in bin/.
if [ -x .venv/Scripts/python.exe ]; then PY=.venv/Scripts/python.exe; else PY=.venv/bin/python; fi
"$PY" -m pip install --quiet --upgrade pip
"$PY" -m pip install --quiet -e ".[dev]"
echo "   Installed API dependencies."

echo
echo "[2/4] Database"
"$PY" -m alembic upgrade head
echo "   Migrations applied."

echo
echo "[3/4] Seed data"
"$PY" -m explanationlab.seed

echo
echo "[4/4] Web dependencies"
cd ../web
npm install --silent
echo "   Installed web dependencies."

cd "$root"
cat <<'MESSAGE'

Setup complete. Start the two processes in separate terminals:

  Terminal 1 (API):
    cd apps/api && ./.venv/Scripts/python.exe -m uvicorn explanationlab.main:app --reload
    (on macOS/Linux: cd apps/api && ./.venv/bin/python -m uvicorn explanationlab.main:app --reload)

  Terminal 2 (web):
    cd apps/web && npm run dev

Then open http://localhost:3000

If port 3000 is taken, run the web app on another port:
    cd apps/web && PORT=3100 npm run dev

To run real experiments, add OPENAI_API_KEY and/or ANTHROPIC_API_KEY to .env
and restart the API. Until then every generated explanation is a local fixture,
flagged SYNTHETIC, and costs nothing.
MESSAGE
