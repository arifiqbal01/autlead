from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.extract.websites.pages import extract_page_candidates
from app.models.schemas.crawling import WebsiteContent
from app.pipelines.common.website_crawl import crawl_website_page
from app.providers.crawling.crawl4ai_provider import (
    Crawl4AICrawlingProvider,
)
from app.transform.analysis.website_pages import (
    select_business_pages,
)


logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class WebsitePageCollectionResult:
    pages: list[WebsiteContent]
    selected: int
    crawled: int
    failed: int


async def collect_business_pages(
    *,
    session: AsyncSession,
    company_id: int,
    homepage: WebsiteContent,
    provider: Crawl4AICrawlingProvider,
    timeout: int = 30,
    limit: int = 5,
) -> WebsitePageCollectionResult:
    """
    Select, crawl, and persist useful internal business pages.

    The homepage is not crawled again.

    Selected pages may include:
    - team
    - people
    - leadership
    - management
    - about
    - contact
    """

    candidates = extract_page_candidates(
        links=[
            str(url)
            for url in homepage.links
        ],
    )

    selected_pages = select_business_pages(
        candidates,
        limit=limit,
    )

    pages = [homepage]

    crawled = 0
    failed = 0

    logger.info(
        "business_page_collection_started",
        company_id=company_id,
        candidates=len(candidates),
        selected=len(selected_pages),
    )

    for candidate in selected_pages:
        url = str(candidate.url)

        if url.rstrip("/") == str(homepage.url).rstrip("/"):
            continue

        try:
            result = await crawl_website_page(
                session=session,
                company_id=company_id,
                url=url,
                provider=provider,
                timeout=timeout,
            )

            pages.append(result.content)
            crawled += 1

        except Exception as exc:
            failed += 1

            logger.warning(
                "business_page_crawl_failed",
                company_id=company_id,
                url=url,
                error_type=type(exc).__name__,
                error=str(exc),
            )

    logger.info(
        "business_page_collection_completed",
        company_id=company_id,
        selected=len(selected_pages),
        crawled=crawled,
        failed=failed,
        total_pages=len(pages),
    )

    return WebsitePageCollectionResult(
        pages=pages,
        selected=len(selected_pages),
        crawled=crawled,
        failed=failed,
    )