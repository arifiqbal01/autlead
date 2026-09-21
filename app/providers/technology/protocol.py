from __future__ import annotations

from typing import Protocol

from app.models.schemas.technology import DetectedTechnology


class WebsiteTechnologyDetectionProvider(Protocol):
    """Provider interface for detecting technologies used by a website."""

    provider_name: str

    async def detect(
        self,
        website: str,
        *,
        timeout: int = 30,
    ) -> list[DetectedTechnology]:
        """Detect technologies used by the website."""
        ...