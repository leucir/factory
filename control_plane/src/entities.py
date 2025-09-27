"""Simplified control plane entities for the prototype."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import uuid4


def _uuid() -> str:
    """Return a UUID4 string."""
    return str(uuid4())


@dataclass
class Product:
    """Represents a Docker container product in the control plane."""

    id: str = field(default_factory=_uuid)
    name: str = ""
    description: str = ""
    docker_image_name: str = ""
    docker_tag: str = "latest"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert product to a serialisable dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "docker_image_name": self.docker_image_name,
            "docker_tag": self.docker_tag,
            "metadata": self.metadata,
        }

    @classmethod
    def from_json(cls, product_id: str, payload: Dict[str, Any]) -> "Product":
        """Create a product instance from JSON payload."""

        return cls(
            id=product_id,
            name=payload.get("name", ""),
            description=payload.get("description", ""),
            docker_image_name=payload.get("docker_image_name", ""),
            docker_tag=payload.get("docker_tag", "latest"),
            metadata=payload.get("metadata", {}),
        )


@dataclass
class Artifact:
    """Represents an artifact produced by pipeline execution."""

    id: str = field(default_factory=_uuid)
    name: str = ""
    docker_image_name: str = ""
    docker_tag: str = ""
    pipeline_id: str = field(default_factory=_uuid)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert artifact to a serialisable dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "docker_image_name": self.docker_image_name,
            "docker_tag": self.docker_tag,
            "pipeline_id": self.pipeline_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_json(cls, artifact_id: str, payload: Dict[str, Any]) -> "Artifact":
        """Create an artifact instance from JSON payload."""

        return cls(
            id=artifact_id,
            name=payload.get("name", ""),
            docker_image_name=payload.get("docker_image_name", ""),
            docker_tag=payload.get("docker_tag", ""),
            pipeline_id=payload.get("pipeline_id", ""),
            metadata=payload.get("metadata", {}),
        )


@dataclass
class Pipeline:
    """Represents a pipeline that builds Docker container products."""

    id: str = field(default_factory=_uuid)
    name: str = ""
    pipeline_type: str = "simple"
    product_id: str = field(default_factory=_uuid)
    status: str = "pending"
    steps: List[str] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert pipeline to a serialisable dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "pipeline_type": self.pipeline_type,
            "product_id": self.product_id,
            "status": self.status,
            "steps": self.steps,
            "artifacts": self.artifacts,
            "metadata": self.metadata,
        }

    @classmethod
    def from_json(cls, pipeline_id: str, payload: Dict[str, Any]) -> "Pipeline":
        """Create a pipeline instance from JSON payload."""

        return cls(
            id=pipeline_id,
            name=payload.get("name", ""),
            pipeline_type=payload.get("pipeline_type", "simple"),
            product_id=payload.get("product_id", ""),
            status=payload.get("status", "pending"),
            steps=payload.get("steps", []),
            artifacts=payload.get("artifacts", []),
            metadata=payload.get("metadata", {}),
        )


def create_product(
    name: str,
    docker_image_name: str,
    description: str = "",
    docker_tag: str = "latest",
    metadata: Optional[Dict[str, Any]] = None,
) -> Product:
    """Create a new product instance."""

    return Product(
        name=name,
        description=description,
        docker_image_name=docker_image_name,
        docker_tag=docker_tag,
        metadata=metadata or {},
    )


def create_artifact(
    name: str,
    docker_image_name: str,
    docker_tag: str,
    pipeline_id: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Artifact:
    """Create a new artifact instance."""

    return Artifact(
        name=name,
        docker_image_name=docker_image_name,
        docker_tag=docker_tag,
        pipeline_id=pipeline_id,
        metadata=metadata or {},
    )


def create_pipeline(
    name: str,
    product_id: str,
    pipeline_type: str = "simple",
    steps: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Pipeline:
    """Create a new pipeline instance."""

    return Pipeline(
        name=name,
        product_id=product_id,
        pipeline_type=pipeline_type,
        steps=steps or [],
        metadata=metadata or {},
    )
