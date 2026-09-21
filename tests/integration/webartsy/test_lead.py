# tests/integration/webartsy/test_lead.py

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.bootstrap.providers import (
    create_pagespeed_provider,
)
from app.models.persistence.contact_observation import (
    ContactObservation,
)
from app.models.persistence.person import Person
from app.models.persistence.person_observation import (
    PersonObservation,
)
from app.models.persistence.technology_observation import (
    TechnologyObservation,
)
from app.models.persistence.website_crawl import WebsiteCrawl
from app.models.persistence.website_crawl_state import (
    WebsiteCrawlState,
)
from app.models.persistence.website_performance import (
    WebsitePerformance,
)
from app.models.schemas import DiscoveryQuery
from app.pipelines.webartsy.lead import (
    run_webartsy_lead_pipeline,
)
from app.providers.crawling.crawl4ai_provider import (
    Crawl4AICrawlingProvider,
)
from app.providers.discovery.gosom import (
    GosomGoogleMapsDiscoveryProvider,
)
from app.providers.technology import (
    create_technology_detection_provider,
)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_real_webartsy_lead_pipeline(
    session,
) -> None:
    """
    Run the complete WebArtsy lead pipeline against real providers.

    Flow:

        Discovery
            ↓
        Company persistence
            ↓
        Technology Detection
            ↓
        Performance / SEO
            ↓
        Website Analysis
            ↓
        Contact Discovery
            ↓
        People Extraction
            ↓
        Decision Makers
            ↓
        PostgreSQL persistence

    Company-level website failures are allowed. A real website may
    reject crawling with HTTP 403, timeout, anti-bot protection, etc.
    Such failures should be recorded by the pipeline without
    terminating the entire run.
    """

    # ---------------------------------------------------------
    # Real providers
    # ---------------------------------------------------------

    discovery_provider = GosomGoogleMapsDiscoveryProvider()

    crawler_provider = Crawl4AICrawlingProvider(
        headless=True,
        timeout_seconds=30,
    )

    performance_provider = create_pagespeed_provider()
    seo_provider = performance_provider

    technology_provider = create_technology_detection_provider()

    # ---------------------------------------------------------
    # Discovery
    # ---------------------------------------------------------

    query = DiscoveryQuery(
        query="web design agencies",
        location="Amsterdam, Nederland",
        limit=3,
    )

    print(f"\n{'=' * 80}")
    print("Starting WebArtsy integration pipeline")
    print(f"Query: {query.query}")
    print(f"Location: {query.location}")

    result = await run_webartsy_lead_pipeline(
        session=session,
        discovery_provider=discovery_provider,
        query=query,
        crawler_provider=crawler_provider,
        technology_provider=technology_provider,
        performance_provider=performance_provider,
        seo_provider=seo_provider,
        phone_region="NL",
        source_id=None,
        retention_days=30,
        timeout=30,
        decision_maker_limit=5,
    )

    # ---------------------------------------------------------
    # Pipeline result
    # ---------------------------------------------------------

    assert result is not None
    assert result.discovery is not None

    print("\nDiscovery")
    print(f"  Found: {result.discovery.found}")
    print(f"  New: {result.discovery.new}")
    print(f"  Duplicates: {result.discovery.duplicates}")
    print(f"  Stored: {result.discovery.stored}")

    assert result.discovery.found > 0
    assert result.discovery.stored > 0

    # ---------------------------------------------------------
    # Company-level failures
    # ---------------------------------------------------------

    print("\nCompany failures:")

    if not result.failures:
        print("  None")

    for failure in result.failures:
        print(
            f"  - {failure.company_name} "
            f"({failure.website})"
        )
        print(
            f"    company_id={failure.company_id}"
        )
        print(
            f"    stage={failure.stage}"
        )
        print(
            f"    error_type={failure.error_type}"
        )
        print(
            f"    error={failure.error_message}"
        )

    assert result.companies_failed >= 0

    # ---------------------------------------------------------
    # Company-level successful results
    # ---------------------------------------------------------

    print("\nCompanies successfully analyzed:")

    for company_result in result.companies:
        print(
            f"  - {company_result.company_name} "
            f"({company_result.website})"
        )

    assert (
        result.companies_analyzed
        + result.companies_failed
        <= result.discovery.found
    )

    # At least one company must successfully complete the
    # website-dependent part of the pipeline for this integration
    # test to validate the downstream stages.
    assert result.companies

    # ---------------------------------------------------------
    # Inspect successful companies
    # ---------------------------------------------------------

    for company_result in result.companies:

        print(f"\n{'-' * 80}")
        print(
            f"Company: {company_result.company_name}"
        )
        print(
            f"Website: {company_result.website}"
        )

        # -----------------------------------------------------
        # Website analysis
        # -----------------------------------------------------

        assert company_result.website_analysis is not None

        website_result = company_result.website_analysis

        assert website_result.content is not None
        assert website_result.content.html
        assert website_result.content.text

        print(
            f"Website status: "
            f"{website_result.content.status_code}"
        )

        print(
            f"Title: "
            f"{website_result.content.title}"
        )

        print(
            f"HTML: "
            f"{len(website_result.content.html or '')}"
        )

        print(
            f"Text: "
            f"{len(website_result.content.text or '')}"
        )

        print(
            f"Links: "
            f"{len(website_result.content.links)}"
        )

        # -----------------------------------------------------
        # Contacts
        # -----------------------------------------------------

        contacts = company_result.contacts

        assert contacts is not None

        print(
            f"Emails: {len(contacts.contacts.emails)}"
        )

        print(
            f"Phones: {len(contacts.contacts.phones)}"
        )

        print(
            "LinkedIn company URLs: "
            f"{len(contacts.contacts.linkedin_company_urls)}"
        )

        print(
            "LinkedIn profile URLs: "
            f"{len(contacts.contacts.linkedin_profile_urls)}"
        )

        # Contact extraction may legitimately find nothing.

        # -----------------------------------------------------
        # People
        # -----------------------------------------------------

        print(
            f"People extracted: "
            f"{len(company_result.people)}"
        )

        for person in company_result.people:
            print(
                "  Person: "
                f"name={person.name!r}, "
                f"title={person.title!r}, "
                f"linkedin={person.linkedin_url!r}"
            )

        assert company_result.people is not None

        # -----------------------------------------------------
        # Decision makers
        # -----------------------------------------------------

        print(
            "Decision makers: "
            f"{len(company_result.decision_makers)}"
        )

        for decision_maker in (
            company_result.decision_makers
        ):
            print(
                "  Decision maker: "
                f"name={decision_maker.person.name!r}, "
                f"title={decision_maker.person.title!r}, "
                f"score={decision_maker.score}, "
                f"role={decision_maker.role_group}, "
                f"confidence={decision_maker.confidence}, "
                f"reasons={decision_maker.reasons!r}"
            )

        assert company_result.decision_makers is not None

    # ---------------------------------------------------------
    # Aggregate pipeline metrics
    # ---------------------------------------------------------

    print(f"\n{'=' * 80}")
    print("Pipeline totals")
    print(
        f"Companies discovered: "
        f"{result.discovery.found}"
    )
    print(
        f"Companies analyzed: "
        f"{result.companies_analyzed}"
    )
    print(
        f"Companies failed: "
        f"{result.companies_failed}"
    )
    print(
        f"People found: "
        f"{result.people_found}"
    )
    print(
        f"Decision makers found: "
        f"{result.decision_makers_found}"
    )

    assert result.companies_analyzed > 0
    assert result.people_found >= 0
    assert result.decision_makers_found >= 0

    # ---------------------------------------------------------
    # PostgreSQL: website crawls
    # ---------------------------------------------------------

    crawl_count = await session.scalar(
        select(WebsiteCrawl.id).limit(1)
    )

    assert crawl_count is not None

    crawl_state = await session.scalar(
        select(WebsiteCrawlState.id).limit(1)
    )

    assert crawl_state is not None

    print(
        "\nPostgreSQL website crawl persistence: OK"
    )

    # ---------------------------------------------------------
    # PostgreSQL: performance
    # ---------------------------------------------------------

    performance = await session.scalar(
        select(WebsitePerformance.id).limit(1)
    )

    assert performance is not None

    print(
        "PostgreSQL website performance "
        "persistence: OK"
    )

    # ---------------------------------------------------------
    # PostgreSQL: technology observations
    #
    # Technology detection can legitimately return zero.
    # ---------------------------------------------------------

    technology_count = await session.scalar(
        select(TechnologyObservation.id).limit(1)
    )

    print(
        "Technology observation query completed: "
        f"{technology_count is not None}"
    )

    # ---------------------------------------------------------
    # PostgreSQL: contacts
    # ---------------------------------------------------------

    contact_count = await session.scalar(
        select(ContactObservation.id).limit(1)
    )

    print(
        "Contact observation query completed: "
        f"{contact_count is not None}"
    )

    # ---------------------------------------------------------
    # PostgreSQL: people
    # ---------------------------------------------------------

    people_count = await session.scalar(
        select(Person.id).limit(1)
    )

    print(
        "Person persistence query completed: "
        f"{people_count is not None}"
    )

    # ---------------------------------------------------------
    # PostgreSQL: decision-maker observations
    # ---------------------------------------------------------

    decision_maker_count = await session.scalar(
        select(PersonObservation.id)
        .where(
            PersonObservation.decision_maker_score.is_not(None)
        )
        .limit(1)
    )

    print(
        "Decision-maker observation query completed: "
        f"{decision_maker_count is not None}"
    )

    # ---------------------------------------------------------
    # Final
    # ---------------------------------------------------------

    print(f"\n{'=' * 80}")
    print(
        "Real WebArtsy lead integration test passed."
    )