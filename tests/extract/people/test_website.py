# tests/extract/people/test_website.py

from __future__ import annotations

from urllib.parse import urlparse

import pytest

from app.extract.people.website import (
    extract_people_from_website,
    find_people_page_urls,
)
from app.models.schemas import DiscoveryQuery
from app.models.schemas.crawling import CrawlRequest
from app.pipelines.common.people import (
    DecisionMaker,
    find_decision_makers,
)
from app.providers.crawling.crawl4ai_provider import (
    Crawl4AICrawlingProvider,
)
from app.providers.crawling.exceptions import (
    CrawlingProviderError,
)
from app.providers.discovery.gosom import (
    GosomGoogleMapsDiscoveryProvider,
)
from app.transform.normalization.person import (
    normalize_person,
    person_identity,
)


# ---------------------------------------------------------------------------
# Known extraction false positives
# ---------------------------------------------------------------------------
#
# These are real-world artifacts observed during live website testing.
#
# They should never become valid person candidates.
#
# Keep this list deliberately small and evidence-based. It represents
# regression protection for bugs already observed in production-like data.
# ---------------------------------------------------------------------------

KNOWN_FALSE_POSITIVE_NAMES = frozenset(
    {
        "gdpr cookie consent",
        "tandarts-directeur big",
        "utrecht maliebaan",
        "lisa goené office",
        "illustratie dr",
    }
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalized_name(
    value: str,
) -> str:
    """Normalize name text for test assertions."""

    return " ".join(
        value.casefold().split()
    )


def _host(
    url: str,
) -> str:
    """Return a normalized hostname."""

    return (
        urlparse(url)
        .hostname
        or ""
    ).casefold()


def _assert_valid_people(
    people: list,
) -> None:
    """
    Validate the structural contract of extracted people.
    """

    for person in people:
        assert person.name
        assert person.source_url
        assert str(person.source_url)

        assert (
            _normalized_name(person.name)
            not in KNOWN_FALSE_POSITIVE_NAMES
        )

        if person.linkedin_url:
            linkedin_url = str(
                person.linkedin_url,
            )

            assert linkedin_url.startswith(
                "https://www.linkedin.com/in/",
            )

            assert "?" not in linkedin_url
            assert "#" not in linkedin_url


def _assert_no_duplicate_identities(
    people: list,
) -> None:
    """
    Verify extraction-level identities are unique.

    This is intentionally based on person_identity() rather than
    reproducing identity logic inside the test.
    """

    identities = [
        person_identity(
            person,
            language="nl",
        )
        for person in people
    ]

    assert len(identities) == len(
        set(identities),
    )


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.integration
async def test_people_extraction_from_real_websites() -> None:
    """
    Discover real Dutch businesses, crawl their websites, discover likely
    people/team pages, extract people, normalize them, and identify
    potential decision makers.

    Pipeline:

        Google Maps discovery
            ↓
        Homepage crawl
            ↓
        People-page discovery
            ↓
        People-page crawl
            ↓
        Person extraction
            ↓
        Person normalization
            ↓
        Entity resolution
            ↓
        Decision-maker scoring
            ↓
        Decision-maker selection

    Responsibilities:

        Discovery provider
            → discovers businesses

        Crawling provider
            → fetches website content

        Website people extractor
            → extracts person candidates
            → discovers likely people/team pages

        Normalization
            → canonicalizes person data

        Entity resolution
            → determines whether candidates represent the same person

        Scoring
            → evaluates decision-maker relevance

        Decision-maker selection
            → returns qualified decision makers

    This is an integration test and intentionally uses real external
    providers. It is not part of the fast unit-test loop.
    """

    # -------------------------------------------------------------
    # Discovery
    # -------------------------------------------------------------

    discovery_query = DiscoveryQuery(
        query="tandartsen",
        location="Nederland",
        limit=10,
    )

    discovery_provider = (
        GosomGoogleMapsDiscoveryProvider()
    )

    businesses = await discovery_provider.discover(
        discovery_query,
    )

    assert businesses, (
        "Discovery returned no businesses."
    )

    businesses_with_websites = [
        business
        for business in businesses
        if business.website
    ]

    assert businesses_with_websites, (
        "Discovery returned no businesses "
        "with websites."
    )

    businesses = businesses_with_websites[:10]

    # -------------------------------------------------------------
    # Crawling provider
    # -------------------------------------------------------------

    crawling_provider = (
        Crawl4AICrawlingProvider(
            headless=True,
            timeout_seconds=30,
        )
    )

    # -------------------------------------------------------------
    # Counters
    # -------------------------------------------------------------

    successful_homepage_crawls = 0
    failed_crawls = 0

    extracted_people = 0
    normalized_people = 0

    discovered_people_pages = 0
    crawled_people_pages = 0

    decision_makers_found = 0
    high_confidence_decision_makers = 0

    # -------------------------------------------------------------
    # Business loop
    # -------------------------------------------------------------

    for business in businesses:
        assert business.name
        assert business.website

        print(f"\n{'=' * 80}")
        print(
            f"Business: {business.name}",
        )
        print(
            f"Website: {business.website}",
        )

        # ---------------------------------------------------------
        # 1. Crawl homepage
        # ---------------------------------------------------------

        try:
            request = CrawlRequest(
                url=business.website,
                timeout=30,
            )

            content = await crawling_provider.crawl(
                request,
            )

        except CrawlingProviderError as exc:
            failed_crawls += 1

            print(
                "Homepage crawl failed: "
                f"{exc}",
            )

            continue

        successful_homepage_crawls += 1

        assert content.status_code is not None
        assert content.html
        assert content.text
        assert content.url

        source_url = str(
            content.url,
        )

        print(
            f"Status: {content.status_code}",
        )
        print(
            f"Title: {content.title}",
        )
        print(
            f"Source URL: {source_url}",
        )

        # ---------------------------------------------------------
        # 2. Extract people from homepage
        # ---------------------------------------------------------

        people = extract_people_from_website(
            text=content.text,
            html=content.html,
            source_url=source_url,
            language="nl",
        )

        # ---------------------------------------------------------
        # 3. Validate homepage extraction
        # ---------------------------------------------------------

        _assert_valid_people(
            people,
        )

        # ---------------------------------------------------------
        # 4. Discover likely people/team pages
        # ---------------------------------------------------------

        people_page_urls = find_people_page_urls(
            html=content.html,
            source_url=source_url,
            language="nl",
            max_results=12,
        )

        discovered_people_pages += len(
            people_page_urls,
        )

        print(
            "People pages discovered: "
            f"{len(people_page_urls)}",
        )

        for page_url in people_page_urls:
            print(
                f"People page: {page_url}",
            )

            # People pages must remain on the same host.
            assert _host(
                page_url,
            ) == _host(
                source_url,
            )

        # ---------------------------------------------------------
        # 5. Crawl discovered people pages
        # ---------------------------------------------------------

        for page_url in people_page_urls:
            try:
                page_request = CrawlRequest(
                    url=page_url,
                    timeout=30,
                )

                page_content = (
                    await crawling_provider.crawl(
                        page_request,
                    )
                )

            except CrawlingProviderError as exc:
                failed_crawls += 1

                print(
                    "People page crawl failed: "
                    f"{page_url} -> {exc}",
                )

                continue

            crawled_people_pages += 1

            assert page_content.status_code is not None
            assert page_content.html
            assert page_content.text
            assert page_content.url

            page_source_url = str(
                page_content.url,
            )

            page_people = (
                extract_people_from_website(
                    text=page_content.text,
                    html=page_content.html,
                    source_url=page_source_url,
                    language="nl",
                )
            )

            _assert_valid_people(
                page_people,
            )

            people.extend(
                page_people,
            )

            print(
                f"Page: {page_source_url}",
            )

            print(
                "People extracted from page: "
                f"{len(page_people)}",
            )

        # ---------------------------------------------------------
        # 6. Extraction-level validation
        # ---------------------------------------------------------
        #
        # extract_people_from_website() already performs lightweight
        # candidate deduplication.
        #
        # Do not reproduce that implementation here.
        #
        # person_identity() is used only for validating its contract.
        # ---------------------------------------------------------

        _assert_valid_people(
            people,
        )

        _assert_no_duplicate_identities(
            people,
        )

        # ---------------------------------------------------------
        # 7. Normalize people
        # ---------------------------------------------------------

        normalized = [
            normalize_person(
                person,
                language="nl",
            )
            for person in people
        ]

        normalized = [
            person
            for person in normalized
            if person.name
        ]

        extracted_people += len(
            people,
        )

        normalized_people += len(
            normalized,
        )

        print(
            f"People extracted: "
            f"{len(people)}",
        )

        print(
            f"People normalized: "
            f"{len(normalized)}",
        )

        # ---------------------------------------------------------
        # 8. Print extracted candidates
        # ---------------------------------------------------------

        for person in people:
            print(
                "Person extracted: "
                f"name={person.name!r}, "
                f"title={person.title!r}, "
                f"linkedin={person.linkedin_url!r}, "
                f"source={str(person.source_url)!r}",
            )

        # ---------------------------------------------------------
        # 9. Print normalized candidates
        # ---------------------------------------------------------

        for person in normalized:
            print(
                "Person normalized: "
                f"name={person.name!r}, "
                f"title={person.title!r}, "
                f"linkedin={person.linkedin_url!r}, "
                f"source={str(person.source_url)!r}",
            )

        # ---------------------------------------------------------
        # 10. Normalization assertions
        # ---------------------------------------------------------

        for person in normalized:
            assert person.name
            assert person.source_url

            if person.linkedin_url:
                linkedin_url = str(
                    person.linkedin_url,
                )

                assert linkedin_url.startswith(
                    "https://www.linkedin.com/in/",
                )

            # Normalization must be idempotent.
            assert (
                normalize_person(
                    person,
                    language="nl",
                )
                == person
            )

        # ---------------------------------------------------------
        # 11. Normalized identity validation
        # ---------------------------------------------------------

        normalized_identities = [
            person_identity(
                person,
                language="nl",
            )
            for person in normalized
        ]

        assert len(
            normalized_identities,
        ) == len(
            set(normalized_identities),
        )

        # ---------------------------------------------------------
        # 12. Decision makers
        # ---------------------------------------------------------
        #
        # find_decision_makers() owns:
        #
        #     entity resolution
        #     scoring
        #     ranking
        #     confidence classification
        #
        # The integration test should not duplicate those algorithms.
        # ---------------------------------------------------------

        decision_makers = (
            find_decision_makers(
                normalized,
            )
        )

        decision_makers_found += len(
            decision_makers,
        )

        high_confidence_decision_makers += sum(
            1
            for decision_maker in decision_makers
            if decision_maker.confidence == "high"
        )

        print(
            "Decision makers found: "
            f"{len(decision_makers)}",
        )

        # ---------------------------------------------------------
        # 13. Decision-maker output
        # ---------------------------------------------------------

        for decision_maker in decision_makers:
            assert isinstance(
                decision_maker,
                DecisionMaker,
            )

            assert decision_maker.person.name
            assert decision_maker.person.source_url

            assert decision_maker.confidence in {
                "high",
                "medium",
                "low",
            }

            assert decision_maker.role_group in {
                "primary",
                "secondary",
            }

            assert isinstance(
                decision_maker.score,
                int,
            )

            assert decision_maker.reasons

            # Professional-only people must not reach the
            # decision-maker layer.
            assert decision_maker.role_group in {
                "primary",
                "secondary",
            }

            print(
                "Decision maker: "
                f"name={decision_maker.person.name!r}, "
                f"title={decision_maker.person.title!r}, "
                f"score={decision_maker.score!r}, "
                f"role_group={decision_maker.role_group!r}, "
                f"confidence={decision_maker.confidence!r}, "
                f"reasons={decision_maker.reasons!r}",
            )

        # ---------------------------------------------------------
        # 14. Decision-maker ranking
        # ---------------------------------------------------------

        scores = [
            decision_maker.score
            for decision_maker in decision_makers
        ]

        assert scores == sorted(
            scores,
            reverse=True,
        )

    # -------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------

    print(f"\n{'=' * 80}")

    print(
        "Businesses tested: "
        f"{len(businesses)}",
    )

    print(
        "Successful homepage crawls: "
        f"{successful_homepage_crawls}",
    )

    print(
        "Failed crawls: "
        f"{failed_crawls}",
    )

    print(
        "People pages discovered: "
        f"{discovered_people_pages}",
    )

    print(
        "People pages crawled: "
        f"{crawled_people_pages}",
    )

    print(
        "People extracted: "
        f"{extracted_people}",
    )

    print(
        "People normalized: "
        f"{normalized_people}",
    )

    print(
        "Decision makers found: "
        f"{decision_makers_found}",
    )

    print(
        "High-confidence decision makers: "
        f"{high_confidence_decision_makers}",
    )

    # -------------------------------------------------------------
    # Final integration assertion
    # -------------------------------------------------------------

    assert successful_homepage_crawls > 0, (
        "None of the discovered websites could be crawled."
    )