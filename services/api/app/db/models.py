"""SQLAlchemy ORM models mirroring app/db/schema.sql."""

from __future__ import annotations

import datetime as dt

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.config import get_settings

settings = get_settings()


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(Text)
    brand: Mapped[str] = mapped_column(Text)
    price: Mapped[float] = mapped_column(Numeric(10, 2))
    rating: Mapped[float] = mapped_column(Numeric(2, 1))
    inventory: Mapped[int]
    specifications: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(default=dt.datetime.utcnow)

    reviews: Mapped[list[Review]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    author: Mapped[str] = mapped_column(Text)
    rating: Mapped[float] = mapped_column(Numeric(2, 1))
    title: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(default=dt.datetime.utcnow)

    product: Mapped[Product] = relationship(back_populates="reviews")


class Embedding(Base):
    __tablename__ = "embeddings"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    source_type: Mapped[str] = mapped_column(Text)  # description | specifications | review
    source_id: Mapped[int | None]
    chunk_text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.embedding_dimensions))
    created_at: Mapped[dt.datetime] = mapped_column(default=dt.datetime.utcnow)
