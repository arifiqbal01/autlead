# app/pipelines/enrichment/contacts.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.extract.contacts.website import WebsiteContactExtractor
from app.load.postgres.contacts import load_contact_observation
from app.models.schemas.contacts import (
    ContactEvidence,
    ContactExtractionResult,
)
from app.models.schemas.crawling import WebsiteContent
from app.transform.normalization.email import normalize_email
from app.transform.normalization.phone import normalize_phone
from app.transform.normalization.social import normalize_social_url


logger = get_logger(__name__)


SOCIAL_KINDS = frozenset(
    {
        "linkedin_company",
        "linkedin_profile",
        "facebook",
        "instagram",
        "x",
        "youtube",
        "github",
        "tiktok",
    }
)


@dataclass(frozen=True, slots=True)
class ContactAnalysisResult:
    contacts: ContactExtractionResult

    extracted_count: int
    normalized_count: int
    discarded_count: int
    persisted_count: int


async def analyze_contacts(
    *,
    session: AsyncSession,
    company_id: int,
    pages: list[WebsiteContent],
    provider_name: str,
    phone_region: str | None = None,
    source_id: int | None = None,
    observed_at: datetime | None = None,
) -> ContactAnalysisResult:
    """
    Extract, normalize, deduplicate, and persist company-level
    contacts from already-crawled website pages.

    Flow:

        WebsiteContent[]
            ↓
        WebsiteContactExtractor
            ↓
        ContactEvidence[]
            ↓
        normalization
            ↓
        deduplication
            ↓
        persistence

    This function does not crawl websites.

    Transaction ownership belongs to the caller.
    """

    if observed_at is None:
        observed_at = datetime.now(UTC)

    logger.info(
        "contact_analysis_started",
        company_id=company_id,
        pages=len(pages),
        provider=provider_name,
    )

    # ------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------

    extractor = WebsiteContactExtractor()

    extracted = extractor.extract(
        pages
    )

    extracted_count = len(
        extracted.evidence
    )

    logger.info(
        "contact_extraction_completed",
        company_id=company_id,
        pages=len(pages),
        evidence_found=extracted_count,
    )

    # ------------------------------------------------------------------
    # Normalization + deduplication
    # ------------------------------------------------------------------

    normalized_contacts, discarded_count = _normalize_result(
        extracted,
        phone_region=phone_region,
    )

    normalized_count = len(
        normalized_contacts.evidence
    )

    logger.info(
        "contact_normalization_completed",
        company_id=company_id,
        extracted=extracted_count,
        normalized=normalized_count,
        discarded=discarded_count,
    )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    persisted_count = 0

    for evidence in normalized_contacts.evidence:
        await load_contact_observation(
            session=session,
            company_id=company_id,
            source_id=source_id,
            provider_name=provider_name,
            kind=evidence.kind,
            value=evidence.value,
            normalized_value=evidence.value,
            source_url=str(evidence.source_url),
            observed_at=observed_at,
        )

        persisted_count += 1

    # ------------------------------------------------------------------
    # Completed
    # ------------------------------------------------------------------

    result = ContactAnalysisResult(
        contacts=normalized_contacts,
        extracted_count=extracted_count,
        normalized_count=normalized_count,
        discarded_count=discarded_count,
        persisted_count=persisted_count,
    )

    logger.info(
        "contact_analysis_completed",
        company_id=company_id,
        pages=len(pages),
        extracted=result.extracted_count,
        normalized=result.normalized_count,
        discarded=result.discarded_count,
        persisted=result.persisted_count,
        emails=len(result.contacts.emails),
        phones=len(result.contacts.phones),
        linkedin_companies=len(
            result.contacts.linkedin_company_urls
        ),
        linkedin_profiles=len(
            result.contacts.linkedin_profile_urls
        ),
        facebook=len(
            result.contacts.facebook_urls
        ),
        instagram=len(
            result.contacts.instagram_urls
        ),
        x=len(
            result.contacts.x_urls
        ),
        youtube=len(
            result.contacts.youtube_urls
        ),
        github=len(
            result.contacts.github_urls
        ),
        tiktok=len(
            result.contacts.tiktok_urls
        ),
    )

    return result


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def _normalize_result(
    result: ContactExtractionResult,
    *,
    phone_region: str | None,
) -> tuple[
    ContactExtractionResult,
    int,
]:
    """
    Normalize and deduplicate extracted contacts.

    Identity:
        (kind, normalized_value)

    The source URL from the first accepted observation is retained.
    """

    normalized = ContactExtractionResult()

    seen: set[
        tuple[str, str]
    ] = set()

    discarded_count = 0

    for evidence in result.evidence:
        normalized_value = _normalize_contact_value(
            kind=evidence.kind,
            value=evidence.value,
            phone_region=phone_region,
        )

        if normalized_value is None:
            discarded_count += 1
            continue

        identity = (
            evidence.kind,
            normalized_value,
        )

        if identity in seen:
            continue

        seen.add(identity)

        normalized_evidence = evidence.model_copy(
            update={
                "value": normalized_value,
            }
        )

        normalized.evidence.append(
            normalized_evidence
        )

        _append_contact_value(
            result=normalized,
            evidence=normalized_evidence,
        )

    return (
        normalized,
        discarded_count,
    )


def _normalize_contact_value(
    *,
    kind: str,
    value: str,
    phone_region: str | None,
) -> str | None:
    """Normalize one contact according to its contact kind."""

    if kind == "outreach":
        return normalize_email(
            value
        )

    if kind == "phone":
        return normalize_phone(
            value,
            region=phone_region,
        )

    if kind in SOCIAL_KINDS:
        return normalize_social_url(
            value
        )

    return None


# ---------------------------------------------------------------------------
# Result building
# ---------------------------------------------------------------------------


def _append_contact_value(
    *,
    result: ContactExtractionResult,
    evidence: ContactEvidence,
) -> None:
    """Add a normalized value to the appropriate result collection."""

    value = evidence.value
    kind = evidence.kind

    if kind == "outreach":
        result.emails.append(
            value
        )

    elif kind == "phone":
        result.phones.append(
            value
        )

    elif kind == "linkedin_company":
        result.linkedin_company_urls.append(
            value
        )

    elif kind == "linkedin_profile":
        result.linkedin_profile_urls.append(
            value
        )

    elif kind == "facebook":
        result.facebook_urls.append(
            value
        )

    elif kind == "instagram":
        result.instagram_urls.append(
            value
        )

    elif kind == "x":
        result.x_urls.append(
            value
        )

    elif kind == "youtube":
        result.youtube_urls.append(
            value
        )

    elif kind == "github":
        result.github_urls.append(
            value
        )

    elif kind == "tiktok":
        result.tiktok_urls.append(
            value
        )