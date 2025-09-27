"""Artifact API endpoints backed by JSON configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from entities import Artifact

router = APIRouter(prefix="/artifacts", tags=["artifacts"])

ARTIFACTS_PATH = Path(__file__).resolve().parents[2] / "data" / "artifact.json"


class ArtifactResponse(BaseModel):
    id: str
    name: str
    docker_image_name: str
    docker_tag: str
    pipeline_id: str
    metadata: Dict[str, Any]


def _load_artifacts() -> Dict[str, Dict[str, Any]]:
    if not ARTIFACTS_PATH.exists():
        raise HTTPException(status_code=500, detail="Artifact store not configured")
    try:
        return json.loads(ARTIFACTS_PATH.read_text())
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail="Invalid artifact store format") from exc


def _get_artifact(artifact_id: str) -> Artifact:
    artifacts = _load_artifacts()
    if artifact_id not in artifacts:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return Artifact.from_json(artifact_id, artifacts[artifact_id])


@router.get("/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(artifact_id: str) -> ArtifactResponse:
    """Fetch an artifact definition from the JSON store."""

    artifact = _get_artifact(artifact_id)
    return ArtifactResponse(**artifact.to_dict())
