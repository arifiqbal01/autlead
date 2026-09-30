# app/pipelines/enrichment/company.py

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.session import SessionFactory
from app.core.logging import get_logger

from app.pipelines.enrichment.stages.business_pages import (
    collect_business_pages,
)
from app.pipelines.enrichment.stages.contacts import (
    analyze_contacts,
)
from app.pipelines.enrichment.stages.homepage import (
    analyze_website,
)
from app.pipelines.enrichment.core.lifecycle import (
    run_checkpointed_stage,
    stage_should_run,
)
from app.pipelines.enrichment.core.models import (
    CompanyEnrichmentResult,
)
from app.pipelines.enrichment.stages.people import (
    enrich_people,
)
from app.pipelines.enrichment.stages.person_email import (
    enrich_person_emails,
)
from app.pipelines.enrichment.stages.technology_detection import (
    analyze_technology,
)
from app.pipelines.enrichment.stages.website_performance import (
    analyze_website_performance,
)
from app.pipelines.enrichment.core.work_items import (
    CompanyEnrichmentWorkItem,
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

from app.state.pipeline.enrichment import (
    EnrichmentStage,
    mark_stage_completed,
    mark_stage_failed,
    mark_stage_running,
)


logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Existing persisted stage identifiers
# ---------------------------------------------------------------------------

# Keep these persisted values unchanged during the structural refactor.
# Genericizing the persistence/state model is a separate concern.

STAGE_TECHNOLOGY = EnrichmentStage(
    "technology_detection"
)

STAGE_PERFORMANCE = EnrichmentStage(
    "performance_seo"
)

STAGE_HOMEPAGE = EnrichmentStage(
    "website_analysis"
)

STAGE_BUSINESS_PAGES = EnrichmentStage(
    "business_pages"
)

STAGE_CONTACTS = EnrichmentStage(
    "contacts"
)

STAGE_PEOPLE = EnrichmentStage(
    "person_persistence"
)

STAGE_PERSON_EMAIL = EnrichmentStage(
    "person_email"
)


# ---------------------------------------------------------------------------
# Session boundary
# ---------------------------------------------------------------------------


async def process_company_with_session(
    *,
    company: CompanyEnrichmentWorkItem,
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
) -> CompanyEnrichmentResult:
    """
    Process one persisted company using its own database session.
    """

    async with SessionFactory() as session:
        try:
            return await process_company(
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
                decision_maker_limit=(
                    decision_maker_limit
                ),
                person_email_limit=(
                    person_email_limit
                ),
                business_page_limit=(
                    business_page_limit
                ),
                language=language,
            )

        except Exception:
            await session.rollback()

            logger.exception(
                "enrichment_company_session_failed",
                company_id=company.company_id,
                company_name=company.name,
                website=company.website,
            )

            raise


# ---------------------------------------------------------------------------
# Company enrichment
# ---------------------------------------------------------------------------


async def process_company(
    *,
    session: AsyncSession,
    company: CompanyEnrichmentWorkItem,
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
) -> CompanyEnrichmentResult:
    """
    Run the complete enrichment flow for one persisted company.
    """

    company_id = company.company_id
    company_name = company.name

    website = _clean_optional(
        company.website
    )

    domain = _clean_optional(
        company.domain
    )

    logger.info(
        "enrichment_company_started",
        company_id=company_id,
        company_name=company_name,
        website=website,
        domain=domain,
    )

    if website is None:
        return _website_missing_result(
            company
        )

    # ------------------------------------------------------------------
    # 1. Technology detection
    # ------------------------------------------------------------------

    technology_result = await run_checkpointed_stage(
        session,
        company_id=company_id,
        company_name=company_name,
        stage=STAGE_TECHNOLOGY,
        operation=lambda: analyze_technology(
            session=session,
            provider=technology_provider,
            company_id=company_id,
            company_name=company_name,
            website=website,
            source_id=source_id,
            timeout=timeout,
        ),
    )

    # ------------------------------------------------------------------
    # 2. Performance + SEO
    # ------------------------------------------------------------------

    performance_result = await run_checkpointed_stage(
        session,
        company_id=company_id,
        company_name=company_name,
        stage=STAGE_PERFORMANCE,
        operation=lambda: analyze_website_performance(
            session=session,
            performance_provider=performance_provider,
            seo_provider=seo_provider,
            company_id=company_id,
            company_name=company_name,
            website=website,
            source_id=source_id,
        ),
    )

    # ------------------------------------------------------------------
    # 3. Homepage
    # ------------------------------------------------------------------

    homepage_result = await _run_homepage_stage(
        session=session,
        company_id=company_id,
        company_name=company_name,
        website=website,
        provider=crawler_provider,
        retention_days=retention_days,
        timeout=timeout,
    )

    homepage = homepage_result.content

    # ------------------------------------------------------------------
    # 4. Business pages
    # ------------------------------------------------------------------

    business_pages_result = (
        await _run_business_pages_stage(
            session=session,
            company_id=company_id,
            company_name=company_name,
            homepage=homepage,
            provider=crawler_provider,
            timeout=timeout,
            limit=business_page_limit,
        )
    )

    pages = business_pages_result.pages

    # ------------------------------------------------------------------
    # 5. Contacts
    # ------------------------------------------------------------------

    contact_result = await run_checkpointed_stage(
        session,
        company_id=company_id,
        company_name=company_name,
        stage=STAGE_CONTACTS,
        operation=lambda: analyze_contacts(
            session=session,
            company_id=company_id,
            pages=pages,
            provider_name=(
                crawler_provider.provider_name
            ),
            phone_region=phone_region,
            source_id=source_id,
        ),
    )

    # ------------------------------------------------------------------
    # 6. People
    # ------------------------------------------------------------------

    people_result = await run_checkpointed_stage(
        session,
        company_id=company_id,
        company_name=company_name,
        stage=STAGE_PEOPLE,
        operation=lambda: enrich_people(
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

    # ------------------------------------------------------------------
    # 7. Person outreach
    # ------------------------------------------------------------------

    person_email_result = None

    if domain is not None:
        person_email_result = (
            await run_checkpointed_stage(
                session,
                company_id=company_id,
                company_name=company_name,
                stage=STAGE_PERSON_EMAIL,
                operation=lambda: enrich_person_emails(
                    session=session,
                    provider=email_provider,
                    company_id=company_id,
                    company_name=company_name,
                    company_domain=domain,
                    source_id=source_id,
                    person_limit=(
                        person_email_limit
                    ),
                ),
            )
        )
    else:
        logger.info(
            "person_email_enrichment_skipped",
            company_id=company_id,
            company_name=company_name,
            reason="missing_domain",
        )

    # ------------------------------------------------------------------
    # Result
    # ------------------------------------------------------------------

    result = CompanyEnrichmentResult(
        company_id=company_id,
        company_name=company_name,
        website=website,
        website_missing=False,
        technology=technology_result,
        performance=performance_result,
        homepage=homepage_result,
        business_pages=(
            business_pages_result
        ),
        contacts=contact_result,
        people=people_result,
        person_email=(
            person_email_result
        ),
        pages_processed=len(pages),
    )

    logger.info(
        "enrichment_company_completed",
        company_id=company_id,
        company_name=company_name,
        website=website,
        pages=len(pages),
        people=(
            len(people_result.people)
            if people_result is not None
            else None
        ),
        decision_makers=(
            people_result.decision_maker_count
            if people_result is not None
            else None
        ),
    )

    return result


# ---------------------------------------------------------------------------
# Rehydrating homepage stage
# ---------------------------------------------------------------------------


async def _run_homepage_stage(
    *,
    session: AsyncSession,
    company_id: int,
    company_name: str,
    website: str,
    provider: Crawl4AICrawlingProvider,
    retention_days: int,
    timeout: int,
):
    """
    Homepage content must always be available to downstream stages.

    The checkpoint controls whether the stage state is transitioned,
    while analyze_website() may rehydrate retained persisted content.
    """

    should_run = await stage_should_run(
        session,
        company_id=company_id,
        company_name=company_name,
        stage=STAGE_HOMEPAGE,
    )

    if should_run:
        await _mark_running(
            session,
            company_id=company_id,
            stage=STAGE_HOMEPAGE,
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
                stage=STAGE_HOMEPAGE,
            )

        return result

    except Exception as exc:
        if should_run:
            await _mark_failed(
                session,
                company_id=company_id,
                stage=STAGE_HOMEPAGE,
                exc=exc,
            )

        raise


# ---------------------------------------------------------------------------
# Rehydrating business-pages stage
# ---------------------------------------------------------------------------


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
    """
    Business pages must be collected/rehydrated because downstream
    contacts and people enrichment require their content.
    """

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
# Checkpoint helpers
# ---------------------------------------------------------------------------


async def _mark_running(
    session: AsyncSession,
    *,
    company_id: int,
    stage: EnrichmentStage,
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
    stage: EnrichmentStage,
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
    stage: EnrichmentStage,
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
    company: CompanyEnrichmentWorkItem,
) -> CompanyEnrichmentResult:
    logger.info(
        "enrichment_company_no_website",
        company_id=company.company_id,
        company_name=company.name,
        opportunity="website_missing",
    )

    return CompanyEnrichmentResult(
        company_id=company.company_id,
        company_name=company.name,
        website=None,
        website_missing=True,
        technology=None,
        performance=None,
        homepage=None,
        business_pages=None,
        contacts=None,
        people=None,
        person_email=None,
        pages_processed=0,
    )