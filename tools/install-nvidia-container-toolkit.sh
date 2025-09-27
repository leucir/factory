#!/usr/bin/env bash
# Install NVIDIA Container Toolkit on Ubuntu hosts (requires sudo).
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Error: Please run as root (sudo)." >&2
  exit 1
fi

. /etc/os-release
DISTRIBUTION="${ID}${VERSION_ID}"

curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -fsSL https://nvidia.github.io/libnvidia-container/${DISTRIBUTION}/libnvidia-container.list | \
  tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

apt-get update
apt-get install -y nvidia-container-toolkit

nvidia-ctk runtime configure --runtime=docker
systemctl restart docker

echo "NVIDIA Container Toolkit installation complete."
