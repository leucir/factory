"""Tests for the JSON-backed Product API."""

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from main import app  # noqa: E402

client = TestClient(app)


def test_get_existing_product():
    response = client.get("/products/llm_factory")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "llm_factory"
    assert data["docker_image_name"] == "llm-factory"
    assert "manifest" in data["metadata"]


def test_get_cuda_product():
    response = client.get("/products/llm_factory_cuda")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "llm_factory_cuda"
    assert data["metadata"]["manifest"].endswith("llm_factory_cuda.json")


def test_get_unknown_product_returns_404():
    response = client.get("/products/does-not-exist")
    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"
