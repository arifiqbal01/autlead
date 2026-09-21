from __future__ import annotations

import pytest

from app.models.schemas import DiscoveryQuery
from app.models.schemas.crawling import CrawlRequest
from app.providers.crawling.crawl4ai_provider import Crawl4AICrawlingProvider
from app.providers.crawling.exceptions import CrawlingProviderError
from app.providers.discovery.gosom import GosomGoogleMapsDiscoveryProvider


@pytest.mark.asyncio
@pytest.mark.integration
async def test_discovery_to_crawling_with_10_businesses() -> None:
    """Discover 10 real businesses and crawl their websites."""

    discovery_query = DiscoveryQuery(
        query="dentists",
        location="Lahore, Pakistan",
        limit=10,
    )

    discovery_provider = GosomGoogleMapsDiscoveryProvider()

    businesses = await discovery_provider.discover(discovery_query)

    assert businesses, "Discovery returned no businesses."

    businesses_with_websites = [
        business
        for business in businesses
        if business.website
    ]

    assert len(businesses_with_websites) >= 10, (
        f"Discovery returned only {len(businesses_with_websites)} "
        "businesses with websites."
    )

    businesses = businesses_with_websites[:10]

    crawling_provider = Crawl4AICrawlingProvider(
        headless=True,
        timeout_seconds=30,
    )

    successful = 0
    failed = 0

    for business in businesses:
        assert business.name
        assert business.website

        print(f"\n{'=' * 80}")
        print(f"Business: {business.name}")
        print(f"Website: {business.website}")

        try:
            request = CrawlRequest(
                url=business.website,
                timeout=30,
            )

            result = await crawling_provider.crawl(request)

        except CrawlingProviderError as exc:
            failed += 1
            print(f"Crawl failed: {exc}")
            continue

        successful += 1

        print(f"Status: {result.status_code}")
        print(f"Title: {result.title}")
        print(f"Description: {result.meta_description}")
        print(f"Links: {len(result.links)}")
        print(f"HTML: {len(result.html or '')}")
        print(f"Text: {len(result.text or '')}")

        assert str(result.url) == business.website
        assert result.status_code is not None
        assert result.html
        assert result.text

    print(f"\n{'=' * 80}")
    print(f"Businesses tested: {len(businesses)}")
    print(f"Successful crawls: {successful}")
    print(f"Failed crawls: {failed}")

    assert successful > 0, "None of the discovered websites could be crawled."