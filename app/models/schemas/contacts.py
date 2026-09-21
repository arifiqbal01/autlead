from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


class ContactEvidence(BaseModel):
    """A single contact value found on a crawled page."""

    value: str
    source_url: HttpUrl
    kind: str


class ContactExtractionResult(BaseModel):
    """Contacts and social profiles extracted from crawled website pages."""

    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)

    linkedin_company_urls: list[HttpUrl] = Field(default_factory=list)
    linkedin_profile_urls: list[HttpUrl] = Field(default_factory=list)

    facebook_urls: list[HttpUrl] = Field(default_factory=list)
    instagram_urls: list[HttpUrl] = Field(default_factory=list)
    x_urls: list[HttpUrl] = Field(default_factory=list)
    youtube_urls: list[HttpUrl] = Field(default_factory=list)
    github_urls: list[HttpUrl] = Field(default_factory=list)
    tiktok_urls: list[HttpUrl] = Field(default_factory=list)

    evidence: list[ContactEvidence] = Field(default_factory=list)