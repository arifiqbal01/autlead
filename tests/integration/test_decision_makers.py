# tests/integration/people/test_decision_makers.py

from __future__ import annotations

import pytest
from sqlalchemy import select
from datetime import UTC, datetime
from app.extract.people.website import (
    extract_people_from_website,
    find_people_page_urls,
)
from app.models.persistence.person import Person
from app.models.persistence.person_observation import PersonObservation
from app.models.schemas import DiscoveryQuery
from app.models.schemas.crawling import CrawlRequest
from app.pipelines.common.people import find_decision_makers
from app.providers.crawling.crawl4ai_provider import (
    Crawl4AICrawlingProvider,
)
from app.providers.crawling.exceptions import CrawlingProviderError
from app.providers.discovery.gosom import (
    GosomGoogleMapsDiscoveryProvider,
)
from app.transform.normalization.person import normalize_person


@pytest.mark.asyncio
@pytest.mark.integration
async def test_real_dutch_decision_maker_pipeline(
    session,
    company,
) -> None:
    """
    Run the real Dutch people and decision-maker flow.

    Flow:

        Google Maps discovery
            ↓
        website crawl
            ↓
        people extraction
            ↓
        person normalization
            ↓
        decision-maker resolution/scoring
            ↓
        Person persistence
            ↓
        PersonObservation persistence
    """

    discovery = GosomGoogleMapsDiscoveryProvider()

    businesses = await discovery.discover(
        DiscoveryQuery(
            query="tandartsen",
            location="Amsterdam, Nederland",
            limit=3,
        ),
    )

    businesses = [
        business
        for business in businesses
        if business.website
    ]

    assert businesses, (
        "Discovery returned no Dutch businesses with websites."
    )

    crawler = Crawl4AICrawlingProvider(
        headless=True,
        timeout_seconds=30,
    )

    all_people = []

    for business in businesses:
        try:
            content = await crawler.crawl(
                CrawlRequest(
                    url=business.website,
                    timeout=30,
                ),
            )
        except CrawlingProviderError:
            continue

        people = extract_people_from_website(
            text=content.text,
            html=content.html,
            source_url=str(content.url),
            language="nl",
        )

        people = [
            normalize_person(
                person,
                language="nl",
            )
            for person in people
        ]

        all_people.extend(people)

        people_pages = find_people_page_urls(
            html=content.html,
            source_url=str(content.url),
            language="nl",
        )

        for page_url in people_pages:
            try:
                page = await crawler.crawl(
                    CrawlRequest(
                        url=page_url,
                        timeout=30,
                    ),
                )
            except CrawlingProviderError:
                continue

            page_people = extract_people_from_website(
                text=page.text,
                html=page.html,
                source_url=str(page.url),
                language="nl",
            )

            page_people = [
                normalize_person(
                    person,
                    language="nl",
                )
                for person in page_people
            ]

            all_people.extend(page_people)

    assert all_people, (
        "Real Dutch websites produced no people."
    )

    decision_makers = find_decision_makers(
        all_people,
    )

    assert decision_makers, (
        "No decision makers were found from the real Dutch websites."
    )

    print(f"\n{'=' * 80}")
    print(f"Businesses discovered: {len(businesses)}")
    print(f"People extracted: {len(all_people)}")
    print(f"Decision makers: {len(decision_makers)}")

    for decision_maker in decision_makers:
        print(
            "Decision maker: "
            f"name={decision_maker.person.name!r}, "
            f"title={decision_maker.person.title!r}, "
            f"score={decision_maker.score}, "
            f"role_group={decision_maker.role_group!r}, "
            f"confidence={decision_maker.confidence!r}, "
            f"reasons={decision_maker.reasons!r}"
        )

    # ---------------------------------------------------------
    # Persist the first discovered company/person set.
    #
    # The fixture company is used as the persistence target,
    # following the pattern used by the other integration tests.
    # ---------------------------------------------------------

    company.name = businesses[0].name
    company.normalized_name = businesses[0].name.lower()
    company.website = str(businesses[0].website)

    session.add(company)
    await session.flush()

    persisted_people: list[Person] = []

    observed_at = datetime.now(UTC)

    for decision_maker in decision_makers:
        person_candidate = decision_maker.person

        person = Person(
            company_id=company.id,
            name=person_candidate.name,
            normalized_name=person_candidate.name.casefold(),
            title=person_candidate.title,
            linkedin_url=(
                str(person_candidate.linkedin_url)
                if person_candidate.linkedin_url
                else None
            ),
        )

        session.add(person)
        await session.flush()

        observation = PersonObservation(
            person_id=person.id,
            company_id=company.id,
            provider_name="website",
            source_url=(
                str(person_candidate.source_url)
                if person_candidate.source_url
                else None
            ),
            name=person_candidate.name,
            title=person_candidate.title,
            linkedin_url=(
                str(person_candidate.linkedin_url)
                if person_candidate.linkedin_url
                else None
            ),
            decision_maker_score=decision_maker.score,
            decision_maker_role_group=decision_maker.role_group,
            decision_maker_confidence=decision_maker.confidence,
            decision_maker_reasons=decision_maker.reasons_text,
            observed_at=observed_at,
        )

        session.add(observation)

        persisted_people.append(person)

    await session.commit()

    # ---------------------------------------------------------
    # Verify Person persistence.
    # ---------------------------------------------------------

    people_rows = list(
        (
            await session.scalars(
                select(Person)
                .where(
                    Person.company_id == company.id,
                )
                .order_by(Person.id)
            )
        ).all()
    )

    assert len(people_rows) == len(decision_makers)

    print(
        f"Persisted people: {len(people_rows)}"
    )

    # ---------------------------------------------------------
    # Verify PersonObservation persistence.
    # ---------------------------------------------------------

    observations = list(
        (
            await session.scalars(
                select(PersonObservation)
                .where(
                    PersonObservation.company_id == company.id,
                )
                .order_by(PersonObservation.id)
            )
        ).all()
    )

    assert len(observations) == len(decision_makers)

    for observation in observations:
        assert observation.person_id is not None
        assert observation.company_id == company.id
        assert observation.provider_name == "website"

        assert observation.name
        assert observation.decision_maker_score is not None
        assert observation.decision_maker_role_group in {
            "primary",
            "secondary",
        }
        assert observation.decision_maker_confidence in {
            "high",
            "medium",
        }
        assert observation.decision_maker_reasons

    print(
        f"Persisted decision-maker observations: "
        f"{len(observations)}"
    )

    # ---------------------------------------------------------
    # Verify persisted values against transformation results.
    # ---------------------------------------------------------

    for decision_maker, observation in zip(
        decision_makers,
        observations,
        strict=True,
    ):
        assert observation.name == decision_maker.person.name
        assert observation.title == decision_maker.person.title

        assert (
            observation.decision_maker_score
            == decision_maker.score
        )

        assert (
            observation.decision_maker_role_group
            == decision_maker.role_group
        )

        assert (
            observation.decision_maker_confidence
            == decision_maker.confidence
        )

        assert (
            observation.decision_maker_reasons
            == decision_maker.reasons_text
        )

    print(f"\n{'=' * 80}")
    print("Real Dutch decision-maker integration test passed.")