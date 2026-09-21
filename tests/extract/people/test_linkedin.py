# tests/extract/people/test_linkedin.py

from __future__ import annotations

import pytest

from app.extract.people.linkedin import LinkedInPeopleExtractor


SOURCE_URL = "https://example.com/about"


@pytest.fixture
def extractor() -> LinkedInPeopleExtractor:
    return LinkedInPeopleExtractor()


def test_extract_linkedin_profile(
    extractor: LinkedInPeopleExtractor,
) -> None:
    result = extractor.extract(
        [
            "https://www.linkedin.com/in/john-smith",
        ],
        source_url=SOURCE_URL,
    )

    assert len(result) == 1

    person = result[0]

    assert person.name == "John Smith"
    assert person.title is None
    assert str(person.linkedin_url) == (
        "https://www.linkedin.com/in/john-smith"
    )
    assert person.source_url == SOURCE_URL


def test_extract_canonicalizes_linkedin_url(
    extractor: LinkedInPeopleExtractor,
) -> None:
    result = extractor.extract(
        [
            "https://linkedin.com/in/john-smith/",
        ],
        source_url=SOURCE_URL,
    )

    assert len(result) == 1

    assert str(result[0].linkedin_url) == (
        "https://www.linkedin.com/in/john-smith"
    )


def test_extract_removes_query_and_fragment(
    extractor: LinkedInPeopleExtractor,
) -> None:
    result = extractor.extract(
        [
            (
                "https://www.linkedin.com/in/john-smith/"
                "?trk=profile&originalSubdomain=uk#section"
            ),
        ],
        source_url=SOURCE_URL,
    )

    assert len(result) == 1

    assert str(result[0].linkedin_url) == (
        "https://www.linkedin.com/in/john-smith"
    )


@pytest.mark.parametrize(
    "url",
    [
        "https://linkedin.com/in/john-smith",
        "https://www.linkedin.com/in/john-smith",
        "HTTPS://WWW.LINKEDIN.COM/IN/john-smith/",
    ],
)
def test_accepts_valid_linkedin_hosts_and_schemes(
    extractor: LinkedInPeopleExtractor,
    url: str,
) -> None:
    result = extractor.extract(
        [url],
        source_url=SOURCE_URL,
    )

    assert len(result) == 1


@pytest.mark.parametrize(
    "url",
    [
        "https://www.linkedin.com/company/acme",
        "https://www.linkedin.com/school/example",
        "https://www.linkedin.com/feed/",
        "https://www.linkedin.com/jobs/",
        "https://www.linkedin.com/",
    ],
)
def test_ignores_non_profile_linkedin_urls(
    extractor: LinkedInPeopleExtractor,
    url: str,
) -> None:
    result = extractor.extract(
        [url],
        source_url=SOURCE_URL,
    )

    assert result == []


@pytest.mark.parametrize(
    "url",
    [
        "https://www.facebook.com/in/john-smith",
        "https://example.com/in/john-smith",
        "http://twitter.com/in/john-smith",
        "ftp://www.linkedin.com/in/john-smith",
        "linkedin.com/in/john-smith",
        "",
    ],
)
def test_ignores_non_linkedin_profile_urls(
    extractor: LinkedInPeopleExtractor,
    url: str,
) -> None:
    result = extractor.extract(
        [url],
        source_url=SOURCE_URL,
    )

    assert result == []


@pytest.mark.parametrize(
    "url",
    [
        "https://www.linkedin.com/in/123456",
        "https://www.linkedin.com/in/a",
        "https://www.linkedin.com/in/123-456",
        "https://www.linkedin.com/in/abc123",
    ],
)
def test_rejects_obviously_non_name_profile_slugs(
    extractor: LinkedInPeopleExtractor,
    url: str,
) -> None:
    result = extractor.extract(
        [url],
        source_url=SOURCE_URL,
    )

    assert result == []


def test_extracts_dutch_style_name_slug(
    extractor: LinkedInPeopleExtractor,
) -> None:
    result = extractor.extract(
        [
            "https://www.linkedin.com/in/jan-de-vries",
        ],
        source_url=SOURCE_URL,
    )

    assert len(result) == 1
    assert result[0].name == "Jan De Vries"


def test_extracts_multiple_people(
    extractor: LinkedInPeopleExtractor,
) -> None:
    result = extractor.extract(
        [
            "https://www.linkedin.com/in/john-smith",
            "https://www.linkedin.com/in/jane-doe",
            "https://www.linkedin.com/in/peter-jansen",
        ],
        source_url=SOURCE_URL,
    )

    assert len(result) == 3

    assert [
        person.name
        for person in result
    ] == [
        "John Smith",
        "Jane Doe",
        "Peter Jansen",
    ]


def test_deduplicates_same_profile(
    extractor: LinkedInPeopleExtractor,
) -> None:
    result = extractor.extract(
        [
            "https://www.linkedin.com/in/john-smith",
            "https://linkedin.com/in/john-smith/",
            (
                "https://www.linkedin.com/in/john-smith"
                "?trk=profile"
            ),
        ],
        source_url=SOURCE_URL,
    )

    assert len(result) == 1

    assert str(result[0].linkedin_url) == (
        "https://www.linkedin.com/in/john-smith"
    )


def test_deduplication_is_case_insensitive(
    extractor: LinkedInPeopleExtractor,
) -> None:
    result = extractor.extract(
        [
            "https://www.linkedin.com/in/john-smith",
            "https://www.linkedin.com/in/JOHN-SMITH",
        ],
        source_url=SOURCE_URL,
    )

    assert len(result) == 1


def test_preserves_source_url(
    extractor: LinkedInPeopleExtractor,
) -> None:
    result = extractor.extract(
        [
            "https://www.linkedin.com/in/john-smith",
        ],
        source_url="https://example.com/team",
    )

    assert len(result) == 1
    assert result[0].source_url == "https://example.com/team"


def test_ignores_mixed_invalid_and_valid_urls(
    extractor: LinkedInPeopleExtractor,
) -> None:
    result = extractor.extract(
        [
            "https://www.linkedin.com/company/example",
            "https://example.com/in/john-smith",
            "https://www.linkedin.com/in/john-smith",
            "https://www.linkedin.com/jobs/",
            "https://www.linkedin.com/in/jane-doe",
        ],
        source_url=SOURCE_URL,
    )

    assert len(result) == 2

    assert [
        person.name
        for person in result
    ] == [
        "John Smith",
        "Jane Doe",
    ]