from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.load.postgres.website_crawls import (
    get_last_website_crawl,
    get_website_crawl_content,
    load_website_crawl,
)
from app.models.schemas.crawling import (
    CrawlRequest,
    WebsiteContent,
)
from app.policies.retention.website_crawl import (
    WebsiteCrawlRetentionContext,
    should_recrawl_website,
)
from app.providers.crawling.crawl4ai_provider import (
    Crawl4AICrawlingProvider,
)
from app.state.transitions.crawling_state import (
    get_or_create_website_crawl_state,
    mark_website_crawl_completed,
    mark_website_crawl_failed,
    mark_website_crawl_started,
)


logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class WebsiteAnalysisResult:
    content: WebsiteContent
    crawled: bool


@dataclass(frozen=True, slots=True)
class WebsitePageCrawlResult:
    content: WebsiteContent
    crawl_id: int


# ---------------------------------------------------------------------------
# Root website analysis
# ---------------------------------------------------------------------------


async def analyze_website(
    session: AsyncSession,
    *,
    company_id: int,
    website: str,
    provider: Crawl4AICrawlingProvider,
    retention_days: int,
    timeout: int = 30,
) -> WebsiteAnalysisResult:
    """
    Analyze the company's root website.

    This operation owns the company-level crawl state and retention
    decision.

    It should be used for the canonical/root company website only.

    Additional pages such as:

        /team
        /about
        /about-us
        /contact
        /leadership

    should be crawled using ``crawl_website_page()`` so they do not
    overwrite or interfere with the company's root crawl state.
    """

    logger.info(
        "website_analysis_started",
        company_id=company_id,
        website=website,
        retention_days=retention_days,
        timeout=timeout,
    )

    # =========================================================
    # Crawl state
    # =========================================================

    state = await get_or_create_website_crawl_state(
        session=session,
        company_id=company_id,
    )

    existing_crawl = await get_last_website_crawl(
        session=session,
        last_crawl_id=state.last_crawl_id,
    )

    now = datetime.now(UTC)

    # =========================================================
    # Retention check
    # =========================================================

    if existing_crawl is not None:
        should_recrawl = should_recrawl_website(
            WebsiteCrawlRetentionContext(
                collected_at=existing_crawl.collected_at,
                max_age=timedelta(days=retention_days),
            ),
            now=now,
        )

        if not should_recrawl:
            logger.info(
                "website_crawl_reused",
                company_id=company_id,
                website=website,
                crawl_id=existing_crawl.id,
                collected_at=existing_crawl.collected_at,
                retention_days=retention_days,
            )

            content = await get_website_crawl_content(
                session=session,
                crawl=existing_crawl,
            )

            logger.info(
                "website_analysis_completed",
                company_id=company_id,
                website=website,
                crawled=False,
                crawl_id=existing_crawl.id,
            )

            return WebsiteAnalysisResult(
                content=content,
                crawled=False,
            )

        logger.info(
            "website_crawl_retention_expired",
            company_id=company_id,
            website=website,
            crawl_id=existing_crawl.id,
            collected_at=existing_crawl.collected_at,
            retention_days=retention_days,
        )

    else:
        logger.info(
            "website_crawl_required",
            company_id=company_id,
            website=website,
            reason="no_previous_crawl",
        )

    # =========================================================
    # Start root crawl
    # =========================================================

    await mark_website_crawl_started(
        session=session,
        state=state,
    )

    await session.commit()

    logger.info(
        "website_crawl_started",
        company_id=company_id,
        website=website,
        provider=provider.provider_name,
    )

    # =========================================================
    # Crawl root website
    # =========================================================

    try:
        content = await provider.crawl(
            CrawlRequest(
                url=website,
                timeout=timeout,
            )
        )

    except Exception as exc:
        await session.rollback()

        logger.error(
            "website_crawl_failed",
            company_id=company_id,
            website=website,
            provider=provider.provider_name,
            error_type=type(exc).__name__,
            error=str(exc),
        )

        state = await get_or_create_website_crawl_state(
            session=session,
            company_id=company_id,
        )

        await mark_website_crawl_failed(
            session=session,
            state=state,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )

        await session.commit()

        raise

    logger.info(
        "website_crawl_completed",
        company_id=company_id,
        website=website,
        provider=provider.provider_name,
        status_code=content.status_code,
        html_chars=len(content.html or ""),
        text_chars=len(content.text or ""),
        links=len(content.links),
    )

    # =========================================================
    # Persist root crawl
    # =========================================================

    try:
        crawl = await load_website_crawl(
            session=session,
            content=content,
            company_id=company_id,
            provider_name=provider.provider_name,
        )

        await mark_website_crawl_completed(
            session=session,
            state=state,
            crawl_id=crawl.id,
        )

        await session.commit()

        logger.info(
            "website_crawl_persisted",
            company_id=company_id,
            website=website,
            crawl_id=crawl.id,
        )

    except Exception as exc:
        await session.rollback()

        logger.error(
            "website_crawl_persistence_failed",
            company_id=company_id,
            website=website,
            provider=provider.provider_name,
            error_type=type(exc).__name__,
            error=str(exc),
        )

        state = await get_or_create_website_crawl_state(
            session=session,
            company_id=company_id,
        )

        await mark_website_crawl_failed(
            session=session,
            state=state,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )

        await session.commit()

        raise

    logger.info(
        "website_analysis_completed",
        company_id=company_id,
        website=website,
        crawled=True,
        crawl_id=crawl.id,
    )

    return WebsiteAnalysisResult(
        content=content,
        crawled=True,
    )


# ---------------------------------------------------------------------------
# Secondary/internal page crawling
# ---------------------------------------------------------------------------


async def crawl_website_page(
    *,
    session: AsyncSession,
    company_id: int,
    url: str,
    provider: Crawl4AICrawlingProvider,
    timeout: int = 30,
) -> WebsitePageCrawlResult:
    """
    Crawl and persist one selected internal website page.

    This operation deliberately does not modify WebsiteCrawlState.

    It is intended for secondary business-relevant pages such as:

        /team
        /people
        /about
        /about-us
        /over-ons
        /leadership
        /management
        /contact

    The caller owns transaction boundaries.
    """

    logger.info(
        "website_page_crawl_started",
        company_id=company_id,
        url=url,
        provider=provider.provider_name,
        timeout=timeout,
    )

    content = await provider.crawl(
        CrawlRequest(
            url=url,
            timeout=timeout,
        )
    )

    logger.info(
        "website_page_crawl_completed",
        company_id=company_id,
        url=url,
        provider=provider.provider_name,
        status_code=content.status_code,
        html_chars=len(content.html or ""),
        text_chars=len(content.text or ""),
        links=len(content.links),
    )

    crawl = await load_website_crawl(
        session=session,
        content=content,
        company_id=company_id,
        provider_name=provider.provider_name,
    )

    logger.info(
        "website_page_crawl_persisted",
        company_id=company_id,
        url=url,
        crawl_id=crawl.id,
    )

    return WebsitePageCrawlResult(
        content=content,
        crawl_id=crawl.id,
    )


__all__ = [
    "WebsiteAnalysisResult",
    "WebsitePageCrawlResult",
    "analyze_website",
    "crawl_website_page",
]