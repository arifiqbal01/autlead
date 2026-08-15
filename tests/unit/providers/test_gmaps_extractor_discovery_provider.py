from typing import Self

import pytest

from app.models.schemas import DiscoveryQuery
from app.providers.discovery import (
    BusinessDiscoveryProviderError,
    GoogleMapsExtractorDiscoveryProvider,
)


class FakeGMapsExtractor:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def async_collect_v2(self, *args: object, **kwargs: object) -> list[dict[str, object]]:
        self.args = args
        self.collect_kwargs = kwargs
        return [
            {
                "name": "Example Agency",
                "website": "https://example.com",
                "phone": "+31 20 000 0000",
                "address": "Example Street 1, Amsterdam",
                "category": "Marketing agency",
                "place_id": "place-1",
            },
            {
                "name": "Second Agency",
                "place_id": "place-2",
            },
        ]


async def test_gmaps_extractor_provider_maps_external_businesses_to_records() -> None:
    provider = GoogleMapsExtractorDiscoveryProvider(
        workers=2,
        extractor_factory=FakeGMapsExtractor,
    )

    records = await provider.discover(
        DiscoveryQuery(
            query="marketing agencies",
            location="Amsterdam",
            limit=1,
        )
    )

    assert len(records) == 1
    assert records[0].name == "Example Agency"
    assert records[0].website == "https://example.com"
    assert records[0].source_name == "Google Maps"
    assert records[0].source_type == "business_discovery"
    assert records[0].provider_name == "gmaps_extractor"
    assert records[0].external_id == "place-1"
    assert records[0].raw_data is not None
    assert records[0].raw_data["category"] == "Marketing agency"


async def test_gmaps_extractor_provider_requires_location() -> None:
    provider = GoogleMapsExtractorDiscoveryProvider(extractor_factory=FakeGMapsExtractor)

    with pytest.raises(BusinessDiscoveryProviderError, match="location"):
        await provider.discover(DiscoveryQuery(query="marketing agencies"))
