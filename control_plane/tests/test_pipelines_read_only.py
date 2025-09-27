"""Tests for the JSON-backed Pipeline API."""

import os
import sys

from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from main import app  # noqa: E402

client = TestClient(app)


def test_get_existing_pipeline():
    response = client.get("/pipelines/layered_build_pipeline")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "layered_build_pipeline"
    assert data["product_id"] == "llm_factory"
    assert data["steps"]


def test_get_cuda_pipeline():
    response = client.get("/pipelines/layered_build_pipeline_cuda")
    assert response.status_code == 200
    data = response.json()
    assert data["product_id"] == "llm_factory_cuda"
    assert data["metadata"]["manifest"].endswith("llm_factory_cuda.json")


def test_get_unknown_pipeline_returns_404():
    response = client.get("/pipelines/does-not-exist")
    assert response.status_code == 404
    assert response.json()["detail"] == "Pipeline not found"
