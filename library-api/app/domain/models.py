"""
models.py - Pydantic domain models for book data
Used for request validation (BookCreate) and response serialization (BookResponse, BookListResponse)
"""
from pydantic import BaseModel, Field, field_validator


class BookCreate(BaseModel):
    """Validation model for creating or updating a book.
    Enforces: title required and non-empty, price > 0, rating 1-5.
    """
    title: str
    category: str | None = None
    price: float = Field(gt=0, description="Price must be greater than 0")
    rating: int = Field(ge=1, le=5, description="Rating must be between 1 and 5")

    @field_validator('title')
    @classmethod
    def title_must_not_be_empty(cls, v):
        """Strip whitespace and reject empty titles."""
        if not v or not v.strip():
            raise ValueError('Title is required and cannot be empty')
        return v.strip()


class BookResponse(BaseModel):
    """Response model for a single book."""
    id: int
    title: str
    category: str | None
    price: float
    rating: int


class BookListResponse(BaseModel):
    """Response model for a book in list context (same fields as BookResponse)."""
    id: int
    title: str
    category: str | None
    price: float
    rating: int
