from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.persistence.website_crawl import WebsiteCrawl
from app.models.persistence.website_crawl_link import WebsiteCrawlLink
from app.models.persistence.website_crawl_state import WebsiteCrawlState
from app.models.schemas import DiscoveryQuery
from app.pipelines.common.website_crawl import analyze_website
from app.providers.crawling.crawl4ai_provider import Crawl4AICrawlingProvider
from app.providers.discovery.gosom import GosomGoogleMapsDiscoveryProvider


@pytest.mark.asyncio
@pytest.mark.integration
async def test_discovery_to_website_analysis(session, company) -> None:
    """Discover a real business and run the complete website analysis flow."""

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

    assert businesses_with_websites, (
        "Discovery returned no businesses with websites."
    )

    business = businesses_with_websites[0]

    assert business.name
    assert business.website

    print(f"\n{'=' * 80}")
    print(f"Business: {business.name}")
    print(f"Website: {business.website}")

    # Use the existing test Company but replace its website
    # with the real website discovered by Gosom.
    company.name = business.name
    company.normalized_name = business.name.lower()
    company.website = str(business.website)

    session.add(company)
    await session.flush()

    crawling_provider = Crawl4AICrawlingProvider(
        headless=True,
        timeout_seconds=30,
    )

    result = await analyze_website(
        session,
        company_id=company.id,
        website=str(business.website),
        provider=crawling_provider,
        retention_days=30,
        timeout=30,
    )

    assert result.crawled is True
    assert str(result.content.url) == str(business.website)
    assert result.content.status_code is not None
    assert result.content.html
    assert result.content.text

    print(f"Status: {result.content.status_code}")
    print(f"Title: {result.content.title}")
    print(f"Description: {result.content.meta_description}")
    print(f"Links: {len(result.content.links)}")
    print(f"HTML: {len(result.content.html or '')}")
    print(f"Text: {len(result.content.text or '')}")

    state = await session.scalar(
        select(WebsiteCrawlState).where(
            WebsiteCrawlState.company_id == company.id,
        )
    )

    assert state is not None
    assert state.status == "completed"
    assert state.last_crawl_id is not None
    assert state.completed_at is not None

    crawl = await session.get(
        WebsiteCrawl,
        state.last_crawl_id,
    )

    assert crawl is not None
    assert crawl.company_id == company.id
    assert crawl.status_code == result.content.status_code
    assert crawl.html == result.content.html
    assert crawl.text == result.content.text
    assert crawl.title == result.content.title
    assert crawl.meta_description == result.content.meta_description
    assert crawl.provider_name == "crawl4ai"
    assert crawl.content_hash is not None

    links = list(
        (
            await session.scalars(
                select(WebsiteCrawlLink.url).where(
                    WebsiteCrawlLink.website_crawl_id == crawl.id,
                )
            )
        ).all()
    )

    assert len(links) == len(result.content.links)

    print(f"Persisted crawl ID: {crawl.id}")
    print(f"Persisted links: {len(links)}")

    # Run the analysis again. The existing crawl should be reused
    # because it is fresh according to the retention policy.
    second_result = await analyze_website(
        session,
        company_id=company.id,
        website=str(business.website),
        provider=crawling_provider,
        retention_days=30,
        timeout=30,
    )

    assert second_result.crawled is False
    assert str(second_result.content.url) == str(result.content.url)
    assert second_result.content.status_code == result.content.status_code
    assert second_result.content.html == result.content.html
    assert second_result.content.text == result.content.text
    assert second_result.content.title == result.content.title
    assert second_result.content.meta_description == result.content.meta_description
    assert second_result.content.links == result.content.links

    print("Second analysis reused the fresh persisted crawl.")

    print(f"\n{'=' * 80}")
    print("Website analysis integration test passed.")
