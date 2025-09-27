#!/usr/bin/env bash
# Cleanup script: purge Docker images and compatibility artefacts.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./tools/cleanup.sh [--force]

Deletes all Docker images on this host and clears compatibility artefacts under
control_plane/data/compatibility/. Requires --force to actually execute.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ "${1:-}" != "--force" ]]; then
  echo "[cleanup] Dry run (no changes applied). Use --force to execute." >&2
  usage
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"

require() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[cleanup] Error: $1 is not installed or not on PATH" >&2
    exit 1
  fi
}

echo "[cleanup] Starting destructive cleanup..."

require docker

echo "[cleanup] Removing all Docker images via docker image prune -af"
docker image prune -af >/dev/null || true

COMPAT_ROOT="${ROOT_DIR}/control_plane/data/compatibility"

if [[ -d "${COMPAT_ROOT}" ]]; then
  echo "[cleanup] Clearing compatibility artefacts under ${COMPAT_ROOT}"
  find "${COMPAT_ROOT}" -mindepth 1 -maxdepth 1 -type d | while read -r subdir; do
    find "${subdir}" -mindepth 1 -delete || true
    mkdir -p "${subdir}"
  done
else
  echo "[cleanup] Warning: ${COMPAT_ROOT} missing, skipping"
fi

echo "[cleanup] Cleanup complete."
