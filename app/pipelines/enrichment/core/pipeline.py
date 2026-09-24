# app/pipelines/enrichment/core/pipeline.py

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from app.core.database.session import SessionFactory
from app.core.logging import get_logger
from app.models.persistence import Company
from app.pipelines.common.workers import (
    WorkerRetryPolicy,
    run_worker_pool,
)
from app.pipelines.enrichment.core.company import (
    process_company_with_session,
)
from app.pipelines.enrichment.core.models import (
    CompanyEnrichmentResult,
    EnrichmentCompanyFailure,
    EnrichmentPipelineResult,
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


logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Enrichment pipeline
# ---------------------------------------------------------------------------


async def run_enrichment_pipeline(
    *,
    crawler_provider: Crawl4AICrawlingProvider,
    technology_provider: WebsiteTechnologyDetectionProvider,
    performance_provider: WebsitePerformanceProvider,
    seo_provider: WebsiteSeoProvider,
    email_provider: EmailVerificationProvider,
    groq_provider: GroqLLMProvider,
    start_from: datetime | None = None,
    after_company_id: int | None = None,
    batch_size: int = 100,
    max_companies: int | None = None,
    company_workers: int = 3,
    company_queue_size: int | None = None,
    company_retries: int = 1,
    phone_region: str | None = None,
    source_id: int | None = None,
    retention_days: int = 30,
    timeout: int = 30,
    decision_maker_limit: int = 5,
    person_email_limit: int | None = None,
    business_page_limit: int = 5,
    language: str = "nl",
) -> EnrichmentPipelineResult:
    """
    Enrich companies already persisted in PostgreSQL.

    Acquisition/business discovery is not performed here.

    Flow:

        PostgreSQL Company
            ↓
        bounded database batch
            ↓
        CompanyEnrichmentWorkItem
            ↓
        worker pool
            ↓
        dedicated session per company
            ↓
        company enrichment
            ↓
        next company / next batch

    Database selection and company processing use separate sessions.

    ORM Company objects are never passed into concurrent workers.
    Workers receive immutable CompanyEnrichmentWorkItem objects.

    Keyset pagination using Company.id prevents loading the complete
    company table into memory.
    """

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    if batch_size < 1:
        raise ValueError(
            "batch_size must be >= 1"
        )

    if company_workers < 1:
        raise ValueError(
            "company_workers must be >= 1"
        )

    if company_retries < 0:
        raise ValueError(
            "company_retries must be >= 0"
        )

    if (
        company_queue_size is not None
        and company_queue_size < 1
    ):
        raise ValueError(
            "company_queue_size must be >= 1"
        )

    if (
        max_companies is not None
        and max_companies < 1
    ):
        raise ValueError(
            "max_companies must be >= 1"
        )

    # ------------------------------------------------------------------
    # Pipeline state
    # ------------------------------------------------------------------

    cursor = after_company_id

    selected_total = 0
    succeeded_total = 0
    failed_total = 0

    successful_results: list[
        CompanyEnrichmentResult
    ] = []

    failures: list[
        EnrichmentCompanyFailure
    ] = []

    logger.info(
        "enrichment_pipeline_started",
        start_from=(
            start_from.isoformat()
            if start_from is not None
            else None
        ),
        after_company_id=after_company_id,
        batch_size=batch_size,
        max_companies=max_companies,
        company_workers=company_workers,
        company_queue_size=company_queue_size,
        company_retries=company_retries,
    )

    # ------------------------------------------------------------------
    # Batch loop
    # ------------------------------------------------------------------

    while True:
        current_batch_size = batch_size

        if max_companies is not None:
            remaining = (
                max_companies
                - selected_total
            )

            if remaining <= 0:
                break

            current_batch_size = min(
                batch_size,
                remaining,
            )

        work_items = await _load_company_batch(
            start_from=start_from,
            after_company_id=cursor,
            limit=current_batch_size,
        )

        if not work_items:
            break

        selected_total += len(
            work_items
        )

        batch_first_id = (
            work_items[0].company_id
        )

        batch_last_id = (
            work_items[-1].company_id
        )

        logger.info(
            "enrichment_batch_loaded",
            companies=len(work_items),
            first_company_id=batch_first_id,
            last_company_id=batch_last_id,
            selected_total=selected_total,
        )

        # --------------------------------------------------------------
        # Company handler
        # --------------------------------------------------------------

        async def handle_company(
            company: CompanyEnrichmentWorkItem,
        ) -> CompanyEnrichmentResult:
            """
            Process exactly one persisted company.

            Company processing owns a dedicated AsyncSession.
            """

            logger.info(
                "enrichment_company_worker_started",
                company_id=company.company_id,
                company_name=company.name,
                website=company.website,
            )

            result = await process_company_with_session(
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

            logger.info(
                "enrichment_company_worker_completed",
                company_id=result.company_id,
                company_name=result.company_name,
                website=result.website,
                website_missing=(
                    result.website_missing
                ),
                pages=result.pages_processed,
                people=_people_count(result),
                decision_makers=(
                    _decision_maker_count(
                        result
                    )
                ),
            )

            return result

        # --------------------------------------------------------------
        # Worker pool
        # --------------------------------------------------------------

        worker_result = await run_worker_pool(
            items=work_items,
            worker_count=company_workers,
            queue_size=company_queue_size,
            handler=handle_company,
            retry_policy=WorkerRetryPolicy(
                retries=company_retries,
                base_delay_seconds=2.0,
                max_delay_seconds=15.0,
                backoff_factor=2.0,
            ),
            should_retry=_should_retry_company,
            item_name=_company_item_name,
        )

        # --------------------------------------------------------------
        # Successful companies
        # --------------------------------------------------------------

        successful_results.extend(
            worker_result.results
        )

        succeeded_total += (
            worker_result.succeeded
        )

        failed_total += (
            worker_result.failed
        )

        # --------------------------------------------------------------
        # Failed companies
        # --------------------------------------------------------------

        for worker_failure in (
            worker_result.failures
        ):
            company = worker_failure.item

            failure = EnrichmentCompanyFailure(
                company_id=company.company_id,
                company_name=company.name,
                website=company.website,
                stage=_failure_stage(
                    worker_failure.exception
                ),
                error_type=(
                    worker_failure.error_type
                ),
                error_message=(
                    worker_failure.error_message
                ),
                attempts=(
                    worker_failure.attempts
                ),
            )

            failures.append(
                failure
            )

            logger.error(
                "enrichment_company_failed",
                company_id=failure.company_id,
                company_name=failure.company_name,
                website=failure.website,
                stage=failure.stage,
                error_type=failure.error_type,
                error_message=(
                    failure.error_message
                ),
                attempts=failure.attempts,
            )

        # --------------------------------------------------------------
        # Advance keyset cursor
        # --------------------------------------------------------------

        cursor = batch_last_id

        logger.info(
            "enrichment_batch_completed",
            batch_selected=len(work_items),
            batch_succeeded=(
                worker_result.succeeded
            ),
            batch_failed=(
                worker_result.failed
            ),
            selected_total=selected_total,
            succeeded_total=succeeded_total,
            failed_total=failed_total,
            next_after_company_id=cursor,
        )

        if (
            len(work_items)
            < current_batch_size
        ):
            break

    # ------------------------------------------------------------------
    # Final aggregates
    # ------------------------------------------------------------------

    companies_with_website = sum(
        1
        for company in successful_results
        if not company.website_missing
    )

    companies_without_website = sum(
        1
        for company in successful_results
        if company.website_missing
    )

    people_found = sum(
        _people_count(company)
        for company in successful_results
    )

    decision_makers_found = sum(
        _decision_maker_count(company)
        for company in successful_results
    )

    result = EnrichmentPipelineResult(
        selected=selected_total,
        succeeded=succeeded_total,
        failed=failed_total,
        companies_with_website=(
            companies_with_website
        ),
        companies_without_website=(
            companies_without_website
        ),
        people_found=people_found,
        decision_makers_found=(
            decision_makers_found
        ),
        last_company_id=cursor,
        companies=successful_results,
        failures=failures,
    )

    logger.info(
        "enrichment_pipeline_completed",
        selected=result.selected,
        succeeded=result.succeeded,
        failed=result.failed,
        companies_with_website=(
            result.companies_with_website
        ),
        companies_without_website=(
            result.companies_without_website
        ),
        people_found=result.people_found,
        decision_makers_found=(
            result.decision_makers_found
        ),
        last_company_id=result.last_company_id,
    )

    return result


# ---------------------------------------------------------------------------
# PostgreSQL work selection
# ---------------------------------------------------------------------------


async def _load_company_batch(
    *,
    start_from: datetime | None,
    after_company_id: int | None,
    limit: int,
) -> list[CompanyEnrichmentWorkItem]:
    """
    Load one bounded batch of persisted companies.

    Selection uses its own database session. ORM objects are converted
    into immutable work items before leaving this function.
    """

    async with SessionFactory() as session:
        statement = select(
            Company.id,
            Company.name,
            Company.website,
            Company.domain,
        )

        if start_from is not None:
            statement = statement.where(
                Company.created_at
                >= start_from
            )

        if after_company_id is not None:
            statement = statement.where(
                Company.id
                > after_company_id
            )

        statement = (
            statement
            .order_by(
                Company.id.asc()
            )
            .limit(limit)
        )

        result = await session.execute(
            statement
        )

        rows = result.all()

    return [
        CompanyEnrichmentWorkItem(
            company_id=row.id,
            name=row.name,
            website=row.website,
            domain=row.domain,
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Aggregate helpers
# ---------------------------------------------------------------------------


def _people_count(
    result: CompanyEnrichmentResult,
) -> int:
    if result.people is None:
        return 0

    return len(
        result.people.people
    )


def _decision_maker_count(
    result: CompanyEnrichmentResult,
) -> int:
    if result.people is None:
        return 0

    return result.people.decision_maker_count


# ---------------------------------------------------------------------------
# Worker helpers
# ---------------------------------------------------------------------------


def _company_item_name(
    company: CompanyEnrichmentWorkItem,
) -> str:
    return (
        f"{company.company_id}:"
        f"{company.name}"
    )


def _should_retry_company(
    exc: Exception,
) -> bool:
    """
    Retry only plausibly transient company failures.
    """

    error_name = (
        type(exc).__name__
    )

    transient_errors = {
        "TimeoutError",
        "AsyncioTimeoutError",
        "CrawlingProviderTimeout",
        "ConnectionError",
        "ConnectionResetError",
        "ConnectError",
        "ReadTimeout",
        "ConnectTimeout",
        "RemoteProtocolError",
        "GroqRateLimitedError",
    }

    if error_name in transient_errors:
        return True

    message = str(
        exc
    ).casefold()

    transient_fragments = (
        "timed out",
        "timeout",
        "connection reset",
        "connection refused",
        "temporary failure",
        "temporarily unavailable",
        "service unavailable",
        "bad gateway",
        "gateway timeout",
        "rate limit",
        "too many requests",
        "http 429",
        "status 429",
        "http 502",
        "status 502",
        "http 503",
        "status 503",
        "http 504",
        "status 504",
    )

    return any(
        fragment in message
        for fragment in transient_fragments
    )


# ---------------------------------------------------------------------------
# Failure classification
# ---------------------------------------------------------------------------


def _failure_stage(
    exc: Exception,
) -> str:
    """
    Determine the likely failed enrichment stage.
    """

    error_name = (
        type(exc).__name__
    )

    if error_name in {
        "CrawlingProviderError",
        "CrawlingProviderTimeout",
    }:
        return "homepage"

    if error_name in {
        "TechnologyDetectionProviderError",
        "TechnologyProviderError",
    }:
        return "technology_detection"

    if error_name in {
        "PerformanceProviderError",
        "PageSpeedProviderError",
        "SeoProviderError",
    }:
        return "website_performance"

    if error_name in {
        "GroqProviderError",
        "GroqRateLimitedError",
        "GroqParseError",
    }:
        return "people_ai"

    if error_name == "IntegrityError":
        return "persistence"

    if error_name in {
        "MrEmailCheckerError",
        "MrEmailCheckerTimeoutError",
        "MrEmailCheckerParseError",
    }:
        return "person_email"

    if error_name in {
        "ValueError",
        "ValidationError",
    }:
        return "company_validation"

    return "company_enrichment"