"""Exploration (matrix) API: expand test plans and summarize results.

Read-only API that:
- Serves configured test plans from control_plane/data/test_plan.json
- Expands plans into combinations of module versions
- Aggregates existing compatibility records into a report per plan
"""

from __future__ import annotations

import itertools
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict


router = APIRouter(prefix="/explore", tags=["explore"])

ROOT = Path(__file__).resolve().parents[2]
PLANS_PATH = ROOT / "data" / "test_plan.json"
RECORDS_DIR = ROOT / "data" / "compatibility" / "records"


class PlanResponse(BaseModel):
    id: str
    name: str
    product_id: str
    description: str
    matrix: Dict[str, List[str]]
    fixed: Dict[str, str]
    manifest: str


class Combo(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    security_version: str
    core_version: str
    light_version: str
    model_serve_mock_version: str


class ComboReport(Combo):
    model_config = ConfigDict(protected_namespaces=())

    status: str  # pass | fail | missing
    pass_count: int
    fail_count: int
    last_tested_at: str
    record_ids: List[str]


def _load_plans() -> Dict[str, Dict[str, Any]]:
    if not PLANS_PATH.exists():
        raise HTTPException(status_code=500, detail="Test plan store not configured")
    try:
        return json.loads(PLANS_PATH.read_text())
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail="Invalid test plan store format") from exc


def _get_plan(plan_id: str) -> Dict[str, Any]:
    plans = _load_plans()
    if plan_id not in plans:
        raise HTTPException(status_code=404, detail="Test plan not found")
    return plans[plan_id]


@router.get("/plans", response_model=List[PlanResponse])
async def list_plans() -> List[PlanResponse]:
    plans = _load_plans()
    out: List[PlanResponse] = []
    for pid, payload in plans.items():
        out.append(
            PlanResponse(
                id=pid,
                name=payload.get("name", pid),
                product_id=payload.get("product_id", ""),
                description=payload.get("description", ""),
                matrix=payload.get("matrix", {}),
                fixed=payload.get("fixed", {}),
                manifest=payload.get("manifest", ""),
            )
        )
    return out


@router.get("/plans/{plan_id}", response_model=PlanResponse)
async def get_plan(plan_id: str) -> PlanResponse:
    payload = _get_plan(plan_id)
    return PlanResponse(
        id=plan_id,
        name=payload.get("name", plan_id),
        product_id=payload.get("product_id", ""),
        description=payload.get("description", ""),
        matrix=payload.get("matrix", {}),
        fixed=payload.get("fixed", {}),
        manifest=payload.get("manifest", ""),
    )


def _expand(plan: Dict[str, Any]) -> List[Combo]:
    fixed = plan.get("fixed", {})
    mat = plan.get("matrix", {})
    cores = mat.get("core", [])
    lights = mat.get("light", [])
    sec = fixed.get("security", "")
    model_serve = fixed.get("model_serve_mock", "")
    combos: List[Combo] = []
    for core_v, light_v in itertools.product(cores, lights):
        combos.append(
            Combo(
                security_version=sec,
                core_version=core_v,
                light_version=light_v,
                model_serve_mock_version=model_serve,
            )
        )
    return combos


@router.get("/plans/{plan_id}/expand", response_model=List[Combo])
async def expand_plan(plan_id: str) -> List[Combo]:
    return _expand(_get_plan(plan_id))


def _iter_record_paths() -> List[Path]:
    if not RECORDS_DIR.exists():
        return []
    return sorted([p for p in RECORDS_DIR.glob("*.json") if p.is_file()])


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text())


def _aggregate_for_combo(combo: Combo, product_id: str) -> ComboReport:
    pass_count = 0
    fail_count = 0
    last_tested: Optional[datetime] = None
    record_ids: List[str] = []

    for path in _iter_record_paths():
        rec = _load_json(path)
        meta = rec.get("metadata", {})
        if meta.get("product_id") != product_id:
            continue
        if (
            rec.get("security_version") == combo.security_version
            and rec.get("core_version") == combo.core_version
            and rec.get("light_version") == combo.light_version
            and rec.get("model_serve_mock_version") == combo.model_serve_mock_version
        ):
            status = (rec.get("result") or {}).get("status")
            if status == "pass":
                pass_count += 1
            elif status == "fail":
                fail_count += 1
            ts = (rec.get("result") or {}).get("tested_at")
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None
            except Exception:
                dt = None
            if dt and (last_tested is None or dt > last_tested):
                last_tested = dt
            record_ids.append(path.stem)

    status = "missing"
    if pass_count:
        status = "pass"
    elif fail_count:
        status = "fail"

    combo_data = combo.model_dump()
    return ComboReport(
        **combo_data,
        status=status,
        pass_count=pass_count,
        fail_count=fail_count,
        last_tested_at=(last_tested.isoformat().replace("+00:00", "Z") if last_tested else ""),
        record_ids=record_ids,
    )


@router.get("/plans/{plan_id}/report", response_model=List[ComboReport])
async def report_plan(plan_id: str) -> List[ComboReport]:
    plan = _get_plan(plan_id)
    product_id = plan.get("product_id", "")
    combos = _expand(plan)
    return [_aggregate_for_combo(c, product_id) for c in combos]
