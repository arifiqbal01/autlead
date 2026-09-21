# app/pipelines/webartsy/company/company.py

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.session import SessionFactory
from app.core.logging import get_logger

from app.pipelines.common.website_crawl import (
    analyze_website,
)
from app.pipelines.common.website_pages import (
    collect_business_pages,
)

from app.pipelines.webartsy.company.lifecycle import (
    run_checkpointed_stage,
    stage_should_run,
)
from app.pipelines.webartsy.company.models import (
    WebArtsyCompanyResult,
)
from app.pipelines.webartsy.company.stages import (
    run_contacts_stage,
    run_people_stage,
    run_performance_stage,
    run_person_email_stage,
    run_technology_stage,
)
from app.pipelines.webartsy.company.work_items import (
    WebArtsyCompanyWorkItem,
)

from app.providers.crawling.crawl4ai_provider import (
    Crawl4AICrawlingProvider,
)
from app.providers.email.verification import (
    EmailVerificationProvider,
)
from app.providers.llm.groq import (
    GroqLLMProvider,
)
from app.providers.performance.protocol import (
    WebsitePerformanceProvider,
    WebsiteSeoProvider,
)
from app.providers.technology.protocol import (
    WebsiteTechnologyDetectionProvider,
)

from app.state.pipeline.webartsy import (
    WebArtsyStage,
    mark_stage_completed,
    mark_stage_failed,
    mark_stage_running,
)

logger = get_logger(__name__)


STAGE_TECHNOLOGY = WebArtsyStage(
    "technology_detection"
)
STAGE_PERFORMANCE = WebArtsyStage(
    "performance_seo"
)
STAGE_WEBSITE = WebArtsyStage(
    "website_analysis"
)
STAGE_BUSINESS_PAGES = WebArtsyStage(
    "business_pages"
)
STAGE_CONTACTS = WebArtsyStage(
    "contacts"
)
STAGE_PEOPLE = WebArtsyStage(
    "person_persistence"
)
STAGE_PERSON_EMAIL = WebArtsyStage(
    "person_email"
)


async def process_company_with_session(
    *,
    company: WebArtsyCompanyWorkItem,
    crawler_provider: Crawl4AICrawlingProvider,
    technology_provider: WebsiteTechnologyDetectionProvider,
    performance_provider: WebsitePerformanceProvider,
    seo_provider: WebsiteSeoProvider,
    email_provider: EmailVerificationProvider,
    groq_provider: GroqLLMProvider,
    phone_region: str | None = None,
    source_id: int | None = None,
    retention_days: int = 30,
    timeout: int = 30,
    decision_maker_limit: int = 5,
    person_email_limit: int | None = None,
    business_page_limit: int = 5,
    language: str = "nl",
) -> WebArtsyCompanyResult:
    async with SessionFactory() as session:
        try:
            return await process_webartsy_company(
                session=session,
                company=company,
                crawler_provider=crawler_provider,
                technology_provider=technology_provider,
                performance_provider=performance_provider,
                seo_provider=seo_provider,
                email_provider=email_provider,
                groq_provider=groq_provider,
                phone_region=phone_region,
                source_id=source_id,
                retention_days=retention_days,
                timeout=timeout,
                decision_maker_limit=decision_maker_limit,
                person_email_limit=person_email_limit,
                business_page_limit=business_page_limit,
                language=language,
            )

        except Exception:
            await session.rollback()

            logger.exception(
                "webartsy_company_session_failed",
                company_id=company.company_id,
                company_name=company.name,
                website=company.website,
            )

            raise


