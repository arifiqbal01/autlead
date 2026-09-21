# app/models/schemas/crawling.py

from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl


class CrawlRequest(BaseModel):
    """Request to crawl a website."""

    url: HttpUrl
    timeout: int = Field(default=30, gt=0)


class WebsiteContent(BaseModel):
    """Structured result returned by a crawling provider."""

    url: HttpUrl
    status_code: int | None = None
    html: str | None = None
    text: str | None = None
    title: str | None = None
    meta_description: str | None = None
    links: list[HttpUrl] = Field(default_factory=list)
    collected_at: datetime