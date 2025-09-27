#!/usr/bin/env bash
# Lightweight smoke test runner for the rendered image.
set -euo pipefail

IMAGE_TAG="${1:-llm-factory:test}"
CONTAINER_NAME="llm-factory-smoke"

cleanup() {
  docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
}

trap cleanup EXIT

cleanup

docker run -d --rm --name "${CONTAINER_NAME}" -p 8080:8080 "${IMAGE_TAG}"

# Wait for health endpoint
for _ in {1..30}; do
  if curl -sf http://localhost:8080/healthz >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

curl -sf http://localhost:8080/healthz >/dev/null
curl -sf -X POST http://localhost:8080/v1/completions \
  -H 'content-type: application/json' \
  -d '{"model":"gpt-3.5-turbo","prompt":"Hello","max_tokens":8}' >/dev/null

echo "Smoke tests passed for ${IMAGE_TAG}"
