# app/providers/crawling/protocol.py

from typing import Protocol

from app.models.schemas.crawling import CrawlRequest, WebsiteContent


class CrawlingProvider(Protocol):
    """Contract for providers that retrieve website content."""

    async def crawl(
        self,
        request: CrawlRequest,
    ) -> WebsiteContent:
        """Crawl a website and return structured website content."""
        ...