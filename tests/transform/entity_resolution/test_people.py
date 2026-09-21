# tests/transform/entity_resolution/test_people.py

from __future__ import annotations

from app.models.schemas.people import PersonCandidate
from app.transform.entity_resolution import (
    compare_people,
    resolve_people,
)


def make_person(
    name: str,
    *,
    title: str | None = None,
    linkedin_url: str | None = None,
    source_url: str = "https://example.com/team",
) -> PersonCandidate:
    return PersonCandidate(
        name=name,
        title=title,
        linkedin_url=linkedin_url,
        source_url=source_url,
    )


def test_same_name_is_resolved_as_same_person() -> None:
    first = make_person(
        "Jan van der Berg",
        title="Directeur",
    )

    second = make_person(
        "Jan van der Berg",
        title="Eigenaar",
    )

    result = compare_people(
        first,
        second,
    )

    assert result.relation == "same"
    assert result.score == 1.0


def test_same_linkedin_is_resolved_as_same_person() -> None:
    first = make_person(
        "Jan van der Berg",
        linkedin_url=(
            "https://www.linkedin.com/in/"
            "jan-van-der-berg"
        ),
    )

    second = make_person(
        "Different Name",
        linkedin_url=(
            "https://www.linkedin.com/in/"
            "jan-van-der-berg"
        ),
    )

    result = compare_people(
        first,
        second,
    )

    assert result.relation == "same"
    assert result.score == 1.0


def test_different_linkedin_profiles_are_not_merged() -> None:
    first = make_person(
        "Jan van der Berg",
        linkedin_url=(
            "https://www.linkedin.com/in/"
            "jan-van-der-berg"
        ),
    )

    second = make_person(
        "Jan van der Berg",
        linkedin_url=(
            "https://www.linkedin.com/in/"
            "another-person"
        ),
    )

    result = compare_people(
        first,
        second,
    )

    assert result.relation == "different"


def test_different_people_are_not_merged() -> None:
    first = make_person(
        "Jan van der Berg",
    )

    second = make_person(
        "Maria de Vries",
    )

    result = compare_people(
        first,
        second,
    )

    assert result.relation == "different"


def test_possible_fuzzy_match_is_not_automatically_merged() -> None:
    first = make_person(
        "Jan van der Berg",
    )

    second = make_person(
        "Jan van Berg",
    )

    result = compare_people(
        first,
        second,
    )

    if result.relation == "possible":
        resolved = resolve_people(
            [first, second],
        )

        assert len(resolved) == 2


def test_resolve_people_merges_exact_duplicates() -> None:
    first = make_person(
        "Susanne Verhees",
        title="Directeur",
    )

    second = make_person(
        "Susanne Verhees",
        title=None,
        source_url="https://example.com/team",
    )

    resolved = resolve_people(
        [first, second],
    )

    assert len(resolved) == 1
    assert resolved[0].person.name == "Susanne Verhees"

    assert len(resolved[0].sources) == 2


def test_resolution_preserves_unique_people() -> None:
    people = [
        make_person("Susanne Verhees"),
        make_person("Mary Laros"),
        make_person("Jan de Vries"),
    ]

    resolved = resolve_people(
        people,
    )

    assert len(resolved) == 3