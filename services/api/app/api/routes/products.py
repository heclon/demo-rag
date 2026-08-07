from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession
from app.db.models import Product
from app.schemas.products import ProductListOut, ProductOut, ProductWithReviewsOut

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=ProductListOut, summary="List products with optional filters")
def list_products(
    db: DbSession,
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    category: str | None = None,
    brand: str | None = None,
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    min_rating: float | None = Query(default=None, ge=0, le=5),
    q: str | None = Query(default=None, description="Simple substring match on title/description"),
) -> ProductListOut:
    stmt = select(Product)
    count_stmt = select(func.count()).select_from(Product)

    filters = []
    if category:
        filters.append(Product.category.ilike(f"%{category}%"))
    if brand:
        filters.append(Product.brand.ilike(f"%{brand}%"))
    if min_price is not None:
        filters.append(Product.price >= min_price)
    if max_price is not None:
        filters.append(Product.price <= max_price)
    if min_rating is not None:
        filters.append(Product.rating >= min_rating)
    if q:
        filters.append(Product.title.ilike(f"%{q}%") | Product.description.ilike(f"%{q}%"))

    for f in filters:
        stmt = stmt.where(f)
        count_stmt = count_stmt.where(f)

    total = db.execute(count_stmt).scalar_one()
    items = db.execute(stmt.order_by(Product.id).limit(limit).offset(offset)).scalars().all()

    return ProductListOut(
        items=[ProductOut.model_validate(p) for p in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/categories", response_model=list[str], summary="Distinct categories (for filter UI)")
def list_categories(db: DbSession) -> list[str]:
    return list(
        db.execute(select(Product.category).distinct().order_by(Product.category)).scalars().all()
    )


@router.get("/brands", response_model=list[str], summary="Distinct brands (for filter UI)")
def list_brands(db: DbSession) -> list[str]:
    return list(
        db.execute(select(Product.brand).distinct().order_by(Product.brand)).scalars().all()
    )


@router.get(
    "/{product_id}",
    response_model=ProductWithReviewsOut,
    summary="Get one product with its reviews",
)
def get_product(product_id: int, db: DbSession) -> ProductWithReviewsOut:
    product = db.execute(
        select(Product).where(Product.id == product_id).options(selectinload(Product.reviews))
    ).scalar_one_or_none()
    if product is None:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return ProductWithReviewsOut.model_validate(product)
