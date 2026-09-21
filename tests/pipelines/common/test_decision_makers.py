# tests/pipelines/common/test_decision_makers.py

from __future__ import annotations

from app.models.schemas.people import PersonCandidate
from app.pipelines.common.people import (
    DecisionMaker,
    find_decision_makers,
    rank_people,
    select_best_decision_maker,
)


def make_person(
    name: str,
    title: str | None,
    *,
    linkedin_url: str | None = None,
) -> PersonCandidate:
    return PersonCandidate(
        name=name,
        title=title,
        linkedin_url=linkedin_url,
        source_url="https://example.com/team",
    )


def test_finds_dutch_primary_decision_maker() -> None:
    people = [
        make_person(
            "Stefanie Schönmuth",
            "Tandarts",
        ),
        make_person(
            "Maarten Vaartjes",
            "Eigenaar",
        ),
        make_person(
            "Jana Stickelbruck",
            "Vestigingsmanager",
        ),
    ]

    result = find_decision_makers(
        people,
    )

    assert result

    assert isinstance(
        result[0],
        DecisionMaker,
    )

    assert result[0].person.name == "Maarten Vaartjes"
    assert result[0].person.title == "Eigenaar"
    assert result[0].confidence == "high"
    assert result[0].role_group == "primary"
    assert result[0].score >= 80
    assert result[0].reasons
    assert result[0].reasons_text == " | ".join(result[0].reasons)


def test_practice_manager_is_secondary_decision_maker() -> None:
    people = [
        make_person(
            "Mary Laros",
            "Praktijkmanager",
        ),
    ]

    result = find_decision_makers(
        people,
    )

    assert len(result) == 1

    assert result[0].person.name == "Mary Laros"
    assert result[0].role_group == "secondary"
    assert result[0].confidence == "medium"
    assert result[0].score >= 60
    assert result[0].reasons


def test_professional_only_person_is_not_decision_maker() -> None:
    people = [
        make_person(
            "Stefanie Schönmuth",
            "Tandarts",
        ),
    ]

    result = find_decision_makers(
        people,
    )

    assert result == []


def test_academic_title_only_is_not_decision_maker() -> None:
    people = [
        make_person(
            "John Smith",
            "Dr.",
        ),
    ]

    result = find_decision_makers(
        people,
    )

    assert result == []


def test_duplicate_persons_are_resolved_before_ranking() -> None:
    people = [
        make_person(
            "Maarten Vaartjes",
            "Eigenaar",
        ),
        make_person(
            "Maarten Vaartjes",
            "Eigenaar",
        ),
    ]

    result = find_decision_makers(
        people,
    )

    assert len(result) == 1
    assert result[0].person.name == "Maarten Vaartjes"


def test_limit_controls_number_of_results() -> None:
    people = [
        make_person(
            "Maarten Vaartjes",
            "Eigenaar",
        ),
        make_person(
            "Susanne Verhees",
            "Directeur",
        ),
        make_person(
            "Mary Laros",
            "Praktijkmanager",
        ),
    ]

    result = find_decision_makers(
        people,
        limit=2,
    )

    assert len(result) == 2


def test_rank_people_returns_all_qualifying_decision_makers() -> None:
    people = [
        make_person(
            "Maarten Vaartjes",
            "Eigenaar",
        ),
        make_person(
            "Susanne Verhees",
            "Directeur",
        ),
        make_person(
            "Mary Laros",
            "Praktijkmanager",
        ),
        make_person(
            "Stefanie Schönmuth",
            "Tandarts",
        ),
    ]

    result = rank_people(people)

    assert len(result) == 3

    assert all(
        isinstance(person, DecisionMaker)
        for person in result
    )

    assert result[0].person.name == "Maarten Vaartjes"


def test_select_best_decision_maker_returns_strongest_candidate() -> None:
    people = [
        make_person(
            "Mary Laros",
            "Praktijkmanager",
        ),
        make_person(
            "Maarten Vaartjes",
            "Eigenaar",
        ),
    ]

    result = select_best_decision_maker(people)

    assert result is not None
    assert isinstance(result, DecisionMaker)
    assert result.person.name == "Maarten Vaartjes"
    assert result.role_group == "primary"
    assert result.confidence == "high"


def test_select_best_decision_maker_returns_none_without_qualifying_person(
) -> None:
    people = [
        make_person(
            "Stefanie Schönmuth",
            "Tandarts",
        ),
        make_person(
            "John Smith",
            "Dr.",
        ),
    ]

    result = select_best_decision_maker(people)

    assert result is None


def test_empty_people_returns_empty_result() -> None:
    assert find_decision_makers([]) == []
    assert rank_people([]) == []
    assert select_best_decision_maker([]) is None


def test_non_positive_limit_returns_empty_result() -> None:
    people = [
        make_person(
            "Maarten Vaartjes",
            "Eigenaar",
        ),
    ]

    assert find_decision_makers(
        people,
        limit=0,
    ) == []

    assert find_decision_makers(
        people,
        limit=-1,
    ) == []