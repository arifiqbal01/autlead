from __future__ import annotations

from typing import Protocol

from app.models.schemas.performance import WebsitePerformanceResult
from app.models.schemas.seo import WebsiteSeoResult


class WebsitePerformanceProvider(Protocol):
    provider_name: str

    async def analyze_performance(
        self,
        website: str,
    ) -> WebsitePerformanceResult:
        ...


class WebsiteSeoProvider(Protocol):
    provider_name: str

    async def analyze_seo(
        self,
        website: str,
    ) -> WebsiteSeoResult:
        ...