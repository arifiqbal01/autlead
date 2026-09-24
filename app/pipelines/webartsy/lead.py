# app/pipelines/webartsy/lead.py

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.schemas import DiscoveryQuery
from app.pipelines.acquisition.business_discovery import (
    BusinessDiscoveryPipelineResult,
    run_business_discovery_pipeline,
)
from app.pipelines.common.workers import (
    WorkerRetryPolicy,
    run_worker_pool,
)
from app.pipelines.webartsy.company import (
    WebArtsyCompanyResult,
    WebArtsyCompanyWorkItem,
    process_company_with_session,
)
from app.providers.crawling.crawl4ai_provider import (
    Crawl4AICrawlingProvider,
)
from app.providers.discovery import BusinessDiscoveryProvider
from app.providers.performance.protocol import (
    WebsitePerformanceProvider,
    WebsiteSeoProvider,
)
from app.providers.technology.protocol import (
    WebsiteTechnologyDetectionProvider,
)
from app.providers.email.verification import (
    EmailVerificationProvider,
)
from app.providers.llm.gemini import (
    GeminiLLMProvider,
)

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Aggregate result models
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WebArtsyTechnologySummary:
    """
    Aggregated technology-detection result across successfully
    processed companies that have websites.
    """

    detected: int
    failed: int
    stored: int


@dataclass(frozen=True, slots=True)
class WebArtsyPerformanceSummary:
    """
    Aggregated performance/SEO result across successfully
    processed companies that have websites.
    """

    analyzed: int
    failed: int
    stored: int


# ---------------------------------------------------------------------------
# Failure model
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WebArtsyCompanyFailure:
    """
    Represents one company that genuinely failed during WebArtsy
    enrichment.

    A missing website is not a company failure.
    """

    company_id: int
    company_name: str
    website: str | None

    stage: str

    error_type: str
    error_message: str


# ---------------------------------------------------------------------------
# Pipeline result
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WebArtsyLeadResult:
    discovery: BusinessDiscoveryPipelineResult

    technology: WebArtsyTechnologySummary
    performance: WebArtsyPerformanceSummary

    companies: list[WebArtsyCompanyResult]
    failures: list[WebArtsyCompanyFailure]

    @property
    def companies_analyzed(self) -> int:
        return len(
            self.companies
        )

    @property
    def companies_failed(self) -> int:
        return len(
            self.failures
        )

    @property
    def companies_with_website(self) -> int:
        return sum(
            1
            for company in self.companies
            if not company.website_missing
        )

    @property
    def companies_without_website(self) -> int:
        return sum(
            1
            for company in self.companies
            if company.website_missing
        )

    @property
    def people_found(self) -> int:
        return sum(
            len(company.people)
            for company in self.companies
        )

    @property
    def decision_makers_found(self) -> int:
        return sum(
            len(company.decision_makers)
            for company in self.companies
        )


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


