"""Tests for the Exploration (matrix) API."""

import os
import sys

from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from main import app  # noqa: E402


client = TestClient(app)


def test_list_plans():
    resp = client.get("/explore/plans")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list) and data
    ids = {p["id"] for p in data}
    assert "baseline_core_light" in ids
    assert "incompatible_core_light" in ids


def test_get_plan():
    resp = client.get("/explore/plans/baseline_core_light")
    assert resp.status_code == 200
    plan = resp.json()
    assert plan["product_id"] == "llm_factory"
    assert plan["matrix"]["core"] == ["0.1.0", "0.2.0"]


def test_expand_plan():
    resp = client.get("/explore/plans/baseline_core_light/expand")
    assert resp.status_code == 200
    combos = resp.json()
    # 2 core versions x 1 light set = 2 combos
    assert len(combos) == 2
    cores = sorted({c["core_version"] for c in combos})
    assert cores == ["0.1.0", "0.2.0"]
    # fixed modules present
    for c in combos:
        assert c["security_version"] == "0.1.0"
        assert c["model_serve_mock_version"] == "0.1.0"


def test_expand_incompatible_plan():
    resp = client.get("/explore/plans/incompatible_core_light/expand")
    assert resp.status_code == 200
    combos = resp.json()
    # 2 cores x 2 lights = 4 combos
    assert len(combos) == 4
    cores = {c["core_version"] for c in combos}
    lights = {c["light_version"] for c in combos}
    assert cores == {"0.1.0", "0.3.0"}
    assert lights == {"0.1.0", "0.2.0"}
    # confirm fixed modules applied
    for c in combos:
        assert c["security_version"] == "0.1.0"
        assert c["model_serve_mock_version"] == "0.1.0"


def test_report_plan_aggregates_records():
    resp = client.get("/explore/plans/baseline_core_light/report")
    assert resp.status_code == 200
    report = resp.json()
    assert len(report) == 2
    # Both combos should have some result recorded in sample data
    for row in report:
        assert row["status"] in {"pass", "fail", "missing"}
        assert row["pass_count"] + row["fail_count"] >= 0
    # Validate that core 0.1.0 combo has at least one pass in our sample set
    c01 = next(r for r in report if r["core_version"] == "0.1.0")
    assert c01["pass_count"] >= 1
    # Validate that core 0.2.0 combo has mixed results in our sample set (at least one pass)
    c02 = next(r for r in report if r["core_version"] == "0.2.0")
    assert c02["pass_count"] >= 1
