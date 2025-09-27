"""Schema API endpoints for accessing JSON schemas."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/schemas", tags=["schemas"])

SCHEMAS_DIR = Path(__file__).resolve().parents[2] / "data" / "schemas"


class SchemaResponse(BaseModel):
    """Response model for schema data."""
    id: str
    name: str
    schema: Dict[str, Any]
    path: str


def _load_schema(schema_id: str) -> Dict[str, Any]:
    """Load a specific schema by ID."""
    schema_path = SCHEMAS_DIR / f"{schema_id}.schema.json"
    if not schema_path.exists():
        raise HTTPException(status_code=404, detail="Schema not found")
    try:
        return json.loads(schema_path.read_text())
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="Invalid schema format") from exc


def _list_schemas() -> List[str]:
    """List all available schema IDs."""
    if not SCHEMAS_DIR.exists():
        return []
    return [
        path.stem.replace(".schema", "")
        for path in SCHEMAS_DIR.glob("*.schema.json")
    ]


@router.get("/", response_model=List[SchemaResponse])
async def list_schemas() -> List[SchemaResponse]:
    """List all available schemas."""
    schema_ids = _list_schemas()
    schemas = []
    for schema_id in schema_ids:
        try:
            schema_data = _load_schema(schema_id)
            schemas.append(SchemaResponse(
                id=schema_id,
                name=schema_data.get("title", schema_id),
                schema=schema_data,
                path=str(SCHEMAS_DIR / f"{schema_id}.schema.json")
            ))
        except HTTPException:
            # Skip schemas that can't be loaded
            continue
    return schemas


@router.get("/{schema_id}", response_model=SchemaResponse)
async def get_schema(schema_id: str) -> SchemaResponse:
    """Get a specific schema by ID."""
    schema_data = _load_schema(schema_id)
    return SchemaResponse(
        id=schema_id,
        name=schema_data.get("title", schema_id),
        schema=schema_data,
        path=str(SCHEMAS_DIR / f"{schema_id}.schema.json")
    )
