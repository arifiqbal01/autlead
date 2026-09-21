# app/pipelines/webartsy/company/stages/website.py

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.pipelines.common.website_crawl import (
    WebsiteAnalysisResult,
    analyze_website,
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


STAGE_WEBSITE = WebArtsyStage(
    "website_analysis"
)


async def run_website_stage(
    *,
    session: AsyncSession,
    company_id: int,
    company_name: str,
    website: str,
    provider: Crawl4AICrawlingProvider,
    retention_days: int = 30,
    timeout: int = 30,
) -> WebsiteAnalysisResult:
    """
    Run or rehydrate website analysis for one company.

    Unlike normal checkpointed stages, this function is called even when
    the website stage is already complete because downstream stages need
    WebsiteContent in memory.

    analyze_website() decides whether persisted crawl data can be reused
    or whether the website must be crawled again.
    """

    should_run = await stage_should_run(
        session,
        company_id=company_id,
        company_name=company_name,
        stage=STAGE_WEBSITE,
    )

    if should_run:
        await mark_stage_running(
            session,
            company_id=company_id,
            stage=STAGE_WEBSITE,
        )
        await session.commit()

        logger.info(
            "webartsy_company_stage_started",
            company_id=company_id,
            company_name=company_name,
            stage=STAGE_WEBSITE.value,
        )

    try:
        result = await analyze_website(
            session=session,
            company_id=company_id,
            website=website,
            provider=provider,
            retention_days=retention_days,
            timeout=timeout,
        )

        if should_run:
            await mark_stage_completed(
                session,
                company_id=company_id,
                stage=STAGE_WEBSITE,
            )
            await session.commit()

            logger.info(
                "webartsy_company_stage_completed",
                company_id=company_id,
                company_name=company_name,
                stage=STAGE_WEBSITE.value,
                crawled=result.crawled,
                status_code=result.content.status_code,
                html_length=len(
                    result.content.html or ""
                ),
                text_length=len(
                    result.content.text or ""
                ),
                links=len(
                    result.content.links
                ),
            )

        else:
            logger.info(
                "webartsy_company_stage_rehydrated",
                company_id=company_id,
                company_name=company_name,
                stage=STAGE_WEBSITE.value,
                crawled=result.crawled,
            )

        return result

    except Exception as exc:
        if should_run:
            await session.rollback()

            await mark_stage_failed(
                session,
                company_id=company_id,
                stage=STAGE_WEBSITE,
                exc=exc,
            )
            await session.commit()

            logger.error(
                "webartsy_company_stage_failed",
                company_id=company_id,
                company_name=company_name,
                stage=STAGE_WEBSITE.value,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )

        raise