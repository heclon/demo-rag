from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    author: str
    rating: float
    title: str
    body: str
    created_at: dt.datetime


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    category: str
    brand: str
    price: float
    rating: float
    inventory: int
    specifications: dict[str, str]
    created_at: dt.datetime


class ProductWithReviewsOut(ProductOut):
    reviews: list[ReviewOut] = []


class ProductListOut(BaseModel):
    items: list[ProductOut]
    total: int
    limit: int
    offset: int
