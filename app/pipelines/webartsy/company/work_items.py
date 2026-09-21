# app/pipelines/webartsy/company/work_items.py

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WebArtsyCompanyWorkItem:
    company_id: int
    name: str
    website: str | None
    domain: str | None