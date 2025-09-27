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

PRODUCT_ID="${1:-llm_factory}"
MANIFEST_STORE="control_plane/data/manifest.json"

read_manifest_metadata() {
  python3 - "$1" <<'PY'
import json
import shlex
import sys
from pathlib import Path

product_id = sys.argv[1]
path = Path("control_plane/data/product.json")
products = json.loads(path.read_text())
if product_id not in products:
    print("__ERROR__")
    sys.exit(0)
product = products[product_id]
metadata = product.get("metadata", {})
manifest_id = metadata.get("manifest_id", "")
image_name = product.get("docker_image_name", "llm-factory")
image_tag = product.get("docker_tag", "dev")
build_platform = metadata.get("build_platform", "")
manifest_store = metadata.get("manifest_store", "control_plane/data/manifest.json")

def set_env(key, value):
    print(f"{key}={shlex.quote(str(value))}")

set_env("MANIFEST_ID", manifest_id)
set_env("IMAGE_NAME", image_name)
set_env("IMAGE_BASE_TAG", image_tag)
set_env("BUILD_PLATFORM", build_platform)
set_env("MANIFEST_STORE", manifest_store)
PY
}

metadata_output=$(read_manifest_metadata "${PRODUCT_ID}")
if [[ "${metadata_output}" == "__ERROR__" ]]; then
  echo "Error: product '${PRODUCT_ID}' not found in control_plane/data/product.json" >&2
  exit 1
fi

while IFS='=' read -r key value; do
  eval "${key}=${value}"
done <<< "${metadata_output}"

if [[ -z "${MANIFEST_ID}" ]]; then
  echo "Error: manifest id missing for product '${PRODUCT_ID}'" >&2
  exit 1
fi

BUILD_ID="${PRODUCT_ID}-$(date +%Y%m%dT%H%M%S)"
IMAGE_TAG="${IMAGE_NAME}:${IMAGE_BASE_TAG}-ci-local"
EVIDENCE_DIR="control_plane/data/compatibility/evidence"
SBOM_DIR="control_plane/data/compatibility/sbom"
ERROR_RECORDS_DIR="control_plane/data/compatibility/records"
mkdir -p "${EVIDENCE_DIR}" "${SBOM_DIR}"
EVIDENCE_FILE="${EVIDENCE_DIR}/${BUILD_ID}.log"
SBOM_FILE=""
touch "${EVIDENCE_FILE}"

echo "# Build ID: ${BUILD_ID}" >> "${EVIDENCE_FILE}"

echo_to_logs() {
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

record_compat() {
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

record_failure() {
  trap - ERR
  echo "status: fail" >> "${EVIDENCE_FILE}"
  write_error_report "run-ci-local failure"
  record_compat fail "run-ci-local failure"
}

record_success() {
  trap - ERR
  record_compat pass "run-ci-local"
}

maybe_generate_sbom() {
  if command -v syft >/dev/null 2>&1; then
    SBOM_FILE="${SBOM_DIR}/${BUILD_ID}.json"
    echo_to_logs "[CI] Generating SBOM at ${SBOM_FILE}"
    ./tools/generate-sbom.sh "${IMAGE_TAG}" "${SBOM_FILE}" 2>&1 | tee -a "${EVIDENCE_FILE}"
  else
    echo_to_logs "[CI] Skipping SBOM generation (syft not installed)"
  fi
}

trap record_failure ERR

echo_to_logs "[CI] Rendering layered Dockerfile (manifest id ${MANIFEST_ID})"
python3 tools/stitch.py --manifest-id "${MANIFEST_ID}" --manifest-store "${MANIFEST_STORE}" 2>&1 | tee -a "${EVIDENCE_FILE}"

echo_to_logs "[CI] Building Docker image ${IMAGE_TAG}"
if [[ -n "${BUILD_PLATFORM}" ]]; then
  docker build --platform "${BUILD_PLATFORM}" -f dockerfiles/Dockerfile.rendered -t "${IMAGE_TAG}" . 2>&1 | tee -a "${EVIDENCE_FILE}"
else
  docker build -f dockerfiles/Dockerfile.rendered -t "${IMAGE_TAG}" . 2>&1 | tee -a "${EVIDENCE_FILE}"
fi

maybe_generate_sbom

echo_to_logs "[CI] Running smoke tests"
./tools/test-runner.sh "${IMAGE_TAG}" 2>&1 | tee -a "${EVIDENCE_FILE}"

echo_to_logs "[CI] Build and smoke tests completed successfully"
record_success
