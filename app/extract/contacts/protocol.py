from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.models.schemas.crawling import WebsiteContent

from app.models.schemas.contacts import ContactExtractionResult


class ContactExtractor(Protocol):
    """Contract for contact extraction from crawled website content."""

    def extract(
        self,
        pages: Sequence[WebsiteContent],
    ) -> ContactExtractionResult:
        """Extract structured contact evidence."""
        ...