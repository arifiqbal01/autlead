# app/pipelines/webartsy/company/stages/business_pages.py

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.pipelines.common.website_pages import (
    WebsitePageCollectionResult,
    collect_business_pages,
)
from app.pipelines.webartsy.company.lifecycle import (
    stage_should_run,
)
from app.providers.crawling.crawl4ai_provider import (
    Crawl4AICrawlingProvider,
)
from app.state.pipeline.webartsy import (
    WebArtsyStage,
    mark_stage_completed,
    mark_stage_failed,
    mark_stage_running,
)


logger = get_logger(__name__)


STAGE_BUSINESS_PAGES = WebArtsyStage(
    "business_pages"
)


async def run_business_pages_stage(
    *,
    session: AsyncSession,
    company_id: int,
    company_name: str,
    homepage: str,
    provider: Crawl4AICrawlingProvider,
    timeout: int = 30,
    limit: int = 5,
) -> WebsitePageCollectionResult:
    """
    Run or rehydrate business-page collection for one company.

    This stage is called even when already completed because contacts
    and people stages need page content in memory.

    collect_business_pages() decides whether existing persisted pages
    can be reused or whether additional crawling is required.
    """

    should_run = await stage_should_run(
        session,
        company_id=company_id,
        company_name=company_name,
        stage=STAGE_BUSINESS_PAGES,
    )

    if should_run:
        await mark_stage_running(
            session,
            company_id=company_id,
            stage=STAGE_BUSINESS_PAGES,
        )
        await session.commit()

        logger.info(
            "webartsy_company_stage_started",
            company_id=company_id,
            company_name=company_name,
            stage=STAGE_BUSINESS_PAGES.value,
        )

    try:
        result = await collect_business_pages(
            session=session,
            company_id=company_id,
            homepage=homepage,
            provider=provider,
            timeout=timeout,
            limit=limit,
        )

        if should_run:
            await mark_stage_completed(
                session,
                company_id=company_id,
                stage=STAGE_BUSINESS_PAGES,
            )
            await session.commit()

            logger.info(
                "webartsy_company_stage_completed",
                company_id=company_id,
                company_name=company_name,
                stage=STAGE_BUSINESS_PAGES.value,
                selected=result.selected,
                crawled=result.crawled,
                failed=result.failed,
                pages=len(
                    result.pages
                ),
            )

        else:
            logger.info(
                "webartsy_company_stage_rehydrated",
                company_id=company_id,
                company_name=company_name,
                stage=STAGE_BUSINESS_PAGES.value,
                pages=len(
                    result.pages
                ),
            )

        return result

    except Exception as exc:
        if should_run:
            await session.rollback()

            await mark_stage_failed(
                session,
                company_id=company_id,
                stage=STAGE_BUSINESS_PAGES,
                exc=exc,
            )
            await session.commit()

            logger.error(
                "webartsy_company_stage_failed",
                company_id=company_id,
                company_name=company_name,
                stage=STAGE_BUSINESS_PAGES.value,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )

        raise