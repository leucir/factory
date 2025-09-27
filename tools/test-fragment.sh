#!/usr/bin/env bash
# Render, build, and optionally smoke-test a single fragment manifest.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

MANIFEST=""
MANIFEST_ID="core_smoke"
MANIFEST_STORE="control_plane/data/manifest.json"
OUTPUT_OVERRIDE=""
IMAGE_TAG="llm-factory:fragment-smoke"
RUN_CMD="python3 --version"
SKIP_RUN=0

usage() {
  cat <<'USAGE'
Usage: tools/test-fragment.sh [options]

Options:
  --manifest PATH     Path to a standalone manifest (overrides manifest ID)
  --manifest-id ID    Manifest identifier inside the store (default: core_smoke)
  --manifest-store PATH  Override manifest store location (default: control_plane/data/manifest.json)
  --output PATH       Override the rendered Dockerfile location
  --tag NAME          Image tag to build (default: llm-factory:fragment-smoke)
  --cmd COMMAND       Command to run inside the container for a quick smoke test (default: python3 --version)
  --skip-run          Build the image but skip running the smoke command
  -h, --help          Show this help message
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --manifest)
      [[ $# -ge 2 ]] || { echo "Missing value for --manifest" >&2; exit 1; }
      MANIFEST="$2"
      shift 2
      ;;
    --manifest-id)
      [[ $# -ge 2 ]] || { echo "Missing value for --manifest-id" >&2; exit 1; }
      MANIFEST_ID="$2"
      shift 2
      ;;
    --manifest-store)
      [[ $# -ge 2 ]] || { echo "Missing value for --manifest-store" >&2; exit 1; }
      MANIFEST_STORE="$2"
      shift 2
      ;;
    --output)
      [[ $# -ge 2 ]] || { echo "Missing value for --output" >&2; exit 1; }
      OUTPUT_OVERRIDE="$2"
      shift 2
      ;;
    --tag)
      [[ $# -ge 2 ]] || { echo "Missing value for --tag" >&2; exit 1; }
      IMAGE_TAG="$2"
      shift 2
      ;;
    --cmd)
      [[ $# -ge 2 ]] || { echo "Missing value for --cmd" >&2; exit 1; }
      RUN_CMD="$2"
      shift 2
      ;;
    --skip-run)
      SKIP_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$MANIFEST" ]]; then
  if [[ "$MANIFEST_STORE" != /* ]]; then
    STORE_PATH="$ROOT/$MANIFEST_STORE"
  else
    STORE_PATH="$MANIFEST_STORE"
  fi
  if [[ ! -f "$STORE_PATH" ]]; then
    echo "Manifest store not found at $STORE_PATH" >&2
    exit 1
  fi
else
  if [[ "$MANIFEST_STORE" != /* ]]; then
    STORE_PATH="$ROOT/$MANIFEST_STORE"
  else
    STORE_PATH="$MANIFEST_STORE"
  fi
fi

get_manifest_output() {
  python3 - "$ROOT" "$STORE_PATH" "$MANIFEST_ID" "$MANIFEST" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1])
store_path = Path(sys.argv[2])
manifest_id = sys.argv[3]
manifest_path_arg = sys.argv[4]

sys.path.insert(0, str(root / "tools"))

from manifest_utils import load_manifest  # type: ignore

manifest_path = Path(manifest_path_arg) if manifest_path_arg else None
manifest = load_manifest(manifest_path, manifest_id, store_path)
print(manifest.get("output", "dockerfiles/Dockerfile.rendered"))
PY
}

RENDER_OUTPUT="$OUTPUT_OVERRIDE"
if [[ -z "$RENDER_OUTPUT" ]]; then
  RENDER_OUTPUT="$(get_manifest_output)"
fi

if [[ "$RENDER_OUTPUT" != /* ]]; then
  RENDER_PATH="$ROOT/$RENDER_OUTPUT"
else
  RENDER_PATH="$RENDER_OUTPUT"
fi

STITCH_CMD=(python3 "$ROOT/tools/stitch.py")
if [[ -n "$MANIFEST" ]]; then
  if [[ "$MANIFEST" != /* ]]; then
    MANIFEST_PATH="$ROOT/$MANIFEST"
  else
    MANIFEST_PATH="$MANIFEST"
  fi
  if [[ ! -f "$MANIFEST_PATH" ]]; then
    echo "Manifest not found at $MANIFEST_PATH" >&2
    exit 1
  fi
  STITCH_CMD+=(--manifest "$MANIFEST_PATH")
else
  STITCH_CMD+=(--manifest-id "$MANIFEST_ID" --manifest-store "$STORE_PATH")
fi
if [[ -n "$OUTPUT_OVERRIDE" ]]; then
  STITCH_CMD+=(--output "$OUTPUT_OVERRIDE")
fi

if [[ -n "$MANIFEST" ]]; then
  echo "[TEST-FRAGMENT] Rendering manifest $MANIFEST_PATH"
else
  echo "[TEST-FRAGMENT] Rendering manifest '${MANIFEST_ID}' from ${STORE_PATH}"
fi
"${STITCH_CMD[@]}"

echo "[TEST-FRAGMENT] Building $IMAGE_TAG via $RENDER_PATH"
docker build -f "$RENDER_PATH" -t "$IMAGE_TAG" "$ROOT"

if [[ "$SKIP_RUN" -eq 0 ]]; then
  echo "[TEST-FRAGMENT] Running smoke command: $RUN_CMD"
  docker run --rm "$IMAGE_TAG" bash -lc "$RUN_CMD"
fi

echo "[TEST-FRAGMENT] Done"
