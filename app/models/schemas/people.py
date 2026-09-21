from __future__ import annotations

from pydantic import BaseModel, HttpUrl


class PersonCandidate(BaseModel):
    """A person discovered from an external source."""

    name: str
    title: str | None = None
    linkedin_url: HttpUrl | None = None
    source_url: HttpUrl