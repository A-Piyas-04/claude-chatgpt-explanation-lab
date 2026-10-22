#!/usr/bin/env bash
# Run the whole test suite plus the linters and the production web build.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root/apps/api"

if [ -x .venv/Scripts/python.exe ]; then PY=.venv/Scripts/python.exe; else PY=.venv/bin/python; fi

echo "== API tests =============================================="
# Tests force demo mode and an isolated temp database, so no network
# call is made and no provider is billed.
"$PY" -m pytest -q

echo
echo "== API lint =============================================="
"$PY" -m ruff check explanationlab tests

echo
echo "== Web typecheck ========================================="
cd "$root/apps/web"
npm run typecheck

echo
echo "== Web build ============================================="
npm run build

echo
echo "All checks passed."
