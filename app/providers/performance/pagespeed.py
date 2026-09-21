from __future__ import annotations

from typing import Any

import httpx

from app.models.schemas.performance import WebsitePerformanceResult
from app.models.schemas.seo import WebsiteSeoResult
from app.providers.performance.protocol import (
    WebsitePerformanceProvider,
    WebsiteSeoProvider,
)


class PageSpeedProvider(
    WebsitePerformanceProvider,
    WebsiteSeoProvider,
):
    """Analyze website performance and SEO using Google PageSpeed Insights."""

    source_name = "PageSpeed Insights"
    source_type = "website_analysis"
    provider_name = "pagespeed"

    endpoint = (
        "https://www.googleapis.com/"
        "pagespeedonline/v5/runPagespeed"
    )

    def __init__(
        self,
        *,
        api_key: str | None = None,
        strategy: str = "mobile",
        timeout_seconds: int = 120,
    ) -> None:
        if strategy not in {"mobile", "desktop"}:
            raise ValueError(
                "strategy must be 'mobile' or 'desktop'"
            )

        self.api_key = api_key
        self.strategy = strategy
        self.timeout_seconds = timeout_seconds

    async def analyze_performance(
        self,
        website: str,
    ) -> WebsitePerformanceResult:
        report = await self._run(
            website,
            category="performance",
        )

        return WebsitePerformanceResult(
            performance_score=self._score(
                report,
                "performance",
            ),
        )

    async def analyze_seo(
        self,
        website: str,
    ) -> WebsiteSeoResult:
        report = await self._run(
            website,
            category="seo",
        )

        return WebsiteSeoResult(
            seo_score=self._score(
                report,
                "seo",
            ),
        )

    async def _run(
        self,
        website: str,
        *,
        category: str,
    ) -> dict[str, Any]:
        params: dict[str, str] = {
            "url": website,
            "category": category,
            "strategy": self.strategy,
        }

        if self.api_key:
            params["key"] = self.api_key

        timeout = httpx.Timeout(
            self.timeout_seconds,
        )

        try:
            async with httpx.AsyncClient(
                timeout=timeout,
            ) as client:
                response = await client.get(
                    self.endpoint,
                    params=params,
                )
        except httpx.TimeoutException as exc:
            raise RuntimeError(
                "PageSpeed Insights request timed out"
            ) from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(
                "PageSpeed Insights request failed"
            ) from exc

        if response.status_code != 200:
            detail = response.text.strip()

            raise RuntimeError(
                "PageSpeed Insights failed with HTTP status "
                f"{response.status_code}: {detail}"
            )

        try:
            report: Any = response.json()
        except ValueError as exc:
            raise RuntimeError(
                "PageSpeed Insights returned invalid JSON"
            ) from exc

        if not isinstance(report, dict):
            raise RuntimeError(
                "PageSpeed Insights returned an invalid report"
            )

        return report

    @staticmethod
    def _score(
        report: dict[str, Any],
        category: str,
    ) -> int | None:
        lighthouse_result = report.get(
            "lighthouseResult",
        )

        if not isinstance(
            lighthouse_result,
            dict,
        ):
            return None

        categories = lighthouse_result.get(
            "categories",
        )

        if not isinstance(categories, dict):
            return None

        category_data = categories.get(category)

        if not isinstance(category_data, dict):
            return None

        score = category_data.get("score")

        if not isinstance(score, (int, float)):
            return None

        return round(score * 100)