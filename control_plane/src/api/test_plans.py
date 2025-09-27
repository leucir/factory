"""Test Plans API endpoints for accessing test plan configurations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/test-plans", tags=["test-plans"])

TEST_PLANS_PATH = Path(__file__).resolve().parents[2] / "data" / "test_plan.json"


class TestPlanResponse(BaseModel):
    """Response model for test plan data."""
    id: str
    name: str
    description: str
    product_id: str
    manifest_id: str
    fixed: Dict[str, str]
    matrix: Dict[str, List[str]]


def _load_test_plans() -> Dict[str, Dict[str, Any]]:
    """Load test plans from JSON file."""
    if not TEST_PLANS_PATH.exists():
        raise HTTPException(status_code=500, detail="Test plan store not configured")
    try:
        return json.loads(TEST_PLANS_PATH.read_text())
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="Invalid test plan store format") from exc


def _get_test_plan(plan_id: str) -> Dict[str, Any]:
    """Get a specific test plan by ID."""
    test_plans = _load_test_plans()
    if plan_id not in test_plans:
        raise HTTPException(status_code=404, detail="Test plan not found")
    return test_plans[plan_id]


@router.get("/", response_model=List[TestPlanResponse])
async def list_test_plans() -> List[TestPlanResponse]:
    """List all available test plans."""
    test_plans = _load_test_plans()
    return [
        TestPlanResponse(
            id=plan_id,
            name=plan_data.get("name", plan_id),
            description=plan_data.get("description", ""),
            product_id=plan_data.get("product_id", ""),
            manifest_id=plan_data.get("manifest_id", ""),
            fixed=plan_data.get("fixed", {}),
            matrix=plan_data.get("matrix", {})
        )
        for plan_id, plan_data in test_plans.items()
    ]


@router.get("/{plan_id}", response_model=TestPlanResponse)
async def get_test_plan(plan_id: str) -> TestPlanResponse:
    """Get a specific test plan by ID."""
    plan_data = _get_test_plan(plan_id)
    return TestPlanResponse(
        id=plan_id,
        name=plan_data.get("name", plan_id),
        description=plan_data.get("description", ""),
        product_id=plan_data.get("product_id", ""),
        manifest_id=plan_data.get("manifest_id", ""),
        fixed=plan_data.get("fixed", {}),
        matrix=plan_data.get("matrix", {})
    )
