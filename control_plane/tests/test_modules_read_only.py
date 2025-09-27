"""Tests for the JSON-backed Modules API."""

import os
import sys

from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from main import app  # noqa: E402

client = TestClient(app)


def test_list_modules():
    """Test listing all modules."""
    response = client.get("/modules/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    
    # Check that we have expected modules
    module_names = [module["name"] for module in data]
    assert "core" in module_names
    assert "light" in module_names
    assert "security" in module_names
    assert "model_serve_mock" in module_names


def test_get_existing_module():
    """Test getting a specific module."""
    response = client.get("/modules/core")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "core"
    assert "versions" in data
    assert "latest_version" in data
    assert "description" in data
    
    # Check versions
    versions = data["versions"]
    assert isinstance(versions, list)
    assert len(versions) > 0
    assert "0.1.0" in versions
    assert "0.2.0" in versions
    assert "0.3.0" in versions
    
    # Check latest version
    assert data["latest_version"] in versions


def test_get_light_module():
    """Test getting the light module."""
    response = client.get("/modules/light")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "light"
    assert "versions" in data
    assert "latest_version" in data
    
    # Check versions
    versions = data["versions"]
    assert isinstance(versions, list)
    assert len(versions) > 0
    assert "0.1.0" in versions
    assert "0.2.0" in versions


def test_get_security_module():
    """Test getting the security module."""
    response = client.get("/modules/security")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "security"
    assert "versions" in data
    assert "latest_version" in data
    
    # Check versions
    versions = data["versions"]
    assert isinstance(versions, list)
    assert len(versions) > 0
    assert "0.1.0" in versions


def test_get_model_serve_mock_module():
    """Test getting the model_serve_mock module."""
    response = client.get("/modules/model_serve_mock")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "model_serve_mock"
    assert "versions" in data
    assert "latest_version" in data
    
    # Check versions
    versions = data["versions"]
    assert isinstance(versions, list)
    assert len(versions) > 0
    assert "0.1.0" in versions


def test_get_unknown_module_returns_404():
    """Test getting a non-existent module returns 404."""
    response = client.get("/modules/does-not-exist")
    assert response.status_code == 404
    assert response.json()["detail"] == "Module not found"


def test_list_module_versions():
    """Test listing versions for a specific module."""
    response = client.get("/modules/core/versions")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "0.1.0" in data
    assert "0.2.0" in data
    assert "0.3.0" in data


def test_get_specific_module_version():
    """Test getting a specific module version."""
    response = client.get("/modules/core/0.3.0")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "0.3.0"
    assert "metadata" in data
    assert "dockerfile_fragment" in data
    assert "requirements" in data
    assert "path" in data
    
    # Check metadata structure
    metadata = data["metadata"]
    assert isinstance(metadata, dict)
    assert "name" in metadata
    assert "version" in metadata
    assert metadata["name"] == "core"
    assert metadata["version"] == "0.3.0"
    
    # Check requirements
    requirements = data["requirements"]
    assert isinstance(requirements, list)
    assert len(requirements) > 0
    
    # Check path
    path = data["path"]
    assert isinstance(path, str)
    assert "control_plane/data/modules/core/0.3.0" in path


def test_get_unknown_module_version_returns_404():
    """Test getting a non-existent module version returns 404."""
    response = client.get("/modules/core/999.999.999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Module core version 999.999.999 not found"


def test_get_unknown_module_versions_returns_404():
    """Test getting versions for a non-existent module returns 404."""
    response = client.get("/modules/does-not-exist/versions")
    assert response.status_code == 404
    assert response.json()["detail"] == "Module not found"


def test_module_structure():
    """Test that module response has correct structure."""
    response = client.get("/modules/core")
    assert response.status_code == 200
    data = response.json()
    
    # Check required fields
    required_fields = ["name", "versions", "latest_version", "description"]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"
    
    # Check that fields have correct types
    assert isinstance(data["name"], str)
    assert isinstance(data["versions"], list)
    assert isinstance(data["latest_version"], str)
    assert isinstance(data["description"], str)


def test_module_version_structure():
    """Test that module version response has correct structure."""
    response = client.get("/modules/core/0.3.0")
    assert response.status_code == 200
    data = response.json()
    
    # Check required fields
    required_fields = ["version", "metadata", "dockerfile_fragment", "requirements", "path"]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"
    
    # Check that fields have correct types
    assert isinstance(data["version"], str)
    assert isinstance(data["metadata"], dict)
    assert isinstance(data["dockerfile_fragment"], str)
    assert isinstance(data["requirements"], list)
    assert isinstance(data["path"], str)
