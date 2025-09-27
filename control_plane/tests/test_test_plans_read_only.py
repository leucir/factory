"""Tests for the JSON-backed Test Plans API."""

import os
import sys

from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from main import app  # noqa: E402

client = TestClient(app)


def test_list_test_plans():
    """Test listing all test plans."""
    response = client.get("/test-plans/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    
    # Check that we have expected test plans
    plan_ids = [plan["id"] for plan in data]
    assert "baseline_core_light" in plan_ids
    assert "incompatible_core_light" in plan_ids


def test_get_existing_test_plan():
    """Test getting a specific test plan."""
    response = client.get("/test-plans/baseline_core_light")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "baseline_core_light"
    assert "name" in data
    assert "description" in data
    assert "product_id" in data
    assert "manifest_id" in data
    assert "fixed" in data
    assert "matrix" in data
    
    # Check that it has the expected product
    assert data["product_id"] == "llm_factory"
    
    # Check matrix structure
    matrix = data["matrix"]
    assert isinstance(matrix, dict)
    assert "core" in matrix
    assert "light" in matrix
    assert isinstance(matrix["core"], list)
    assert isinstance(matrix["light"], list)
    
    # Check fixed modules
    fixed = data["fixed"]
    assert isinstance(fixed, dict)
    assert "security" in fixed
    assert "model_serve_mock" in fixed


def test_get_incompatible_test_plan():
    """Test getting the incompatible test plan."""
    response = client.get("/test-plans/incompatible_core_light")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "incompatible_core_light"
    assert data["product_id"] == "llm_factory"
    
    # Check matrix structure
    matrix = data["matrix"]
    assert "core" in matrix
    assert "light" in matrix
    assert len(matrix["core"]) > 0
    assert len(matrix["light"]) > 0


def test_get_unknown_test_plan_returns_404():
    """Test getting a non-existent test plan returns 404."""
    response = client.get("/test-plans/does-not-exist")
    assert response.status_code == 404
    assert response.json()["detail"] == "Test plan not found"


def test_test_plan_structure():
    """Test that test plan response has correct structure."""
    response = client.get("/test-plans/baseline_core_light")
    assert response.status_code == 200
    data = response.json()
    
    # Check required fields
    required_fields = ["id", "name", "description", "product_id", "manifest_id", "fixed", "matrix"]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"
    
    # Check that fields have correct types
    assert isinstance(data["name"], str)
    assert isinstance(data["description"], str)
    assert isinstance(data["product_id"], str)
    assert isinstance(data["manifest_id"], str)
    assert isinstance(data["fixed"], dict)
    assert isinstance(data["matrix"], dict)


def test_test_plan_matrix_content():
    """Test that test plan matrix has expected content."""
    response = client.get("/test-plans/baseline_core_light")
    assert response.status_code == 200
    data = response.json()
    
    matrix = data["matrix"]
    
    # Check core versions
    core_versions = matrix["core"]
    assert isinstance(core_versions, list)
    assert len(core_versions) > 0
    assert "0.1.0" in core_versions
    assert "0.2.0" in core_versions
    
    # Check light versions
    light_versions = matrix["light"]
    assert isinstance(light_versions, list)
    assert len(light_versions) > 0
    assert "0.1.0" in light_versions
    
    # Check fixed modules
    fixed = data["fixed"]
    assert fixed["security"] == "0.1.0"
    assert fixed["model_serve_mock"] == "0.1.0"
