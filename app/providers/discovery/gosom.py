from __future__ import annotations

import asyncio
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.models.schemas import BusinessRecord, DiscoveryQuery
from app.providers.discovery.exceptions import BusinessDiscoveryProviderError
from app.providers.discovery.gosom_utils import (
    deduplicate,
    extract_domain,
    optional_text,
    parse_location,
    read_results,
    required_text,
)


class GosomGoogleMapsDiscoveryProvider:
    source_name = "Google Maps"
    source_type = "business_discovery"
    provider_name = "gosom_google_maps"

    def __init__(
        self,
        *,
        image: str = "gosom/google-maps-scraper",
        concurrency: int = 1,
        depth: int = 1,
        zoom: int = 15,
        grid_bbox: str | None = None,
        grid_cell_km: float = 5.0,
        proxy: str | None = None,
        docker_command: str = "docker",
        timeout_seconds: int = 600,
    ) -> None:
        self.image = image
        self.concurrency = concurrency
        self.depth = depth
        self.zoom = zoom
        self.grid_bbox = grid_bbox
        self.grid_cell_km = grid_cell_km
        self.proxy = proxy
        self.docker_command = docker_command
        self.timeout_seconds = timeout_seconds

    async def discover(
        self,
        query: DiscoveryQuery,
    ) -> list[BusinessRecord]:
        area = required_text(query.location, "location")

        with tempfile.TemporaryDirectory(
            prefix="autlead-gosom-"
        ) as temp_dir:
            work_dir = Path(temp_dir)
            queries_file = work_dir / "queries.txt"
            results_file = work_dir / "results.csv"

            queries_file.write_text(
                f"{query.query} in {area}\n",
                encoding="utf-8",
            )

            command = self._build_command(
                queries_file=queries_file,
                results_file=results_file,
            )

            try:
                await self._run(
                    command,
                    cwd=work_dir,
                )
            except asyncio.TimeoutError as exc:
                raise BusinessDiscoveryProviderError(
                    "Google Maps discovery timed out"
                ) from exc
            except OSError as exc:
                raise BusinessDiscoveryProviderError(
                    "Could not start Gosom Google Maps scraper"
                ) from exc
            except RuntimeError as exc:
                raise BusinessDiscoveryProviderError(
                    "Gosom Google Maps discovery failed"
                ) from exc

            if not results_file.exists():
                raise BusinessDiscoveryProviderError(
                    "Gosom completed without producing a results file"
                )

            businesses = read_results(results_file)

        businesses = deduplicate(businesses)

        return [
            self._to_business_record(
                business,
                query,
            )
            for business in businesses[:query.limit]
        ]

    def _build_command(
        self,
        *,
        queries_file: Path,
        results_file: Path,
    ) -> list[str]:
        command = [
            self.docker_command,
            "run",
            "--rm",
            "-v",
            f"{queries_file}:/queries.txt:ro",
            "-v",
            f"{results_file.parent}:/out",
            self.image,
            "-input",
            "/queries.txt",
            "-results",
            "/out/results.csv",
            "-depth",
            str(self.depth),
            "-c",
            str(self.concurrency),
            "-exit-on-inactivity",
            "3m",
        ]

        if self.grid_bbox:
            command.extend(
                [
                    "-grid-bbox",
                    self.grid_bbox,
                    "-grid-cell",
                    str(self.grid_cell_km),
                    "-zoom",
                    str(self.zoom),
                ]
            )

        if self.proxy:
            command.extend(
                [
                    "-proxies",
                    self.proxy,
                ]
            )

        return command

    async def _run(
        self,
        command: list[str],
        *,
        cwd: Path,
    ) -> None:
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=cwd,
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
                errors="replace"
            ).strip()

            if not error:
                error = stdout.decode(
                    errors="replace"
                ).strip()

            raise RuntimeError(
                f"Gosom exited with code "
                f"{process.returncode}: {error}"
            )

    def _to_business_record(
        self,
        business: Mapping[str, Any],
        query: DiscoveryQuery,
    ) -> BusinessRecord:
        name = required_text(
            business.get("title"),
            "title",
        )

        website = optional_text(
            business.get("website"),
        )

        address = optional_text(
            business.get("address")
            or business.get("complete_address")
        )

        city, country = parse_location(
            optional_text(query.location)
        )

        return BusinessRecord(
            name=name,
            website=website,
            domain=extract_domain(website),
            phone=optional_text(
                business.get("phone")
            ),
            country=country,
            city=city,
            address=address,
            category=optional_text(
                business.get("category")
            ),
            source_name=self.source_name,
            source_type=self.source_type,
            provider_name=self.provider_name,
            external_id=optional_text(
                business.get("place_id")
                or business.get("cid")
                or business.get("link")
            ),
            raw_data=dict(business),
        )