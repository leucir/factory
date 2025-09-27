#!/usr/bin/env bash
# Empirically determine the Docker image layer limit by attempting builds.

set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: ./tools/check-layer-limit.sh [--max N]

Attempts to build an image with incrementally more layers until Docker refuses
it, revealing the effective layer limit on this host. Requires Docker.

Options:
  --max N   Maximum layers to try (default: 200)
  -h, --help  Show this help message
USAGE
}

MAX_LAYERS=200
while [[ $# -gt 0 ]]; do
  case "$1" in
    --max)
      shift
      if [[ $# -eq 0 ]]; then
        echo "Error: --max requires a value" >&2
        exit 1
      fi
      MAX_LAYERS="$1"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
  shift
done

if ! command -v docker >/dev/null 2>&1; then
  echo "Error: docker not found on PATH" >&2
  exit 1
fi

format_elapsed() {
  local now elapsed
  now=$(date +%s)
  elapsed=$(( now - start_epoch ))
  printf '%02d:%02d:%02d' $((elapsed / 3600)) $(((elapsed % 3600) / 60)) $((elapsed % 60))
}

start_epoch=$(date +%s)
printf "[layer-limit][%s] Starting probe (max %s layers)\n" "$(format_elapsed)" "$MAX_LAYERS"

tmp_dir=$(mktemp -d "layer-limit.XXXXXX")
trap 'rm -rf "${tmp_dir}"; docker image rm -f layer-limit:test >/dev/null 2>&1 || true' EXIT

dockerfile="${tmp_dir}/Dockerfile"
workspace="${tmp_dir}/context"
mkdir -p "${workspace}"

cat <<'DOCKERFILE' >"${dockerfile}"
FROM alpine:3.19
DOCKERFILE

limit_reached=false
failure_layer=""

for ((layer=1; layer <= MAX_LAYERS; layer++)); do
  printf 'RUN echo layer_%03d > /dev/null\n' "$layer" >>"${dockerfile}"
  printf '[layer-limit][%s] Building with %3d layers... ' "$(format_elapsed)" "$layer"
  if build_output=$(docker build --no-cache --progress=plain \
      -t layer-limit:test -f "${dockerfile}" "${workspace}" 2>&1); then
    printf 'ok\n'
  else
    printf 'failed\n'
    echo "[layer-limit][$(format_elapsed)] Build failed at layer ${layer}."
    failure_layer="${layer}"
    echo "[layer-limit] Docker output:" >&2
    echo "${build_output}" >&2
    limit_reached=true
    break
  fi
  docker image rm -f layer-limit:test >/dev/null 2>&1 || true

done

if [[ "${limit_reached}" == true ]]; then
  effective_limit=$((failure_layer - 1))
  echo "[layer-limit][$(format_elapsed)] Empirical limit observed: ${effective_limit} layers (failure at layer ${failure_layer})."
else
  echo "[layer-limit][$(format_elapsed)] No failure encountered up to ${MAX_LAYERS} layers."
  echo "[layer-limit][$(format_elapsed)] Increase --max to probe further."
fi

storage_driver=$(docker info --format '{{.Driver}}' 2>/dev/null || echo "unknown")
echo "[layer-limit][$(format_elapsed)] Storage driver: ${storage_driver}"
