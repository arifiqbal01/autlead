# app/providers/discovery/gosom_import.py

from __future__ import annotations

from pathlib import Path

from app.models.schemas import BusinessRecord, DiscoveryQuery
from app.providers.discovery.gosom import (
    GosomGoogleMapsDiscoveryProvider,
)


class GosomResultsFileDiscoveryProvider:
    """
    Discovery provider backed by an existing Gosom results.csv.

    Allows historical Gosom output to pass through the normal
    discovery pipeline without running the scraper again.
    """

    source_name = "Google Maps"
    source_type = "business_discovery"
    provider_name = "gosom_google_maps"

    def __init__(
        self,
        *,
        results_file: str | Path,
    ) -> None:
        self.results_file = (
            Path(results_file)
            .expanduser()
            .resolve()
        )

        self._gosom = GosomGoogleMapsDiscoveryProvider()

    async def discover(
        self,
        query: DiscoveryQuery,
    ) -> list[BusinessRecord]:
        return await self._gosom.load_results(
            results_file=self.results_file,
            query=query,
        )