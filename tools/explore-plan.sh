#!/usr/bin/env bash
# Wrapper to run the explore-plan CLI via Bash for consistency with other tooling.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$ROOT/tools/explore-plan.py"
PYTHON_BIN="${PYTHON:-python3}"

if [[ ! -f "$SCRIPT" ]]; then
  echo "explore-plan script not found at $SCRIPT" >&2
  exit 1
fi

exec "$PYTHON_BIN" "$SCRIPT" "$@"
