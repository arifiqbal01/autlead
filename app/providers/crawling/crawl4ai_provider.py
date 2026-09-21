# app/providers/crawling/crawl4ai_provider.py

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CacheMode,
    CrawlerRunConfig,
)
from crawl4ai.async_crawler_strategy import (
    AsyncPlaywrightCrawlerStrategy,
)
from crawl4ai.browser_adapter import UndetectedAdapter

from app.core.logging import get_logger
from app.models.schemas.crawling import (
    CrawlRequest,
    WebsiteContent,
)
from app.providers.crawling.exceptions import (
    CrawlingProviderError,
)


logger = get_logger(__name__)


class Crawl4AICrawlingProvider:
    """
    Crawl website pages using Crawl4AI.

    The provider is:

    - asynchronous
    - safe to share across concurrent pipeline workers
    - bounded by an internal concurrency semaphore
    - independent from PostgreSQL/session state
    - independent from WebArtsy business logic

    Each crawl creates its own crawler lifecycle so concurrent calls
    do not share mutable browser/page state.
    """

    provider_name = "crawl4ai"
    source_name = "Website"
    source_type = "website_crawling"

    def __init__(
        self,
        *,
        headless: bool = True,
        concurrency: int = 5,
    ) -> None:
        if concurrency < 1:
            raise ValueError(
                "Crawl concurrency must be at least 1."
            )

        self.headless = headless
        self.concurrency = concurrency

        self._semaphore = asyncio.Semaphore(
            concurrency,
        )

    async def crawl(
        self,
        request: CrawlRequest,
    ) -> WebsiteContent:
        """
        Crawl one URL and return normalized WebsiteContent.

        Multiple calls may run concurrently. Actual browser concurrency
        is bounded by ``self.concurrency``.

        Persistence and transaction management belong to the caller.
        """

        url = str(request.url)

        logger.info(
            "crawl4ai_crawl_requested",
            url=url,
            timeout=request.timeout,
        )

        async with self._semaphore:
            return await self._crawl(
                request=request,
            )

    async def _crawl(
        self,
        *,
        request: CrawlRequest,
    ) -> WebsiteContent:
        """
        Execute one isolated Crawl4AI operation.

        This method runs only after a concurrency slot has been acquired.
        """

        url = str(request.url)

        browser_config = BrowserConfig(
            headless=self.headless,
        )

        crawl_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            page_timeout=request.timeout * 1000,
        )

        crawler_strategy = AsyncPlaywrightCrawlerStrategy(
            browser_config=browser_config,
            browser_adapter=UndetectedAdapter(),
        )

        logger.info(
            "crawl4ai_crawl_started",
            url=url,
            concurrency=self.concurrency,
        )

        try:
            async with AsyncWebCrawler(
                crawler_strategy=crawler_strategy,
            ) as crawler:
                result = await crawler.arun(
                    url=url,
                    config=crawl_config,
                )

        except asyncio.CancelledError:
            logger.warning(
                "crawl4ai_crawl_cancelled",
                url=url,
            )

            raise

        except Exception as exc:
            logger.error(
                "crawl4ai_crawl_failed",
                url=url,
                error_type=type(exc).__name__,
                error=str(exc),
            )

            raise CrawlingProviderError(
                f"Failed to crawl {url}"
            ) from exc

        if not result.success:
            error_message = getattr(
                result,
                "error_message",
                None,
            )

            if not error_message:
                error_message = (
                    "Crawl4AI returned an unsuccessful result."
                )

            logger.warning(
                "crawl4ai_crawl_unsuccessful",
                url=url,
                error_message=error_message,
            )

            raise CrawlingProviderError(
                error_message
            )

        content = self._to_website_content(
            request=request,
            result=result,
        )

        logger.info(
            "crawl4ai_crawl_completed",
            url=url,
            status_code=content.status_code,
            html_chars=len(content.html or ""),
            text_chars=len(content.text or ""),
            links=len(content.links),
        )

        return content

    def _to_website_content(
        self,
        *,
        request: CrawlRequest,
        result: Any,
    ) -> WebsiteContent:
        """
        Convert provider-specific Crawl4AI output into Autlead's
        WebsiteContent boundary model.
        """

        metadata = result.metadata or {}

        markdown = result.markdown

        return WebsiteContent(
            url=request.url,
            status_code=result.status_code,
            html=result.cleaned_html,
            text=(
                markdown.raw_markdown
                if markdown
                else None
            ),
            title=metadata.get("title"),
            meta_description=metadata.get(
                "description"
            ),
            links=self._extract_links(result),
            collected_at=datetime.now(UTC),
        )

    @staticmethod
    def _extract_links(
        result: Any,
    ) -> list[str]:
        """
        Extract unique internal HTTP(S) links.

        These links may later be ranked by the pipeline for additional
        crawling, e.g. team/about/leadership/contact pages.
        """

        found: list[str] = []
        seen: set[str] = set()

        result_links = result.links or {}

        for link in result_links.get(
            "internal",
            [],
        ):
            href = link.get("href")

            if not href:
                continue

            href = str(href).strip()

            if not href.startswith(
                ("http://", "https://")
            ):
                continue

            if href in seen:
                continue

            seen.add(href)
            found.append(href)

        return found