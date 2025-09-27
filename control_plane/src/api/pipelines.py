"""Pipeline API endpoints backed by JSON configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from entities import Pipeline

router = APIRouter(prefix="/pipelines", tags=["pipelines"])

PIPELINES_PATH = Path(__file__).resolve().parents[2] / "data" / "pipeline.json"


class PipelineResponse(BaseModel):
    id: str
    name: str
    pipeline_type: str
    product_id: str
    status: str
    steps: list[str]
    artifacts: list[str]
    metadata: Dict[str, Any]


def _load_pipelines() -> Dict[str, Dict[str, Any]]:
    if not PIPELINES_PATH.exists():
        raise HTTPException(status_code=500, detail="Pipeline store not configured")
    try:
        return json.loads(PIPELINES_PATH.read_text())
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail="Invalid pipeline store format") from exc


def _get_pipeline(pipeline_id: str) -> Pipeline:
    pipelines = _load_pipelines()
    if pipeline_id not in pipelines:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return Pipeline.from_json(pipeline_id, pipelines[pipeline_id])


@router.get("/{pipeline_id}", response_model=PipelineResponse)
async def get_pipeline(pipeline_id: str) -> PipelineResponse:
    """Fetch a pipeline definition from the JSON store."""

    pipeline = _get_pipeline(pipeline_id)
    return PipelineResponse(**pipeline.to_dict())
