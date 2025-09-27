"""Tests for the JSON-backed Manifests API."""

import os
import sys

from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from main import app  # noqa: E402

client = TestClient(app)


def test_list_manifests():
    """Test listing all manifests."""
    response = client.get("/manifests/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    
    # Check that we have expected manifests
    manifest_ids = [manifest["id"] for manifest in data]
    assert "llm_factory" in manifest_ids
    assert "llm_factory_cuda" in manifest_ids


def test_get_existing_manifest():
    """Test getting a specific manifest."""
    response = client.get("/manifests/llm_factory")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "llm_factory"
    assert "template" in data
    assert "modules" in data
    assert "base_image" in data
    assert "output" in data
    
    # Check template structure
    template = data["template"]
    assert "id" in template
    assert "version" in template
    
    # Check modules structure
    modules = data["modules"]
    assert isinstance(modules, list)
    assert len(modules) > 0
    
    # Check that we have expected modules
    module_names = [module["name"] for module in modules]
    assert "security" in module_names
    assert "core" in module_names
    assert "light" in module_names
    assert "model_serve_mock" in module_names


def test_get_cuda_manifest():
    """Test getting the CUDA manifest."""
    response = client.get("/manifests/llm_factory_cuda")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "llm_factory_cuda"
    assert data["base_image"] == "ubuntu:22.04"
    
    # Check that it has the same modules but potentially different versions
    modules = data["modules"]
    assert isinstance(modules, list)
    assert len(modules) > 0


def test_get_unknown_manifest_returns_404():
    """Test getting a non-existent manifest returns 404."""
    response = client.get("/manifests/does-not-exist")
    assert response.status_code == 404
    assert response.json()["detail"] == "Manifest not found"


def test_manifest_structure():
    """Test that manifest response has correct structure."""
    response = client.get("/manifests/llm_factory")
    assert response.status_code == 200
    data = response.json()
    
    # Check required fields
    required_fields = ["id", "template", "modules", "base_image", "output"]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"
    
    # Check template structure
    template = data["template"]
    assert isinstance(template, dict)
    assert "id" in template
    assert "version" in template
    
    # Check modules structure
    modules = data["modules"]
    assert isinstance(modules, list)
    for module in modules:
        assert "name" in module
        assert "version" in module
        assert isinstance(module["name"], str)
        assert isinstance(module["version"], str)
