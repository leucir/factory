"""Compatibility records API backed by JSON files under control_plane/data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel


router = APIRouter(prefix="/compatibility", tags=["compatibility"])

# control_plane/src/api/ -> parents[2] == control_plane/
RECORDS_DIR = Path(__file__).resolve().parents[2] / "data" / "compatibility" / "records"


class RecordSummary(BaseModel):
    id: str
    build_id: str
    product_id: str
    status: str
    tested_at: str
    manifest: str
    template_id: str
    template_version: str
    core_version: str
    light_version: str


def _iter_record_paths() -> List[Path]:
    if not RECORDS_DIR.exists():
        return []
    return sorted([p for p in RECORDS_DIR.glob("*.json") if p.is_file()])


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=f"Invalid JSON in record {path.name}") from exc


def _to_summary(path: Path, rec: Dict[str, Any]) -> RecordSummary:
    return RecordSummary(
        id=path.stem,
        build_id=rec.get("build_id", ""),
        product_id=rec.get("metadata", {}).get("product_id", ""),
        status=rec.get("result", {}).get("status", ""),
        tested_at=rec.get("result", {}).get("tested_at", ""),
        manifest=rec.get("metadata", {}).get("manifest", ""),
        template_id=rec.get("template_id", ""),
        template_version=rec.get("template_version", ""),
        core_version=rec.get("core_version", ""),
        light_version=rec.get("light_version", ""),
    )


@router.get("/records", response_model=list[RecordSummary])
async def list_records(product_id: Optional[str] = Query(default=None)) -> List[RecordSummary]:
    """List compatibility records, optionally filtered by product_id."""

    summaries: List[RecordSummary] = []
    for path in _iter_record_paths():
        rec = _load_json(path)
        if product_id and rec.get("metadata", {}).get("product_id") != product_id:
            continue
        summaries.append(_to_summary(path, rec))
    return summaries


@router.get("/records/{record_id}", response_model=Dict[str, Any])
async def get_record(record_id: str) -> Dict[str, Any]:
    """Fetch a full compatibility record by filename stem."""

    path = RECORDS_DIR / f"{record_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Record not found")
    return _load_json(path)


@router.get("/records/by-build/{build_id}", response_model=Dict[str, Any])
async def get_record_by_build_id(build_id: str) -> Dict[str, Any]:
    """Fetch a compatibility record by build_id value."""

    for path in _iter_record_paths():
        rec = _load_json(path)
        if rec.get("build_id") == build_id:
            return rec
    raise HTTPException(status_code=404, detail="Record not found")

