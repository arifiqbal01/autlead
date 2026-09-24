from __future__ import annotations

import pytest

from app.extract.contacts import WebsiteContactExtractor
from app.extract.contacts.phone import phone_identity
from app.models.schemas import DiscoveryQuery
from app.models.schemas.crawling import CrawlRequest
from app.providers.crawling.crawl4ai_provider import Crawl4AICrawlingProvider
from app.providers.crawling.exceptions import CrawlingProviderError
from app.providers.discovery.gosom import GosomGoogleMapsDiscoveryProvider
from app.transform.normalization.email import normalize_emails
from app.transform.normalization.phone import normalize_phone


@pytest.mark.asyncio
@pytest.mark.integration
async def test_contact_extraction_from_real_websites() -> None:
    """
    Discover real businesses, crawl their websites, extract contacts,
    and apply country-aware phone and outreach normalization.

    Extraction produces raw contact candidates.

    Transformation:
        - normalizes emails
        - normalizes Pakistani phones to E.164

    This test does not verify whether outreach mailboxes actually exist.
    """

    discovery_query = DiscoveryQuery(
        query="dentists",
        location="Lahore, Pakistan",
        limit=10,
    )

    # The discovery location determines the expected phone region.
    phone_region = "PK"

    discovery_provider = GosomGoogleMapsDiscoveryProvider()

    businesses = await discovery_provider.discover(discovery_query)

    assert businesses, "Discovery returned no businesses."

    businesses_with_websites = [
        business
        for business in businesses
        if business.website
    ]

    assert businesses_with_websites, (
        "Discovery returned no businesses with websites."
    )

    businesses = businesses_with_websites[:10]

    crawling_provider = Crawl4AICrawlingProvider(
        headless=True,
        timeout_seconds=30,
    )

    extractor = WebsiteContactExtractor()

    successful_crawls = 0
    failed_crawls = 0

    extracted_contacts = 0
    normalized_email_count = 0
    normalized_phone_count = 0

    for business in businesses:
        assert business.name
        assert business.website

        print(f"\n{'=' * 80}")
        print(f"Business: {business.name}")
        print(f"Website: {business.website}")

        try:
            request = CrawlRequest(
                url=business.website,
                timeout=30,
            )

            content = await crawling_provider.crawl(request)

        except CrawlingProviderError as exc:
            failed_crawls += 1
            print(f"Crawl failed: {exc}")
            continue

        successful_crawls += 1

        assert content.status_code is not None
        assert content.html
        assert content.text

        # ---------------------------------------------------------
        # Extraction
        # ---------------------------------------------------------

        result = extractor.extract([content])

        # ---------------------------------------------------------
        # Email transformation
        # ---------------------------------------------------------

        normalized_emails = normalize_emails(
            result.emails,
        )

        # ---------------------------------------------------------
        # Phone transformation
        # ---------------------------------------------------------

        normalized_phones: list[str] = []

        for phone in result.phones:
            normalized = normalize_phone(
                phone,
                region=phone_region,
            )

            if normalized is not None:
                normalized_phones.append(normalized)

        normalized_phones = sorted(set(normalized_phones))

        # ---------------------------------------------------------
        # Output
        # ---------------------------------------------------------

        print(f"Status: {content.status_code}")
        print(f"Title: {content.title}")
        print("Pages: 1")

        print(f"Emails extracted: {len(result.emails)}")
        print(f"Emails normalized: {len(normalized_emails)}")

        print(f"Phones extracted: {len(result.phones)}")
        print(f"Phones normalized: {len(normalized_phones)}")

        print(
            "LinkedIn company URLs: "
            f"{len(result.linkedin_company_urls)}"
        )
        print(
            "LinkedIn profile URLs: "
            f"{len(result.linkedin_profile_urls)}"
        )
        print(f"Facebook URLs: {len(result.facebook_urls)}")
        print(f"Instagram URLs: {len(result.instagram_urls)}")
        print(f"X URLs: {len(result.x_urls)}")
        print(f"YouTube URLs: {len(result.youtube_urls)}")
        print(f"GitHub URLs: {len(result.github_urls)}")
        print(f"TikTok URLs: {len(result.tiktok_urls)}")
        print(f"Evidence: {len(result.evidence)}")

        if result.emails:
            print(f"Emails extracted: {result.emails}")

        if normalized_emails:
            print(f"Emails normalized: {normalized_emails}")
            normalized_email_count += len(normalized_emails)

        if result.phones:
            print(f"Phones extracted: {result.phones}")

        if normalized_phones:
            print(
                f"Phones normalized ({phone_region}): "
                f"{normalized_phones}"
            )
            normalized_phone_count += len(normalized_phones)

        if result.linkedin_company_urls:
            print(
                "LinkedIn companies found: "
                f"{result.linkedin_company_urls}"
            )

        if result.linkedin_profile_urls:
            print(
                "LinkedIn profiles found: "
                f"{result.linkedin_profile_urls}"
            )

        if result.facebook_urls:
            print(f"Facebook found: {result.facebook_urls}")

        if result.instagram_urls:
            print(f"Instagram found: {result.instagram_urls}")

        if result.x_urls:
            print(f"X found: {result.x_urls}")

        if result.youtube_urls:
            print(f"YouTube found: {result.youtube_urls}")

        if result.github_urls:
            print(f"GitHub found: {result.github_urls}")

        if result.tiktok_urls:
            print(f"TikTok found: {result.tiktok_urls}")

        extracted_contacts += (
            len(result.emails)
            + len(result.phones)
            + len(result.linkedin_company_urls)
            + len(result.linkedin_profile_urls)
            + len(result.facebook_urls)
            + len(result.instagram_urls)
            + len(result.x_urls)
            + len(result.youtube_urls)
            + len(result.github_urls)
            + len(result.tiktok_urls)
        )

        # ---------------------------------------------------------
        # Structural assertions
        # ---------------------------------------------------------

        assert isinstance(result.emails, list)
        assert isinstance(result.phones, list)

        assert isinstance(result.linkedin_company_urls, list)
        assert isinstance(result.linkedin_profile_urls, list)
        assert isinstance(result.facebook_urls, list)
        assert isinstance(result.instagram_urls, list)
        assert isinstance(result.x_urls, list)
        assert isinstance(result.youtube_urls, list)
        assert isinstance(result.github_urls, list)
        assert isinstance(result.tiktok_urls, list)

        assert isinstance(result.evidence, list)

        # ---------------------------------------------------------
        # Extraction invariants
        # ---------------------------------------------------------

        assert len(result.emails) == len(set(result.emails))

        assert len(result.phones) == len(
            {
                phone_identity(phone)
                for phone in result.phones
            }
        )

        # ---------------------------------------------------------
        # Email transformation invariants
        # ---------------------------------------------------------

        assert len(normalized_emails) == len(
            set(normalized_emails)
        )

        for email in normalized_emails:
            assert email == email.lower()
            assert "@" in email

            local_part, domain = email.rsplit("@", 1)

            assert local_part
            assert domain
            assert "." in domain

        # Normalization must be deterministic.
        assert normalize_emails(
            result.emails,
        ) == normalize_emails(
            result.emails,
        )

        # Every normalized outreach must originate from an extracted outreach.
        assert set(normalized_emails) <= set(result.emails)

        # ---------------------------------------------------------
        # Phone transformation invariants
        # ---------------------------------------------------------

        for phone in normalized_phones:
            assert phone.startswith("+")
            assert phone[1:].isdigit()

            # E.164 maximum is 15 digits.
            assert 8 <= len(phone[1:]) <= 15

        for phone in result.phones:
            first = normalize_phone(
                phone,
                region=phone_region,
            )

            second = normalize_phone(
                phone,
                region=phone_region,
            )

            assert first == second

        assert len(normalized_phones) == len(
            set(normalized_phones)
        )

        # ---------------------------------------------------------
        # Social URL invariants
        # ---------------------------------------------------------

        social_url_lists = (
            result.linkedin_company_urls,
            result.linkedin_profile_urls,
            result.facebook_urls,
            result.instagram_urls,
            result.x_urls,
            result.youtube_urls,
            result.github_urls,
            result.tiktok_urls,
        )

        for urls in social_url_lists:
            assert len(urls) == len(
                set(map(str, urls))
            )

        # ---------------------------------------------------------
        # Evidence assertions
        # ---------------------------------------------------------

        for evidence in result.evidence:
            assert evidence.value
            assert evidence.source_url
            assert evidence.kind

            assert str(evidence.source_url) == str(content.url)

        evidence_by_kind = {
            "outreach": {
                evidence.value
                for evidence in result.evidence
                if evidence.kind == "outreach"
            },
            "phone": {
                evidence.value
                for evidence in result.evidence
                if evidence.kind == "phone"
            },
        }

        assert set(result.emails) <= evidence_by_kind["outreach"]
        assert set(result.phones) <= evidence_by_kind["phone"]

    # -------------------------------------------------------------
    # Test summary
    # -------------------------------------------------------------

    print(f"\n{'=' * 80}")
    print(f"Businesses tested: {len(businesses)}")
    print(f"Successful crawls: {successful_crawls}")
    print(f"Failed crawls: {failed_crawls}")
    print(f"Extracted contact values: {extracted_contacts}")
    print(f"Normalized emails: {normalized_email_count}")
    print(f"Normalized Pakistani phones: {normalized_phone_count}")

    assert successful_crawls > 0, (
        "None of the discovered websites could be crawled."
    )

    assert extracted_contacts > 0, (
        "Successful website crawls produced no contact information."
    )