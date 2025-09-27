"""Tests for the JSON-backed Artifact API."""

import os
import sys

from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from main import app  # noqa: E402

client = TestClient(app)


def test_get_existing_artifact():
    response = client.get("/artifacts/llm_factory_image")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "llm_factory_image"
    assert data["pipeline_id"] == "layered_build_pipeline"
    assert data["docker_image_name"] == "llm-factory"


def test_get_cuda_artifact():
    response = client.get("/artifacts/llm_factory_cuda_image")
    assert response.status_code == 200
    data = response.json()
    assert data["pipeline_id"] == "layered_build_pipeline_cuda"
    assert data["docker_image_name"] == "llm-factory-cuda"


def test_get_unknown_artifact_returns_404():
    response = client.get("/artifacts/does-not-exist")
    assert response.status_code == 404
    assert response.json()["detail"] == "Artifact not found"
