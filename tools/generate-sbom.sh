#!/usr/bin/env bash
# Generate an SBOM for a container image using Syft.
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <image> <output-file>" >&2
  exit 1
fi

IMAGE="$1"
OUTPUT="$2"

if ! command -v syft >/dev/null 2>&1; then
  echo "Error: syft not found on PATH. Install from https://github.com/anchore/syft" >&2
  exit 1
fi

syft "${IMAGE}" -o json > "${OUTPUT}"

echo "SBOM written to ${OUTPUT}"
