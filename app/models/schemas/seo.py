from __future__ import annotations

from pydantic import BaseModel, Field


class WebsiteSeoResult(BaseModel):
    """SEO analysis result for a website."""

    seo_score: int | None = Field(
        default=None,
        ge=0,
        le=100,
    )