async def process_webartsy_company(
    *,
    session: AsyncSession,
    company: WebArtsyCompanyWorkItem,
    crawler_provider: Crawl4AICrawlingProvider,
    technology_provider: WebsiteTechnologyDetectionProvider,
    performance_provider: WebsitePerformanceProvider,
    seo_provider: WebsiteSeoProvider,
    email_provider: EmailVerificationProvider,
    groq_provider: GroqLLMProvider,
    phone_region: str | None = None,
    source_id: int | None = None,
    retention_days: int = 30,
    timeout: int = 30,
    decision_maker_limit: int = 5,
    person_email_limit: int | None = None,
    business_page_limit: int = 5,
    language: str = "nl",
) -> WebArtsyCompanyResult:
    company_id = company.company_id
    company_name = company.name

    website = _clean_optional(
        company.website
    )
    domain = _clean_optional(
        company.domain
    )

    logger.info(
        "webartsy_company_started",
        company_id=company_id,
        company_name=company_name,
        website=website,
        domain=domain,
    )

    if website is None:
        return _website_missing_result(
            company
        )

    # ---------------------------------------------------------
    # Technology
    # ---------------------------------------------------------

    technology_result = await run_checkpointed_stage(
        session,
        company_id=company_id,
        company_name=company_name,
        stage=STAGE_TECHNOLOGY,
        operation=lambda: run_technology_stage(
            session=session,
            provider=technology_provider,
            company_id=company_id,
            company_name=company_name,
            website=website,
            source_id=source_id,
            timeout=timeout,
        ),
    )

    # ---------------------------------------------------------
    # Performance + SEO
    # ---------------------------------------------------------

    performance_result = await run_checkpointed_stage(
        session,
        company_id=company_id,
        company_name=company_name,
        stage=STAGE_PERFORMANCE,
        operation=lambda: run_performance_stage(
            session=session,
            performance_provider=performance_provider,
            seo_provider=seo_provider,
            company_id=company_id,
            company_name=company_name,
            website=website,
            source_id=source_id,
        ),
    )

    # ---------------------------------------------------------
    # Website
    # ---------------------------------------------------------

    website_result = await _run_website_stage(
        session=session,
        company_id=company_id,
        company_name=company_name,
        website=website,
        provider=crawler_provider,
        retention_days=retention_days,
        timeout=timeout,
    )

    homepage = website_result.content

    # ---------------------------------------------------------
    # Business pages
    # ---------------------------------------------------------

    page_collection = await _run_business_pages_stage(
        session=session,
        company_id=company_id,
        company_name=company_name,
        homepage=homepage,
        provider=crawler_provider,
        timeout=timeout,
        limit=business_page_limit,
    )

    pages = page_collection.pages

    # ---------------------------------------------------------
    # Contacts
    # ---------------------------------------------------------

    contact_result = await run_checkpointed_stage(
        session,
        company_id=company_id,
        company_name=company_name,
        stage=STAGE_CONTACTS,
        operation=lambda: run_contacts_stage(
            session=session,
            company_id=company_id,
            company_name=company_name,
            pages=pages,
            provider_name=(
                crawler_provider.provider_name
            ),
            phone_region=phone_region,
            source_id=source_id,
        ),
    )

    # ---------------------------------------------------------
    # People
    # ---------------------------------------------------------

    people_result = await run_checkpointed_stage(
        session,
        company_id=company_id,
        company_name=company_name,
        stage=STAGE_PEOPLE,
        operation=lambda: run_people_stage(
            session=session,
            company_id=company_id,
            company_name=company_name,
            pages=pages,
            homepage_url=str(
                homepage.url
            ),
            provider_name=(
                crawler_provider.provider_name
            ),
            groq_provider=groq_provider,
            source_id=source_id,
            decision_maker_limit=(
                decision_maker_limit
            ),
            language=language,
        ),
    )

    # ---------------------------------------------------------
    # Person email
    # ---------------------------------------------------------

    person_email_result = await run_checkpointed_stage(
        session,
        company_id=company_id,
        company_name=company_name,
        stage=STAGE_PERSON_EMAIL,
        operation=lambda: run_person_email_stage(
            session=session,
            provider=email_provider,
            company_id=company_id,
            company_name=company_name,
            company_domain=domain,
            source_id=source_id,
            person_limit=person_email_limit,
        ),
    )

    result = WebArtsyCompanyResult(
        company_id=company_id,
        company_name=company_name,
        website=website,
        website_missing=False,
        technology=technology_result,
        performance=performance_result,
        website_analysis=website_result,
        contacts=contact_result,
        people_analysis=people_result,
        person_email_analysis=(
            person_email_result
        ),
        pages_processed=len(
            pages
        ),
    )

    logger.info(
        "webartsy_company_completed",
        company_id=company_id,
        company_name=company_name,
        website=website,
        pages=len(pages),
    )

    return result


