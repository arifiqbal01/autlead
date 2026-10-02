from __future__ import annotations

import asyncio
import json
import uuid
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
        hard_timeout_grace_seconds: int = 15,
        memory_limit: str = "1g",
        cpu_limit: str = "1",
    ) -> None:
        self.image = image
        self.docker_command = docker_command
        self.scan_type = scan_type
        self.timeout_seconds = timeout_seconds
        self.hard_timeout_grace_seconds = hard_timeout_grace_seconds
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit

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
        hard_timeout = scan_timeout + self.hard_timeout_grace_seconds

        container_name = (
            f"autlead-wappalyzer-{uuid.uuid4().hex}"
        )

        command = self._build_command(
            website=website,
            timeout=scan_timeout,
            container_name=container_name,
        )

        output = await self._run(
            command,
            container_name=container_name,
            timeout=hard_timeout,
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
        container_name: str,
    ) -> list[str]:
        return [
            self.docker_command,
            "run",
            "--rm",
            "--name",
            container_name,
            "--memory",
            self.memory_limit,
            "--memory-swap",
            self.memory_limit,
            "--cpus",
            self.cpu_limit,
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
        container_name: str,
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
        except (TimeoutError, asyncio.CancelledError):
            await self._terminate_process(process)
            await self._remove_container(container_name)
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
    async def _terminate_process(
        process: asyncio.subprocess.Process,
    ) -> None:
        if process.returncode is not None:
            return

        try:
            process.kill()
        except ProcessLookupError:
            return

        await process.wait()

    async def _remove_container(
        self,
        container_name: str,
    ) -> None:
        """
        Force-remove the Wappalyzer container.

        Killing the local `docker run` process does not guarantee that the
        container created by Docker Engine is stopped. Explicit cleanup
        prevents orphaned Playwright/Chromium containers after timeouts or
        cancellation.
        """
        try:
            cleanup = await asyncio.create_subprocess_exec(
                self.docker_command,
                "rm",
                "-f",
                container_name,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )

            await asyncio.wait_for(
                cleanup.wait(),
                timeout=10,
            )
        except (TimeoutError, FileNotFoundError, OSError):
            # Cleanup is best-effort. Preserve the original timeout or
            # cancellation rather than replacing it with a cleanup failure.
            return

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
            raise TypeError(
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