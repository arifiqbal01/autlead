from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.persistence.contact_observation import ContactObservation
from app.models.persistence.website_crawl import WebsiteCrawl
from app.models.persistence.website_crawl_link import WebsiteCrawlLink
from app.models.persistence.website_crawl_state import WebsiteCrawlState
from app.pipelines.common.contacts import analyze_contacts
from app.pipelines.common.website_crawl import analyze_website
from app.providers.crawling.crawl4ai_provider import Crawl4AICrawlingProvider


@pytest.mark.asyncio
@pytest.mark.integration
async def test_website_to_contacts_pipeline(
    session,
    company,
) -> None:
    """Run website crawling and contact extraction against a real website."""

    assert company.website, (
        "Test company does not have a saved website. "
        "Use a company fixture populated with a real website."
    )

    website = str(company.website)

    print(f"\n{'=' * 80}")
    print(f"Company: {company.name}")
    print(f"Saved website: {website}")

    crawling_provider = Crawl4AICrawlingProvider(
        headless=True,
        timeout_seconds=30,
    )

    # First ensure we have a real persisted website crawl.
    crawl_result = await analyze_website(
        session,
        company_id=company.id,
        website=website,
        provider=crawling_provider,
        retention_days=30,
        timeout=30,
    )

    assert crawl_result.content.html
    assert crawl_result.content.text

    print(f"Website status: {crawl_result.content.status_code}")
    print(f"Title: {crawl_result.content.title}")
    print(f"HTML: {len(crawl_result.content.html or '')}")
    print(f"Text: {len(crawl_result.content.text or '')}")
    print(f"Links: {len(crawl_result.content.links)}")

    # Verify the crawl was persisted.
    state = await session.scalar(
        select(WebsiteCrawlState).where(
            WebsiteCrawlState.company_id == company.id,
        )
    )

    assert state is not None
    assert state.last_crawl_id is not None

    crawl = await session.get(
        WebsiteCrawl,
        state.last_crawl_id,
    )

    assert crawl is not None
    assert crawl.company_id == company.id
    assert crawl.html
    assert crawl.text

    print(f"Persisted crawl ID: {crawl.id}")

    # Run the real contact extraction pipeline against the
    # already-crawled website content.
    result = await analyze_contacts(
        session,
        company_id=company.id,
        pages=[crawl_result.content],
        provider_name=crawling_provider.provider_name,
    )

    print(f"Emails: {len(result.contacts.emails)}")
    print(f"Phones: {len(result.contacts.phones)}")
    print(
        "LinkedIn company URLs: "
        f"{len(result.contacts.linkedin_company_urls)}"
    )
    print(
        "LinkedIn profile URLs: "
        f"{len(result.contacts.linkedin_profile_urls)}"
    )
    print(f"Facebook URLs: {len(result.contacts.facebook_urls)}")
    print(f"Instagram URLs: {len(result.contacts.instagram_urls)}")
    print(f"X URLs: {len(result.contacts.x_urls)}")
    print(f"YouTube URLs: {len(result.contacts.youtube_urls)}")
    print(f"GitHub URLs: {len(result.contacts.github_urls)}")
    print(f"TikTok URLs: {len(result.contacts.tiktok_urls)}")

    print(f"Persisted observations: {result.persisted_count}")

    # The pipeline should complete successfully even when a website
    # contains no contact information.
    assert result.persisted_count >= 0

    # Verify persisted contact observations.
    observations = list(
        (
            await session.scalars(
                select(ContactObservation)
                .where(
                    ContactObservation.company_id == company.id,
                )
                .order_by(ContactObservation.id)
            )
        ).all()
    )

    assert len(observations) == result.persisted_count

    for observation in observations:
        assert observation.company_id == company.id
        assert observation.provider_name == (
            crawling_provider.provider_name
        )
        assert observation.kind
        assert observation.value
        assert observation.normalized_value
        assert observation.observed_at is not None

    print(
        f"Verified persisted contact observations: "
        f"{len(observations)}"
    )

    # Verify every persisted observation has a source URL.
    # Website contact evidence comes from crawled pages.
    for observation in observations:
        assert observation.source_url

    # Show the discovered contacts for manual validation.
    if result.contacts.emails:
        print("\nEmails:")
        for email in result.contacts.emails:
            print(f"  - {email}")

    if result.contacts.phones:
        print("\nPhones:")
        for phone in result.contacts.phones:
            print(f"  - {phone}")

    if result.contacts.linkedin_company_urls:
        print("\nLinkedIn company:")
        for url in result.contacts.linkedin_company_urls:
            print(f"  - {url}")

    if result.contacts.linkedin_profile_urls:
        print("\nLinkedIn profiles:")
        for url in result.contacts.linkedin_profile_urls:
            print(f"  - {url}")

    if result.contacts.instagram_urls:
        print("\nInstagram:")
        for url in result.contacts.instagram_urls:
            print(f"  - {url}")

    if result.contacts.facebook_urls:
        print("\nFacebook:")
        for url in result.contacts.facebook_urls:
            print(f"  - {url}")

    if result.contacts.x_urls:
        print("\nX:")
        for url in result.contacts.x_urls:
            print(f"  - {url}")

    print(f"\n{'=' * 80}")
    print("Website contact integration test passed.")