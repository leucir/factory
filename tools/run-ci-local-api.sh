#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "${ROOT_DIR}"

require() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Error: $1 is not installed or not on PATH" >&2
    exit 1
  fi
}

require python3
require docker
require curl

if ! python3 -c "import uvicorn" >/dev/null 2>&1; then
  echo "[API] Installing Python dependencies for control plane"
  python3 -m pip install --quiet uvicorn fastapi
fi

PRODUCT_ID="${1:-llm_factory}"
PIPELINE_ID="${2:-layered_build_pipeline}"

BUILD_ID="${PRODUCT_ID}-$(date +%Y%m%dT%H%M%S)"
API_HOST="127.0.0.1"
API_PORT="8081"
BASE_URL="http://${API_HOST}:${API_PORT}"
MANIFEST_ID=""
MANIFEST_STORE="control_plane/data/manifest.json"
IMAGE_TAG=""
BUILD_PLATFORM=""
EVIDENCE_DIR="control_plane/data/compatibility/evidence"
SBOM_DIR="control_plane/data/compatibility/sbom"
ERROR_RECORDS_DIR="control_plane/data/compatibility/records"
mkdir -p "${EVIDENCE_DIR}" "${SBOM_DIR}"
EVIDENCE_FILE="${EVIDENCE_DIR}/${BUILD_ID}.log"
SBOM_FILE=""
touch "${EVIDENCE_FILE}"

echo "# Build ID: ${BUILD_ID}" >> "${EVIDENCE_FILE}"

echo_log() {
  echo "$1"
  echo "$1" >> "${EVIDENCE_FILE}"
}

write_error_report() {
  local reason="$1"
  mkdir -p "${ERROR_RECORDS_DIR}"
  local error_file="${ERROR_RECORDS_DIR}/error-${BUILD_ID}.json"
  ERROR_FILE="${error_file}" \
  ERROR_REASON="${reason}" \
  BUILD_ID="${BUILD_ID}" \
  PRODUCT_ID="${PRODUCT_ID}" \
  PIPELINE_ID="${PIPELINE_ID}" \
  IMAGE_TAG="${IMAGE_TAG}" \
  MANIFEST_ID_VALUE="${MANIFEST_ID}" \
  MANIFEST_STORE_VALUE="${MANIFEST_STORE}" \
  EVIDENCE_FILE="${EVIDENCE_FILE}" \
  python3 - <<'PY'
import datetime as dt
import json
import os
from pathlib import Path

evidence_path = Path(os.environ["EVIDENCE_FILE"])
lines = []
if evidence_path.exists():
    try:
        lines = evidence_path.read_text().splitlines()
    except Exception:
        lines = []

excerpt = lines[-40:]
timestamp = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
payload = {
    "type": "build_error",
    "build_id": os.environ.get("BUILD_ID", ""),
    "product_id": os.environ.get("PRODUCT_ID", ""),
    "pipeline_id": os.environ.get("PIPELINE_ID", ""),
    "image_tag": os.environ.get("IMAGE_TAG", ""),
    "manifest_id": os.environ.get("MANIFEST_ID_VALUE", ""),
    "manifest_store": os.environ.get("MANIFEST_STORE_VALUE", ""),
    "notes": os.environ.get("ERROR_REASON", ""),
    "timestamp": timestamp,
    "evidence_path": os.environ.get("EVIDENCE_FILE", ""),
    "log_excerpt": excerpt,
}

Path(os.environ["ERROR_FILE"]).write_text(json.dumps(payload, indent=2) + "\n")
PY
}

record_compatibility() {
  local status="$1"
  local notes="$2"
  local cmd=(
    python3 tools/write-compatibility-record.py
    --manifest-id "${MANIFEST_ID}"
    --manifest-store "${MANIFEST_STORE}"
    --image "${IMAGE_TAG}"
    --status "${status}"
    --notes "${notes}"
    --build-id "${BUILD_ID}"
    --evidence-path "${EVIDENCE_FILE}"
  )
  if [[ -n "${SBOM_FILE}" && -f "${SBOM_FILE}" ]]; then
    cmd+=(--sbom-path "${SBOM_FILE}")
  fi
  "${cmd[@]}"
}

