from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import HttpUrl

import app.pipelines.common.contacts as contacts_pipeline
from app.models.schemas.contacts import (
    ContactEvidence,
    ContactExtractionResult,
)


@pytest.mark.asyncio
async def test_analyze_contacts_extracts_normalizes_and_persists() -> None:
    extracted = ContactExtractionResult(
        emails=["INFO@Example.com"],
        phones=["0333 2142260"],
        linkedin_company_urls=[
            HttpUrl("https://www.linkedin.com/company/example/"),
        ],
        evidence=[
            ContactEvidence(
                value="INFO@Example.com",
                source_url=HttpUrl("https://example.com/contact"),
                kind="email",
            ),
            ContactEvidence(
                value="0333 2142260",
                source_url=HttpUrl("https://example.com/contact"),
                kind="phone",
            ),
            ContactEvidence(
                value="https://www.linkedin.com/company/example/",
                source_url=HttpUrl("https://example.com/contact"),
                kind="linkedin_company",
            ),
        ],
    )

    session = AsyncMock()

    with (
        patch.object(
            contacts_pipeline.WebsiteContactExtractor,
            "extract",
            return_value=extracted,
        ) as mock_extract,
        patch.object(
            contacts_pipeline,
            "load_contact_observation",
            new_callable=AsyncMock,
        ) as mock_load,
    ):
        result = await contacts_pipeline.analyze_contacts(
            session=session,
            company_id=1,
            pages=[],
            provider_name="website",
            phone_region="PK",
            source_id=10,
        )

    mock_extract.assert_called_once_with([])

    assert result.persisted_count == 3

    assert result.contacts.emails == [
        "info@example.com",
    ]

    assert result.contacts.phones == [
        "+923332142260",
    ]

    assert result.contacts.linkedin_company_urls == [
        "https://linkedin.com/company/example",
    ]

    assert mock_load.await_count == 3

    calls = mock_load.await_args_list

    assert calls[0].kwargs["company_id"] == 1
    assert calls[0].kwargs["source_id"] == 10
    assert calls[0].kwargs["provider_name"] == "website"
    assert calls[0].kwargs["kind"] == "email"
    assert calls[0].kwargs["value"] == "INFO@Example.com"
    assert calls[0].kwargs["normalized_value"] == "info@example.com"
    assert calls[0].kwargs["source_url"] == (
        "https://example.com/contact"
    )

    assert calls[1].kwargs["company_id"] == 1
    assert calls[1].kwargs["source_id"] == 10
    assert calls[1].kwargs["provider_name"] == "website"
    assert calls[1].kwargs["kind"] == "phone"
    assert calls[1].kwargs["value"] == "0333 2142260"
    assert calls[1].kwargs["normalized_value"] == (
        "+923332142260"
    )
    assert calls[1].kwargs["source_url"] == (
        "https://example.com/contact"
    )

    assert calls[2].kwargs["company_id"] == 1
    assert calls[2].kwargs["source_id"] == 10
    assert calls[2].kwargs["provider_name"] == "website"
    assert calls[2].kwargs["kind"] == "linkedin_company"
    assert calls[2].kwargs["value"] == (
        "https://www.linkedin.com/company/example/"
    )
    assert calls[2].kwargs["normalized_value"] == (
        "https://linkedin.com/company/example"
    )
    assert calls[2].kwargs["source_url"] == (
        "https://example.com/contact"
    )

    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_analyze_contacts_discards_invalid_contacts() -> None:
    extracted = ContactExtractionResult(
        evidence=[
            ContactEvidence(
                value="not-an-email",
                source_url=HttpUrl("https://example.com/contact"),
                kind="email",
            ),
            ContactEvidence(
                value="not-a-phone",
                source_url=HttpUrl("https://example.com/contact"),
                kind="phone",
            ),
            ContactEvidence(
                value="https://example.com/not-social",
                source_url=HttpUrl("https://example.com/contact"),
                kind="instagram",
            ),
        ],
    )

    session = AsyncMock()

    with (
        patch.object(
            contacts_pipeline.WebsiteContactExtractor,
            "extract",
            return_value=extracted,
        ),
        patch.object(
            contacts_pipeline,
            "load_contact_observation",
            new_callable=AsyncMock,
        ) as mock_load,
    ):
        result = await contacts_pipeline.analyze_contacts(
            session=session,
            company_id=1,
            pages=[],
            provider_name="website",
            phone_region="PK",
        )

    assert result.persisted_count == 0
    assert result.contacts.emails == []
    assert result.contacts.phones == []
    assert result.contacts.instagram_urls == []
    assert result.contacts.evidence == []

    mock_load.assert_not_awaited()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_analyze_contacts_commits_after_persistence() -> None:
    extracted = ContactExtractionResult(
        evidence=[
            ContactEvidence(
                value="info@example.com",
                source_url=HttpUrl("https://example.com/contact"),
                kind="email",
            ),
        ],
    )

    session = AsyncMock()

    with (
        patch.object(
            contacts_pipeline.WebsiteContactExtractor,
            "extract",
            return_value=extracted,
        ),
        patch.object(
            contacts_pipeline,
            "load_contact_observation",
            new_callable=AsyncMock,
        ) as mock_load,
    ):
        result = await contacts_pipeline.analyze_contacts(
            session=session,
            company_id=1,
            pages=[],
            provider_name="website",
        )

    assert result.persisted_count == 1
    mock_load.assert_awaited_once()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_analyze_contacts_does_not_crawl_website() -> None:
    extractor = Mock()
    extractor.extract.return_value = ContactExtractionResult()

    session = AsyncMock()

    with (
        patch.object(
            contacts_pipeline,
            "WebsiteContactExtractor",
            return_value=extractor,
        ),
        patch.object(
            contacts_pipeline,
            "load_contact_observation",
            new_callable=AsyncMock,
        ),
    ):
        result = await contacts_pipeline.analyze_contacts(
            session=session,
            company_id=1,
            pages=[],
            provider_name="website",
        )

    extractor.extract.assert_called_once_with([])

    assert result.persisted_count == 0