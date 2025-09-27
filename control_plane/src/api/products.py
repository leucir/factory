"""Product API endpoints backed by JSON configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from entities import Product

router = APIRouter(prefix="/products", tags=["products"])

PRODUCTS_PATH = Path(__file__).resolve().parents[2] / "data" / "product.json"


class ProductResponse(BaseModel):
    id: str
    name: str
    description: str
    docker_image_name: str
    docker_tag: str
    metadata: Dict[str, Any]


def _load_products() -> Dict[str, Dict[str, Any]]:
    if not PRODUCTS_PATH.exists():
        raise HTTPException(status_code=500, detail="Product store not configured")
    try:
        return json.loads(PRODUCTS_PATH.read_text())
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail="Invalid product store format") from exc


def _get_product(product_id: str) -> Product:
    products = _load_products()
    if product_id not in products:
        raise HTTPException(status_code=404, detail="Product not found")
    return Product.from_json(product_id, products[product_id])


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str) -> ProductResponse:
    """Fetch a product definition from the JSON store."""

    product = _get_product(product_id)
    return ProductResponse(**product.to_dict())
