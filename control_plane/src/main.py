"""
Control Plane FastAPI Application

This module contains the main FastAPI application for the factory control plane.
Simplified to focus on core entities: Product, Artifact, and Pipeline.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
import uvicorn

from entities import (
    Product, Artifact, Pipeline,
    create_product, create_artifact, create_pipeline
)

# Import API routers
from api.products import router as products_router
from api.artifacts import router as artifacts_router
from api.pipelines import router as pipelines_router
from api.compatibility import router as compatibility_router
from api.explore import router as explore_router
from api.manifests import router as manifests_router
from api.schemas import router as schemas_router
from api.test_plans import router as test_plans_router
from api.modules import router as modules_router

# Initialize FastAPI app
app = FastAPI(
    title="Factory Control Plane API",
    description="Simplified API for managing Docker container products and pipelines",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage (will be replaced with database later)
products_db: Dict[str, Product] = {}
artifacts_db: Dict[str, Artifact] = {}
pipelines_db: Dict[str, Pipeline] = {}

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Factory Control Plane API",
        "version": "1.0.0",
        "description": "Simplified API for Docker container products and pipelines",
        "endpoints": {
            "products": "/products",
            "artifacts": "/artifacts",
            "pipelines": "/pipelines",
            "manifests": "/manifests",
            "schemas": "/schemas",
            "test-plans": "/test-plans",
            "modules": "/modules"
        }
    }

# Include API routers
app.include_router(products_router)
app.include_router(artifacts_router)
app.include_router(pipelines_router)
app.include_router(compatibility_router)
app.include_router(explore_router)
app.include_router(manifests_router)
app.include_router(schemas_router)
app.include_router(test_plans_router)
app.include_router(modules_router)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "control-plane"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
