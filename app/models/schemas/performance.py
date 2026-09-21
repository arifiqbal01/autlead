from __future__ import annotations

from pydantic import BaseModel, Field


class WebsitePerformanceResult(BaseModel):
    """Performance analysis result for a website."""

    performance_score: int | None = Field(
        default=None,
        ge=0,
        le=100,
    )
    first_contentful_paint_ms: float | None = None
    largest_contentful_paint_ms: float | None = None
    cumulative_layout_shift: float | None = None
    total_blocking_time_ms: float | None = None
    speed_index_ms: float | None = None