cleanup() {
  if [[ -n "${API_PID:-}" ]]; then
    kill "${API_PID}" >/dev/null 2>&1 || true
    wait "${API_PID}" 2>/dev/null || true
  fi
}

trap cleanup EXIT
trap 'trap - ERR; echo "status: fail" >> "${EVIDENCE_FILE}"; write_error_report "run-ci-local-api failure"; record_compatibility fail "run-ci-local-api failure"' ERR

echo_log "[API] Starting control plane server"
python3 -m uvicorn main:app \
  --app-dir control_plane/src \
  --host "${API_HOST}" \
  --port "${API_PORT}" \
  --log-level warning >> "${EVIDENCE_FILE}" 2>&1 &
API_PID=$!

# Wait for server
for _ in {1..30}; do
  if curl -sf "${BASE_URL}/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

if ! curl -sf "${BASE_URL}/health" >/dev/null 2>&1; then
  echo_log "Error: control plane API failed to start"
  exit 1
fi

echo_log "[API] Fetching product and pipeline metadata"
metadata=$(BASE_URL="${BASE_URL}" PRODUCT_ID="${PRODUCT_ID}" PIPELINE_ID="${PIPELINE_ID}" python3 <<'PY'
import json
import os
import sys
import urllib.request

base = os.environ["BASE_URL"]
product_id = os.environ["PRODUCT_ID"]
pipeline_id = os.environ["PIPELINE_ID"]

product_url = f"{base}/products/{product_id}"
pipeline_url = f"{base}/pipelines/{pipeline_id}"

try:
    with urllib.request.urlopen(product_url) as resp:
        product = json.load(resp)
except Exception:
    print("__PRODUCT_ERROR__")
    sys.exit(0)

try:
    with urllib.request.urlopen(pipeline_url) as resp:
        pipeline = json.load(resp)
except Exception:
    print("__PIPELINE_ERROR__")
    sys.exit(0)

metadata = product.get("metadata", {})
result = {
    "manifest_id": metadata.get("manifest_id", ""),
    "manifest_store": metadata.get("manifest_store", "control_plane/data/manifest.json"),
    "rendered": metadata.get("rendered_dockerfile", "dockerfiles/Dockerfile.rendered"),
    "stitch_script": metadata.get("stitch_script", "tools/stitch.py"),
    "image_name": product.get("docker_image_name", "llm-factory"),
    "image_tag": product.get("docker_tag", "dev"),
    "test_runner": pipeline["metadata"].get("test_runner", "tools/test-runner.sh"),
    "build_tool": pipeline["metadata"].get("build_tool", "docker build"),
    "build_platform": metadata.get("build_platform", ""),
}

print(json.dumps(result))
PY
)

if [[ "${metadata}" == "__PRODUCT_ERROR__" ]]; then
  echo_log "Error: product '${PRODUCT_ID}' not found via API"
  write_error_report "Product not found via API"
  exit 1
fi
if [[ "${metadata}" == "__PIPELINE_ERROR__" ]]; then
  echo_log "Error: pipeline '${PIPELINE_ID}' not found via API"
  write_error_report "Pipeline not found via API"
  exit 1
fi

echo "${metadata}" >> "${EVIDENCE_FILE}"

MANIFEST_ID=$(METADATA="${metadata}" python3 - <<'PY'
import json
import os
info = json.loads(os.environ["METADATA"])
print(info.get("manifest_id", ""))
PY
)

if [[ -z "${MANIFEST_ID}" ]]; then
  echo_log "Error: manifest id missing in metadata"
  write_error_report "Manifest id missing"
  exit 1
fi

MANIFEST_STORE=$(METADATA="${metadata}" python3 - <<'PY'
import json
import os
info = json.loads(os.environ["METADATA"])
print(info.get("manifest_store", "control_plane/data/manifest.json"))
PY
)

