"""Manifest API endpoints for accessing manifest configurations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/manifests", tags=["manifests"])

MANIFESTS_PATH = Path(__file__).resolve().parents[2] / "data" / "manifest.json"


class ManifestResponse(BaseModel):
    """Response model for manifest data."""
    id: str
    template: Dict[str, Any]
    modules: List[Dict[str, str]]
    base_image: str
    output: str


def _load_manifests() -> Dict[str, Dict[str, Any]]:
    """Load manifests from JSON file."""
    if not MANIFESTS_PATH.exists():
        raise HTTPException(status_code=500, detail="Manifest store not configured")
    try:
        return json.loads(MANIFESTS_PATH.read_text())
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="Invalid manifest store format") from exc


def _get_manifest(manifest_id: str) -> Dict[str, Any]:
    """Get a specific manifest by ID."""
    manifests = _load_manifests()
    if manifest_id not in manifests:
        raise HTTPException(status_code=404, detail="Manifest not found")
    return manifests[manifest_id]


@router.get("/", response_model=List[ManifestResponse])
async def list_manifests() -> List[ManifestResponse]:
    """List all available manifests."""
    manifests = _load_manifests()
    return [
        ManifestResponse(
            id=manifest_id,
            template=manifest_data.get("template", {}),
            modules=manifest_data.get("modules", []),
            base_image=manifest_data.get("base_image", ""),
            output=manifest_data.get("output", "")
        )
        for manifest_id, manifest_data in manifests.items()
    ]


@router.get("/{manifest_id}", response_model=ManifestResponse)
async def get_manifest(manifest_id: str) -> ManifestResponse:
    """Get a specific manifest by ID."""
    manifest_data = _get_manifest(manifest_id)
    return ManifestResponse(
        id=manifest_id,
        template=manifest_data.get("template", {}),
        modules=manifest_data.get("modules", []),
        base_image=manifest_data.get("base_image", ""),
        output=manifest_data.get("output", "")
    )
