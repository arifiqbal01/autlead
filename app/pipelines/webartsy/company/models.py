# app/pipelines/enrichment/models.py

from __future__ import annotations

from dataclasses import dataclass

from app.pipelines.common.contacts import (
    ContactAnalysisResult,
)
from app.pipelines.common.people import (
    AnalyzedPerson,
    PeopleAnalysisResult,
)
from app.pipelines.common.person_email import (
    PersonEmailAnalysisResult,
)
from app.pipelines.common.technology_detection import (
    WebsiteTechnologyPipelineResult,
)
from app.pipelines.common.website_crawl import (
    WebsiteAnalysisResult,
)
from app.pipelines.common.website_performance import (
    WebsitePerformancePipelineResult,
)


@dataclass(frozen=True, slots=True)
class WebArtsyCompanyWorkItem:
    company_id: int
    name: str
    website: str | None
    domain: str | None


@dataclass(frozen=True, slots=True)
class WebArtsyCompanyResult:
    company_id: int
    company_name: str

    website: str | None
    website_missing: bool

    technology: WebsiteTechnologyPipelineResult | None
    performance: WebsitePerformancePipelineResult | None
    website_analysis: WebsiteAnalysisResult | None

    contacts: ContactAnalysisResult | None
    people_analysis: PeopleAnalysisResult | None
    person_email_analysis: PersonEmailAnalysisResult | None

    pages_processed: int

    @property
    def people(self) -> list[AnalyzedPerson]:
        if self.people_analysis is None:
            return []

        return self.people_analysis.people

    @property
    def decision_makers(self) -> list[AnalyzedPerson]:
        if self.people_analysis is None:
            return []

        return self.people_analysis.decision_makers