IMAGE_TAG=$(METADATA="${metadata}" python3 - <<'PY'
import json
import os
info = json.loads(os.environ["METADATA"])
image_name = info.get('image_name', 'llm-factory')
image_tag = info.get('image_tag', 'dev')
print(f"{image_name}:{image_tag}-api-local")
PY
)

BUILD_PLATFORM=$(METADATA="${metadata}" python3 - <<'PY'
import json
import os
info = json.loads(os.environ["METADATA"])
print(info.get('build_platform', ''))
PY
)

echo_log "[API] Rendering Dockerfile via manifest '${MANIFEST_ID}'"
STITCH_SCRIPT=$(METADATA="${metadata}" python3 - <<'PY'
import json
import os
info = json.loads(os.environ["METADATA"])
print(info.get("stitch_script", "tools/stitch.py"))
PY
)
python3 "${STITCH_SCRIPT}" --manifest-id "${MANIFEST_ID}" --manifest-store "${MANIFEST_STORE}" 2>&1 | tee -a "${EVIDENCE_FILE}"

echo_log "[API] Building Docker image ${IMAGE_TAG}"
build_tool=$(METADATA="${metadata}" python3 - <<'PY'
import json
import os
info = json.loads(os.environ["METADATA"])
print(info.get("build_tool", "docker build"))
PY
)

renderer=$(METADATA="${metadata}" python3 - <<'PY'
import json
import os
info = json.loads(os.environ["METADATA"])
print(info.get("rendered", "dockerfiles/Dockerfile.rendered"))
PY
)

if [[ "${build_tool}" == "docker build" ]]; then
  if [[ -n "${BUILD_PLATFORM}" ]]; then
    docker build --platform "${BUILD_PLATFORM}" -f "${renderer}" -t "${IMAGE_TAG}" . 2>&1 | tee -a "${EVIDENCE_FILE}"
  else
    docker build -f "${renderer}" -t "${IMAGE_TAG}" . 2>&1 | tee -a "${EVIDENCE_FILE}"
  fi
else
  echo_log "Warning: unsupported build tool '${build_tool}', defaulting to docker build"
  if [[ -n "${BUILD_PLATFORM}" ]]; then
    docker build --platform "${BUILD_PLATFORM}" -f "${renderer}" -t "${IMAGE_TAG}" . 2>&1 | tee -a "${EVIDENCE_FILE}"
  else
    docker build -f "${renderer}" -t "${IMAGE_TAG}" . 2>&1 | tee -a "${EVIDENCE_FILE}"
  fi
fi

if command -v syft >/dev/null 2>&1; then
  SBOM_FILE="${SBOM_DIR}/${BUILD_ID}.json"
  echo_log "[API] Generating SBOM at ${SBOM_FILE}"
  ./tools/generate-sbom.sh "${IMAGE_TAG}" "${SBOM_FILE}" 2>&1 | tee -a "${EVIDENCE_FILE}"
else
  echo_log "[API] Skipping SBOM generation (syft not installed)"
fi

TEST_RUNNER=$(METADATA="${metadata}" python3 - <<'PY'
import json
import os
info = json.loads(os.environ["METADATA"])
print(info.get("test_runner", "tools/test-runner.sh"))
PY
)

echo_log "[API] Running smoke tests via ${TEST_RUNNER}"
if [[ -n "${BUILD_PLATFORM}" ]]; then
  DOCKER_DEFAULT_PLATFORM="${BUILD_PLATFORM}" "${TEST_RUNNER}" "${IMAGE_TAG}" 2>&1 | tee -a "${EVIDENCE_FILE}"
else
  "${TEST_RUNNER}" "${IMAGE_TAG}" 2>&1 | tee -a "${EVIDENCE_FILE}"
fi

echo_log "[API] Pipeline execution completed"
trap - ERR
record_compatibility pass "run-ci-local-api"
