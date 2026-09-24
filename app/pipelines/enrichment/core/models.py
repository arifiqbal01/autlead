# app/pipelines/enrichment/models.py

from __future__ import annotations

from dataclasses import dataclass

from app.pipelines.enrichment.stages.business_pages import (
    WebsitePageCollectionResult,
)
from app.pipelines.enrichment.stages.contacts import (
    ContactAnalysisResult,
)
from app.pipelines.enrichment.stages.homepage import (
    WebsiteAnalysisResult,
)
from app.pipelines.enrichment.stages.people import (
    PeopleAnalysisResult,
)
from app.pipelines.enrichment.stages.person_email import (
    PersonEmailAnalysisResult,
)
from app.pipelines.enrichment.stages.technology_detection import (
    TechnologyDetectionResult,
)
from app.pipelines.enrichment.stages.website_performance import (
    WebsitePerformanceResult,
)


@dataclass(frozen=True, slots=True)
class CompanyEnrichmentResult:
    """
    Final enrichment result for one persisted company.

    Acquisition has already created the company.

    Enrichment flow:

        company
            ↓
        technology detection
            ↓
        performance + SEO
            ↓
        homepage
            ↓
        business pages
            ↓
        contacts
            ↓
        people
            ↓
        person email verification
    """

    company_id: int
    company_name: str

    website: str | None
    website_missing: bool

    technology: TechnologyDetectionResult | None = None

    performance: WebsitePerformanceResult | None = None

    homepage: WebsiteAnalysisResult | None = None

    business_pages: WebsitePageCollectionResult | None = None

    contacts: ContactAnalysisResult | None = None

    people: PeopleAnalysisResult | None = None

    person_email: PersonEmailAnalysisResult | None = None

    pages_processed: int = 0


@dataclass(frozen=True, slots=True)
class EnrichmentCompanyFailure:
    """
    One persisted company that failed during enrichment.
    """

    company_id: int
    company_name: str
    website: str | None

    stage: str

    error_type: str
    error_message: str
    attempts: int


@dataclass(frozen=True, slots=True)
class EnrichmentPipelineResult:
    """
    Aggregate result for one enrichment pipeline invocation.
    """

    selected: int
    succeeded: int
    failed: int

    companies_with_website: int
    companies_without_website: int

    people_found: int
    decision_makers_found: int

    last_company_id: int | None

    companies: list[CompanyEnrichmentResult]
    failures: list[EnrichmentCompanyFailure]