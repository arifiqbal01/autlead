from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.models.schemas.crawling import CrawlRequest
from app.providers.crawling import crawl4ai_provider as crawl4ai_module
from app.providers.crawling.crawl4ai_provider import Crawl4AICrawlingProvider
from app.providers.crawling.exceptions import CrawlingProviderError


@pytest.mark.asyncio
async def test_crawl4ai_provider_with_real_discovery_data() -> None:
    """Crawl a real website URL obtained from business discovery."""

    request = CrawlRequest(
        url="https://rochatandartspraktijk.nl/",
        timeout=30,
    )

    provider = Crawl4AICrawlingProvider(
        headless=True,
        timeout_seconds=30,
    )

    result = await provider.crawl(request)

    assert result.url == request.url
    assert result.status_code == 200

    assert result.html
    assert len(result.html) > 100

    assert result.text
    assert len(result.text) > 100

    assert result.title
    assert isinstance(result.links, list)

    print(f"\nURL: {result.url}")
    print(f"Status: {result.status_code}")
    print(f"Title: {result.title}")
    print(f"Description: {result.meta_description}")
    print(f"Links: {len(result.links)}")
    print(f"HTML: {len(result.html)}")
    print(f"Text: {len(result.text)}")


@pytest.mark.asyncio
async def test_crawl4ai_provider_raises_on_crawl_failure() -> None:
    """Convert an unsuccessful Crawl4AI result into CrawlingProviderError."""

    request = CrawlRequest(
        url="https://example.com/",
        timeout=30,
    )

    provider = Crawl4AICrawlingProvider()

    failed_result = type(
        "FailedResult",
        (),
        {
            "success": False,
            "error_message": "Simulated crawl failure",
        },
    )()

    mock_crawler = AsyncMock()
    mock_crawler.arun.return_value = failed_result

    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_crawler
    mock_context.__aexit__.return_value = None

    with patch.object(
        crawl4ai_module,
        "AsyncWebCrawler",
        return_value=mock_context,
    ):
        with pytest.raises(
            CrawlingProviderError,
            match="Simulated crawl failure",
        ):
            await provider.crawl(request)

def test_extract_links_excludes_non_http_links() -> None:
    result = type(
        "Result",
        (),
        {
            "links": {
                "internal": [
                    {"href": "https://example.com/about"},
                    {"href": "http://example.com/contact"},
                    {"href": "tel:03277088881"},
                    {"href": "mailto:test@example.com"},
                    {"href": "#contact"},
                    {"href": ""},
                    {},
                ],
            },
        },
    )()

    links = Crawl4AICrawlingProvider._extract_links(result)

    assert links == [
        "https://example.com/about",
        "http://example.com/contact",
    ]