# ---------------------------------------------------------------------------
# Rehydrating stages
# ---------------------------------------------------------------------------


async def _run_website_stage(
    *,
    session: AsyncSession,
    company_id: int,
    company_name: str,
    website: str,
    provider: Crawl4AICrawlingProvider,
    retention_days: int,
    timeout: int,
):
    should_run = await stage_should_run(
        session,
        company_id=company_id,
        company_name=company_name,
        stage=STAGE_WEBSITE,
    )

    if should_run:
        await _mark_running(
            session,
            company_id=company_id,
            stage=STAGE_WEBSITE,
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
            await _mark_completed(
                session,
                company_id=company_id,
                stage=STAGE_WEBSITE,
            )

        return result

    except Exception as exc:
        if should_run:
            await _mark_failed(
                session,
                company_id=company_id,
                stage=STAGE_WEBSITE,
                exc=exc,
            )

        raise


async def _run_business_pages_stage(
    *,
    session: AsyncSession,
    company_id: int,
    company_name: str,
    homepage,
    provider: Crawl4AICrawlingProvider,
    timeout: int,
    limit: int,
):
    should_run = await stage_should_run(
        session,
        company_id=company_id,
        company_name=company_name,
        stage=STAGE_BUSINESS_PAGES,
    )

    if should_run:
        await _mark_running(
            session,
            company_id=company_id,
            stage=STAGE_BUSINESS_PAGES,
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
            await _mark_completed(
                session,
                company_id=company_id,
                stage=STAGE_BUSINESS_PAGES,
            )

        return result

    except Exception as exc:
        if should_run:
            await _mark_failed(
                session,
                company_id=company_id,
                stage=STAGE_BUSINESS_PAGES,
                exc=exc,
            )

        raise


# ---------------------------------------------------------------------------
# Small checkpoint helpers used by rehydrating stages
# ---------------------------------------------------------------------------


async def _mark_running(
    session: AsyncSession,
    *,
    company_id: int,
    stage: WebArtsyStage,
) -> None:
    await mark_stage_running(
        session,
        company_id=company_id,
        stage=stage,
    )
    await session.commit()


async def _mark_completed(
    session: AsyncSession,
    *,
    company_id: int,
    stage: WebArtsyStage,
) -> None:
    await mark_stage_completed(
        session,
        company_id=company_id,
        stage=stage,
    )
    await session.commit()


async def _mark_failed(
    session: AsyncSession,
    *,
    company_id: int,
    stage: WebArtsyStage,
    exc: Exception,
) -> None:
    await session.rollback()

    await mark_stage_failed(
        session,
        company_id=company_id,
        stage=stage,
        exc=exc,
    )

    await session.commit()


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _clean_optional(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    value = value.strip()

    return value or None


def _website_missing_result(
    company: WebArtsyCompanyWorkItem,
) -> WebArtsyCompanyResult:
    logger.info(
        "webartsy_company_no_website",
        company_id=company.company_id,
        company_name=company.name,
        opportunity="website_missing",
    )

    return WebArtsyCompanyResult(
        company_id=company.company_id,
        company_name=company.name,
        website=None,
        website_missing=True,
        technology=None,
        performance=None,
        website_analysis=None,
        contacts=None,
        people_analysis=None,
        person_email_analysis=None,
        pages_processed=0,
    )