async def run_webartsy_lead_pipeline(
    *,
    session: AsyncSession,
    discovery_provider: BusinessDiscoveryProvider,
    query: DiscoveryQuery,
    crawler_provider: Crawl4AICrawlingProvider,
    technology_provider: WebsiteTechnologyDetectionProvider,
    performance_provider: WebsitePerformanceProvider,
    seo_provider: WebsiteSeoProvider,
    email_provider: EmailVerificationProvider,
    gemini_provider: GeminiLLMProvider,
    phone_region: str | None = None,
    source_id: int | None = None,
    retention_days: int = 30,
    timeout: int = 30,
    decision_maker_limit: int = 5,
    person_email_limit: int | None = None,
    business_page_limit: int = 5,
    company_workers: int = 3,
    company_queue_size: int | None = None,
    company_retries: int = 1,
    language: str = "nl",
) -> WebArtsyLeadResult:
    """
    Run discovery followed by WebArtsy company enrichment.

    Workflow:

        business discovery
            ↓
        company persistence
            ↓
        convert discovered companies into neutral WebArtsy work items
            ↓
        async company worker pool
            ↓
        each worker:
            process_company_with_session()
                ↓
            dedicated AsyncSession
                ↓
            full company enrichment
                ↓
            persist + commit
            ↓
        worker receives next company

    The session passed to this function belongs only to the
    discovery/orchestration stage.

    Company workers must never share that session.
    """

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

    logger.info(
        "webartsy_pipeline_started",
        query=query.query,
        location=query.location,
        limit=query.limit,
        company_workers=company_workers,
        company_queue_size=company_queue_size,
        company_retries=company_retries,
    )

    # =========================================================
    # 1. BUSINESS DISCOVERY
    # =========================================================

    logger.info(
        "webartsy_stage_started",
        stage="discovery",
    )

    discovery = await run_business_discovery_pipeline(
        provider=discovery_provider,
        query=query,
        session=session,
    )

    logger.info(
        "webartsy_stage_completed",
        stage="discovery",
        found=discovery.found,
        new=discovery.new,
        duplicates=discovery.duplicates,
        stored=discovery.stored,
    )

    # =========================================================
    # 2. BUILD COMPANY WORK ITEMS
    # =========================================================
    #
    # Discovery-specific objects stop here.
    #
    # company.py receives only the minimal neutral data required
    # to enrich a persisted company.
    #
    # Companies without websites are intentionally included.
    # =========================================================

    company_work_items = [
        WebArtsyCompanyWorkItem(
            company_id=company.company_id,
            name=company.name,
            website=company.website,
            domain=company.domain,
        )
        for company in discovery.companies
    ]

    failures: list[
        WebArtsyCompanyFailure
    ] = []

    companies_with_website = sum(
        1
        for company in company_work_items
        if company.website
        and company.website.strip()
    )

    companies_without_website = (
        len(company_work_items)
        - companies_with_website
    )

    logger.info(
        "webartsy_company_queue_prepared",
        discovered=len(
            discovery.companies
        ),
        processable=len(
            company_work_items
        ),
        with_website=(
            companies_with_website
        ),
        without_website=(
            companies_without_website
        ),
        workers=company_workers,
        queue_size=company_queue_size,
    )

    # =========================================================
    # 3. COMPANY HANDLER
    # =========================================================

    async def handle_company(
        company: WebArtsyCompanyWorkItem,
        gemini_provider: GeminiLLMProvider,
    ) -> WebArtsyCompanyResult:
        """
        Process exactly one company.

        process_company_with_session() creates an isolated
        AsyncSession for this company.

        After that company commits or rolls back, the worker may
        receive another company.
        """

        logger.info(
            "webartsy_company_worker_started",
            company_id=company.company_id,
            company_name=company.name,
            website=company.website,
            website_missing=(
                not bool(
                    company.website
                    and company.website.strip()
                )
            ),
        )

        result = await process_company_with_session(
            company=company,
            crawler_provider=crawler_provider,
            technology_provider=technology_provider,
            performance_provider=performance_provider,
            seo_provider=seo_provider,
            email_provider=email_provider,
            gemini_provider=gemini_provider,
            phone_region=phone_region,
            source_id=source_id,
            retention_days=retention_days,
            timeout=timeout,
            decision_maker_limit=decision_maker_limit,
            person_email_limit=person_email_limit,
            business_page_limit=business_page_limit,
            language=language,
        )

        logger.info(
            "webartsy_company_worker_completed",
            company_id=result.company_id,
            company_name=result.company_name,
            website=result.website,
            website_missing=(
                result.website_missing
            ),
            technologies_detected=(
                result.technology.detected
                if result.technology is not None
                else 0
            ),
            technology_failed=(
                result.technology.failed
                if result.technology is not None
                else 0
            ),
            performance_analyzed=(
                result.performance.analyzed
                if result.performance is not None
                else 0
            ),
            performance_failed=(
                result.performance.failed
                if result.performance is not None
                else 0
            ),
            contacts_persisted=(
                result.contacts.persisted_count
                if result.contacts is not None
                else 0
            ),
            people=len(
                result.people
            ),
            decision_makers=len(
                result.decision_makers
            ),
            pages=(
                result.pages_processed
            ),
        )

        return result

    # =========================================================
    # 4. COMPANY WORKER POOL
    # =========================================================

    logger.info(
        "webartsy_stage_started",
        stage="company_enrichment",
        companies=len(
            company_work_items
        ),
        with_website=(
            companies_with_website
        ),
        without_website=(
            companies_without_website
        ),
        workers=company_workers,
    )

    worker_result = await run_worker_pool(
        items=company_work_items,
        worker_count=company_workers,
        queue_size=company_queue_size,
        handler=handle_company,
        retry_policy=WorkerRetryPolicy(
            retries=company_retries,
            base_delay_seconds=2.0,
            max_delay_seconds=15.0,
            backoff_factor=2.0,
        ),
        should_retry=(
            _should_retry_company
        ),
        item_name=(
            _company_item_name
        ),
    )

    company_results = (
        worker_result.results
    )

    # =========================================================
    # 5. WORKER FAILURES
    # =========================================================

    for worker_failure in (
        worker_result.failures
    ):
        company = worker_failure.item

        failure = WebArtsyCompanyFailure(
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
        )

        failures.append(
            failure
        )

        logger.error(
            "webartsy_company_failed",
            company_id=company.company_id,
            company_name=company.name,
            website=company.website,
            stage=failure.stage,
            error_type=failure.error_type,
            error_message=failure.error_message,
            attempts=worker_failure.attempts,
        )

    successful_with_website = sum(
        1
        for company in company_results
        if not company.website_missing
    )

    successful_without_website = sum(
        1
        for company in company_results
        if company.website_missing
    )

    logger.info(
        "webartsy_stage_completed",
        stage="company_enrichment",
        companies=len(
            company_work_items
        ),
        succeeded=(
            worker_result.succeeded
        ),
        succeeded_with_website=(
            successful_with_website
        ),
        succeeded_without_website=(
            successful_without_website
        ),
        failed=(
            worker_result.failed
        ),
        workers=company_workers,
    )

    # =========================================================
    # 6. AGGREGATE TECHNOLOGY RESULTS
    # =========================================================

    technology_summary = (
        _aggregate_technology(
            company_results
        )
    )

    # =========================================================
    # 7. AGGREGATE PERFORMANCE RESULTS
    # =========================================================

    performance_summary = (
        _aggregate_performance(
            company_results
        )
    )

    # =========================================================
    # 8. FINAL RESULT
    # =========================================================

    result = WebArtsyLeadResult(
        discovery=discovery,
        technology=technology_summary,
        performance=performance_summary,
        companies=company_results,
        failures=failures,
    )

    logger.info(
        "webartsy_pipeline_completed",
        found=result.discovery.found,
        new=result.discovery.new,
        duplicates=(
            result.discovery.duplicates
        ),
        stored=(
            result.discovery.stored
        ),
        companies_analyzed=(
            result.companies_analyzed
        ),
        companies_with_website=(
            result.companies_with_website
        ),
        companies_without_website=(
            result.companies_without_website
        ),
        companies_failed=(
            result.companies_failed
        ),
        people_found=(
            result.people_found
        ),
        decision_makers_found=(
            result.decision_makers_found
        ),
        technologies_detected=(
            result.technology.detected
        ),
        technology_failed=(
            result.technology.failed
        ),
        technology_stored=(
            result.technology.stored
        ),
        performance_analyzed=(
            result.performance.analyzed
        ),
        performance_failed=(
            result.performance.failed
        ),
        performance_stored=(
            result.performance.stored
        ),
        company_workers=(
            company_workers
        ),
    )

    return result


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def _aggregate_technology(
    companies: list[
        WebArtsyCompanyResult
    ],
) -> WebArtsyTechnologySummary:
    """
    Aggregate per-company technology results.

    Companies without websites have technology=None.
    """

    return WebArtsyTechnologySummary(
        detected=sum(
            company.technology.detected
            for company in companies
            if company.technology is not None
        ),
        failed=sum(
            company.technology.failed
            for company in companies
            if company.technology is not None
        ),
        stored=sum(
            company.technology.stored
            for company in companies
            if company.technology is not None
        ),
    )


def _aggregate_performance(
    companies: list[
        WebArtsyCompanyResult
    ],
) -> WebArtsyPerformanceSummary:
    """
    Aggregate per-company performance/SEO results.

    Companies without websites have performance=None.
    """

    return WebArtsyPerformanceSummary(
        analyzed=sum(
            company.performance.analyzed
            for company in companies
            if company.performance is not None
        ),
        failed=sum(
            company.performance.failed
            for company in companies
            if company.performance is not None
        ),
        stored=sum(
            company.performance.stored
            for company in companies
            if company.performance is not None
        ),
    )


# ---------------------------------------------------------------------------
# Worker helpers
# ---------------------------------------------------------------------------


def _company_item_name(
    company: WebArtsyCompanyWorkItem,
) -> str:
    return (
        f"{company.company_id}:"
        f"{company.name}"
    )


def _should_retry_company(
    exc: Exception,
) -> bool:
    """
    Retry only failures that are plausibly transient.
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
    error_name = (
        type(exc).__name__
    )

    if error_name in {
        "CrawlingProviderError",
        "CrawlingProviderTimeout",
    }:
        return "website_analysis"

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
        return "performance_seo"

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

    return "company_pipeline"