# app/pipelines/enrichment/work_items.py

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CompanyEnrichmentWorkItem:
    """
    Immutable persisted-company input passed to enrichment workers.
    """

    company_id: int
    name: str
    website: str | None
    domain: str | None