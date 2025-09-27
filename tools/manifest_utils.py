"""Helpers for loading manifests from the control plane manifest store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

DEFAULT_MANIFEST_STORE = Path("control_plane/data/manifest.json")


def load_manifest_from_store(store_path: Path, manifest_id: str) -> Dict:
    """Load a manifest definition by ID from the manifest store."""

    if not store_path.exists():
        raise FileNotFoundError(f"Manifest store not found: {store_path}")
    store = json.loads(store_path.read_text())
    if manifest_id not in store:
        raise KeyError(f"Manifest '{manifest_id}' not found in {store_path}")
    return store[manifest_id]


def load_manifest(manifest_path: Path | None, manifest_id: str, store_path: Path = DEFAULT_MANIFEST_STORE) -> Dict:
    """Load a manifest from either a standalone path or the manifest store."""

    if manifest_path:
        path = Path(manifest_path)
        if not path.exists():
            raise FileNotFoundError(f"Manifest not found at {path}")
        return json.loads(path.read_text())
    return load_manifest_from_store(store_path, manifest_id)


def iter_manifest_items(store_path: Path = DEFAULT_MANIFEST_STORE):
    """Yield (manifest_id, manifest_dict) pairs from the store."""

    store = json.loads(store_path.read_text())
    for key, value in store.items():
        yield key, value
