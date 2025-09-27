"""Tests for the JSON-backed Compatibility API."""

import os
import sys

from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from main import app  # noqa: E402


client = TestClient(app)


def test_list_compatibility_records():
    response = client.get("/compatibility/records")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(item["id"] == "sample" for item in data)
    # Validate shape of an element
    item = data[0]
    for key in [
        "id",
        "build_id",
        "product_id",
        "status",
        "tested_at",
        "manifest",
        "template_id",
        "template_version",
        "core_version",
        "light_version",
    ]:
        assert key in item


def test_get_record_by_id_sample():
    response = client.get("/compatibility/records/sample")
    assert response.status_code == 200
    rec = response.json()
    assert rec["build_id"] == "sample-build-001"
    assert rec["metadata"]["product_id"] == "llm_factory"


def test_get_record_by_build_id():
    # choose a known existing build_id we copied over
    response = client.get("/compatibility/records/by-build/llm_factory_cuda-20250926T135300")
    assert response.status_code == 200
    rec = response.json()
    assert rec["template_id"] == "llm_factory"
    assert rec["core_version"] == "0.2.0"


def test_get_unknown_record_returns_404():
    response = client.get("/compatibility/records/does-not-exist")
    assert response.status_code == 404
    assert response.json()["detail"] == "Record not found"

