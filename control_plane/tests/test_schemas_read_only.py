"""Tests for the JSON-backed Schemas API."""

import os
import sys

from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from main import app  # noqa: E402

client = TestClient(app)


def test_list_schemas():
    """Test listing all schemas."""
    response = client.get("/schemas/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    
    # Check that we have the compatibility schema
    schema_ids = [schema["id"] for schema in data]
    assert "compatibility" in schema_ids


def test_get_existing_schema():
    """Test getting a specific schema."""
    response = client.get("/schemas/compatibility")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "compatibility"
    assert "name" in data
    assert "schema" in data
    assert "path" in data
    
    # Check schema structure
    schema = data["schema"]
    assert isinstance(schema, dict)
    assert "$schema" in schema
    assert "title" in schema
    assert "type" in schema
    assert "properties" in schema


def test_get_unknown_schema_returns_404():
    """Test getting a non-existent schema returns 404."""
    response = client.get("/schemas/does-not-exist")
    assert response.status_code == 404
    assert response.json()["detail"] == "Schema not found"


def test_schema_structure():
    """Test that schema response has correct structure."""
    response = client.get("/schemas/compatibility")
    assert response.status_code == 200
    data = response.json()
    
    # Check required fields
    required_fields = ["id", "name", "schema", "path"]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"
    
    # Check that schema is valid JSON schema
    schema = data["schema"]
    assert "$schema" in schema
    assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
    assert schema["title"] == "CompatibilityRecord"
    assert schema["type"] == "object"
    assert "properties" in schema
    assert "required" in schema


def test_schema_path():
    """Test that schema path is correctly formatted."""
    response = client.get("/schemas/compatibility")
    assert response.status_code == 200
    data = response.json()
    
    path = data["path"]
    assert isinstance(path, str)
    assert "compatibility.schema.json" in path
    assert "control_plane/data/schemas" in path
