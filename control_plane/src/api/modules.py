"""Modules API endpoints for accessing module definitions and metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/modules", tags=["modules"])

MODULES_DIR = Path(__file__).resolve().parents[2] / "data" / "modules"


class ModuleVersionResponse(BaseModel):
    """Response model for module version data."""
    version: str
    metadata: Dict[str, Any]
    dockerfile_fragment: str
    requirements: List[str]
    path: str


class ModuleResponse(BaseModel):
    """Response model for module data."""
    name: str
    versions: List[str]
    latest_version: str
    description: str


def _load_module_metadata(module_name: str, version: str) -> Dict[str, Any]:
    """Load module metadata for a specific version."""
    module_path = MODULES_DIR / module_name / version / "module.json"
    if not module_path.exists():
        raise HTTPException(status_code=404, detail=f"Module {module_name} version {version} not found")
    try:
        return json.loads(module_path.read_text())
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="Invalid module metadata format") from exc


def _load_module_requirements(module_name: str, version: str) -> List[str]:
    """Load module requirements for a specific version."""
    requirements_path = MODULES_DIR / module_name / version / "requirements.txt"
    if not requirements_path.exists():
        return []
    try:
        return requirements_path.read_text().strip().split('\n')
    except Exception:
        return []


def _load_dockerfile_fragment(module_name: str, version: str) -> str:
    """Load Dockerfile fragment for a specific version."""
    fragment_path = MODULES_DIR / module_name / version / "Dockerfile.fragment"
    if not fragment_path.exists():
        return ""
    try:
        return fragment_path.read_text()
    except Exception:
        return ""


def _list_modules() -> List[str]:
    """List all available module names."""
    if not MODULES_DIR.exists():
        return []
    return [
        path.name for path in MODULES_DIR.iterdir()
        if path.is_dir() and not path.name.startswith('.')
    ]


def _list_module_versions(module_name: str) -> List[str]:
    """List all versions for a specific module."""
    module_path = MODULES_DIR / module_name
    if not module_path.exists():
        return []
    return [
        path.name for path in module_path.iterdir()
        if path.is_dir() and not path.name.startswith('.')
    ]


@router.get("/", response_model=List[ModuleResponse])
async def list_modules() -> List[ModuleResponse]:
    """List all available modules."""
    module_names = _list_modules()
    modules = []
    for module_name in module_names:
        versions = _list_module_versions(module_name)
        if not versions:
            continue
        
        # Get description from latest version
        latest_version = sorted(versions)[-1]
        try:
            metadata = _load_module_metadata(module_name, latest_version)
            description = metadata.get("description", f"Module {module_name}")
        except HTTPException:
            description = f"Module {module_name}"
        
        modules.append(ModuleResponse(
            name=module_name,
            versions=sorted(versions),
            latest_version=latest_version,
            description=description
        ))
    return modules


@router.get("/{module_name}", response_model=ModuleResponse)
async def get_module(module_name: str) -> ModuleResponse:
    """Get a specific module by name."""
    versions = _list_module_versions(module_name)
    if not versions:
        raise HTTPException(status_code=404, detail="Module not found")
    
    # Get description from latest version
    latest_version = sorted(versions)[-1]
    try:
        metadata = _load_module_metadata(module_name, latest_version)
        description = metadata.get("description", f"Module {module_name}")
    except HTTPException:
        description = f"Module {module_name}"
    
    return ModuleResponse(
        name=module_name,
        versions=sorted(versions),
        latest_version=latest_version,
        description=description
    )


@router.get("/{module_name}/versions", response_model=List[str])
async def list_module_versions(module_name: str) -> List[str]:
    """List all versions for a specific module."""
    versions = _list_module_versions(module_name)
    if not versions:
        raise HTTPException(status_code=404, detail="Module not found")
    return sorted(versions)


@router.get("/{module_name}/{version}", response_model=ModuleVersionResponse)
async def get_module_version(module_name: str, version: str) -> ModuleVersionResponse:
    """Get a specific module version."""
    try:
        metadata = _load_module_metadata(module_name, version)
        requirements = _load_module_requirements(module_name, version)
        dockerfile_fragment = _load_dockerfile_fragment(module_name, version)
        
        return ModuleVersionResponse(
            version=version,
            metadata=metadata,
            dockerfile_fragment=dockerfile_fragment,
            requirements=requirements,
            path=str(MODULES_DIR / module_name / version)
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error loading module version: {str(exc)}")
