from __future__ import annotations

import asyncio
import json
from typing import Any

from app.models.schemas.performance import WebsitePerformanceResult
from app.models.schemas.seo import WebsiteSeoResult
from app.providers.performance.protocol import (
    WebsitePerformanceProvider,
    WebsiteSeoProvider,
)


class LighthouseProvider(
    WebsitePerformanceProvider,
    WebsiteSeoProvider,
):
    """Lighthouse-based website performance and SEO provider."""

    source_name = "Lighthouse"
    source_type = "website_analysis"
    provider_name = "lighthouse"

    def __init__(
        self,
        *,
        image: str = "autlead-lighthouse",
        docker_command: str = "docker",
        timeout_seconds: int = 120,
        form_factor: str = "mobile",
    ) -> None:
        self.image = image
        self.docker_command = docker_command
        self.timeout_seconds = timeout_seconds
        self.form_factor = form_factor

    async def analyze_performance(
        self,
        website: str,
    ) -> WebsitePerformanceResult:
        report = await self._run(website)

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
        report = await self._run(website)

        return WebsiteSeoResult(
            seo_score=self._score(
                report,
                "seo",
            ),
        )

    async def _run(
        self,
        website: str,
    ) -> dict[str, Any]:
        command = self._build_command(website)

        stdout = await self._execute(command)

        try:
            report = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Lighthouse returned invalid JSON"
            ) from exc

        if not isinstance(report, dict):
            raise RuntimeError(
                "Lighthouse returned an invalid report"
            )

        return report

    def _build_command(
        self,
        website: str,
    ) -> list[str]:
        return [
            self.docker_command,
            "run",
            "--rm",
            self.image,
            website,
            "--output=json",
            "--output-path=stdout",
            "--quiet",
            f"--form-factor={self.form_factor}",
            "--only-categories=performance,seo",
        ]

    async def _execute(
        self,
        command: list[str],
    ) -> str:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise

        if process.returncode != 0:
            error = stderr.decode(
                errors="replace",
            ).strip()

            if not error:
                error = stdout.decode(
                    errors="replace",
                ).strip()

            raise RuntimeError(
                "Lighthouse failed with exit code "
                f"{process.returncode}: {error}"
            )

        return stdout.decode(
            errors="replace",
        )

    @staticmethod
    def _score(
        report: dict[str, Any],
        category: str,
    ) -> int | None:
        categories = report.get("categories")

        if not isinstance(categories, dict):
            return None

        category_data = categories.get(category)

        if not isinstance(category_data, dict):
            return None

        score = category_data.get("score")

        if not isinstance(score, (int, float)):
            return None

        return round(score * 100)