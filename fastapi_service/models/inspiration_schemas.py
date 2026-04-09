from typing import List

from pydantic import BaseModel, Field


class TrendingBook(BaseModel):
    """Single trending book data."""
    title: str = Field(..., min_length=1, max_length=200)
    synopsis: str = Field(default="", max_length=5000)
    tags: List[str] = Field(default_factory=list)
    hot_score: float = Field(default=0.0, ge=0)


class InspirationGenerateRequest(BaseModel):
    """Request to generate inspiration from trending books."""
    trending_books: List[TrendingBook] = Field(..., min_items=1, max_items=50)
    genre_preference: str = Field(default="", max_length=100)


class CustomInspirationRequest(BaseModel):
    """Request to generate custom inspirations from user prompt."""
    custom_prompt: str = Field(..., min_length=1, max_length=2000)
    count: int = Field(default=3, ge=1, le=10)


class GeneratedInspiration(BaseModel):
    """AI-generated novel inspiration."""
    title: str
    synopsis: str
    genre: str
    selling_points: List[str]
    target_audience: str
    estimated_popularity: float


class InspirationGenerateResponse(BaseModel):
    """Response containing generated inspirations."""
    inspirations: List[GeneratedInspiration]
    analysis_summary: str
