# tests/transform/scoring/test_people.py

from __future__ import annotations

from app.models.schemas.people import PersonCandidate
from app.transform.scoring import (
    score_person,
    score_people,
)


def make_person(
    name: str,
    title: str | None,
) -> PersonCandidate:
    return PersonCandidate(
        name=name,
        title=title,
        source_url="https://example.com/team",
    )


def test_dutch_owner_is_primary_decision_maker() -> None:
    person = make_person(
        "Maarten Vaartjes",
        "Eigenaar",
    )

    result = score_person(person)

    assert result.role_group == "primary"
    assert result.score >= 100
    assert "primary_decision_maker_role" in result.reasons


def test_dutch_directeur_is_primary_decision_maker() -> None:
    person = make_person(
        "Susanne Verhees",
        "Directeur",
    )

    result = score_person(person)

    assert result.role_group == "primary"
    assert result.score >= 100


def test_dutch_praktijkmanager_is_secondary_decision_maker() -> None:
    person = make_person(
        "Mary Laros",
        "Praktijkmanager",
    )

    result = score_person(person)

    assert result.role_group == "secondary"
    assert result.score >= 60


def test_dutch_vestigingsmanager_is_secondary_decision_maker() -> None:
    person = make_person(
        "Jana Stickelbruck",
        "Vestigingsmanager",
    )

    result = score_person(person)

    assert result.role_group == "secondary"
    assert result.score >= 60


def test_dentist_is_not_automatically_decision_maker() -> None:
    person = make_person(
        "Stefanie Schönmuth",
        "Tandarts",
    )

    result = score_person(person)

    assert result.role_group == "professional"
    assert result.score < 60


def test_doctor_is_not_automatically_decision_maker() -> None:
    person = make_person(
        "John Smith",
        "Dr.",
    )

    result = score_person(person)

    assert result.role_group == "academic"
    assert result.score < 60


def test_linkedin_adds_evidence_score() -> None:
    without_linkedin = PersonCandidate(
        name="Maarten Vaartjes",
        title="Eigenaar",
        source_url="https://example.com/team",
    )

    with_linkedin = PersonCandidate(
        name="Maarten Vaartjes",
        title="Eigenaar",
        linkedin_url=(
            "https://www.linkedin.com/in/"
            "maarten-vaartjes"
        ),
        source_url="https://example.com/team",
    )

    without_score = score_person(
        without_linkedin,
    )

    with_score = score_person(
        with_linkedin,
    )

    assert with_score.score > without_score.score
    assert "linkedin_profile" in with_score.reasons


def test_score_people_returns_highest_score_first() -> None:
    people = [
        make_person(
            "Stefanie Schönmuth",
            "Tandarts",
        ),
        make_person(
            "Mary Laros",
            "Praktijkmanager",
        ),
        make_person(
            "Maarten Vaartjes",
            "Eigenaar",
        ),
    ]

    results = score_people(
        people,
    )

    assert results[0].person.name == "Maarten Vaartjes"
    assert results[0].role_group == "primary"