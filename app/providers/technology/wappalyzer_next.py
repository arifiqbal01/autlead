from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from typing import Any

from app.models.schemas.technology import DetectedTechnology


class WappalyzerTechnologyDetectionProvider:
    """Detect website technologies using Wappalyzer in Docker."""

    provider_name = "wappalyzer"

    def __init__(
        self,
        *,
        image: str = "autlead-wappalyzer",
        docker_command: str = "docker",
        scan_type: str = "full",
        timeout_seconds: int = 30,
    ) -> None:
        self.image = image
        self.docker_command = docker_command
        self.scan_type = scan_type
        self.timeout_seconds = timeout_seconds

    async def detect(
        self,
        website: str,
        *,
        timeout: int | None = None,
    ) -> list[DetectedTechnology]:
        scan_timeout = (
            timeout
            if timeout is not None
            else self.timeout_seconds
        )

        command = self._build_command(
            website=website,
            timeout=scan_timeout,
        )

        output = await self._run(
            command,
            timeout=scan_timeout,
        )

        return self._parse_output(
            output,
            website=website,
        )

    def _build_command(
        self,
        *,
        website: str,
        timeout: int,
    ) -> list[str]:
        return [
            self.docker_command,
            "run",
            "--rm",
            self.image,
            "-i",
            website,
            "--scan-type",
            self.scan_type,
            "-t",
            str(timeout),
            "-oJ",
            "-",
        ]

    async def _run(
        self,
        command: list[str],
        *,
        timeout: int,
    ) -> str:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
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
                "Wappalyzer failed with exit code "
                f"{process.returncode}: {error}"
            )

        return stdout.decode(
            errors="replace",
        )

    @staticmethod
    def _parse_output(
        output: str,
        *,
        website: str,
    ) -> list[DetectedTechnology]:
        try:
            data: Any = json.loads(output)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Wappalyzer returned invalid JSON"
            ) from exc

        if not isinstance(data, Mapping):
            raise RuntimeError(
                "Wappalyzer returned an invalid result"
            )

        technologies = data.get(website, {})

        if not isinstance(technologies, Mapping):
            return []

        results: list[DetectedTechnology] = []

        for name, details in technologies.items():
            if not isinstance(name, str):
                continue

            if not isinstance(details, Mapping):
                continue

            version = details.get("version")

            if version is not None and not isinstance(version, str):
                version = str(version)

            confidence = details.get(
                "confidence",
                100,
            )

            if not isinstance(confidence, (int, float)):
                confidence = 100

            categories = details.get(
                "categories",
                [],
            )

            if not isinstance(categories, list):
                categories = []

            categories = [
                category
                for category in categories
                if isinstance(category, str)
            ]

            groups = details.get(
                "groups",
                [],
            )

            if not isinstance(groups, list):
                groups = []

            groups = [
                group
                for group in groups
                if isinstance(group, str)
            ]

            results.append(
                DetectedTechnology(
                    name=name,
                    version=version,
                    confidence=int(confidence),
                    categories=categories,
                    groups=groups,
                )
            )

        return results