from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import HttpUrl

from app.extract.people.ai import (
    _build_people_context,
    refine_people_with_ai,
)
from app.models.schemas.people import PersonCandidate


def _page(
    url: str,
    text: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        url=url,
        content=SimpleNamespace(
            url=url,
            text=text,
        ),
    )


def _candidate(
    name: str,
    *,
    title: str | None = None,
    source_url: str = "https://example.com/",
) -> PersonCandidate:
    return PersonCandidate(
        name=name,
        title=title,
        linkedin_url=None,
        source_url=HttpUrl(source_url),
    )


def test_build_people_context_finds_candidate_on_homepage() -> None:
    pages = [
        _page(
            "https://example.com/",
            (
                "Welcome to Example BV. "
                "Jan de Vries is the founder and owner "
                "of Example BV."
            ),
        ),
    ]

    candidates = [
        _candidate(
            "Jan de Vries",
            title="Founder",
        ),
    ]

    context = _build_people_context(
        pages,
        candidates=candidates,
        max_chars=6_000,
        chars_per_match=600,
        max_matches_per_candidate=3,
    )

    assert "Jan de Vries" in context
    assert "founder and owner" in context
    assert "https://example.com/" in context


def test_build_people_context_finds_candidate_on_team_page() -> None:
    pages = [
        _page(
            "https://example.com/",
            "Welcome to Example BV.",
        ),
        _page(
            "https://example.com/team",
            (
                "Our team includes Jane Smith. "
                "Jane Smith is Operations Manager "
                "and leads the delivery team."
            ),
        ),
    ]

    candidates = [
        _candidate(
            "Jane Smith",
            title="Operations Manager",
        ),
    ]

    context = _build_people_context(
        pages,
        candidates=candidates,
        max_chars=6_000,
        chars_per_match=600,
        max_matches_per_candidate=3,
    )

    assert "Jane Smith" in context
    assert "Operations Manager" in context
    assert "https://example.com/team" in context


def test_build_people_context_matches_name_across_whitespace() -> None:
    pages = [
        _page(
            "https://example.com/team",
            (
                "Leadership\n\n"
                "Jan\n   de   Vries\n"
                "Founder and Managing Director"
            ),
        ),
    ]

    candidates = [
        _candidate("Jan de Vries"),
    ]

    context = _build_people_context(
        pages,
        candidates=candidates,
        max_chars=6_000,
        chars_per_match=600,
        max_matches_per_candidate=3,
    )

    assert "CANDIDATE: Jan de Vries" in context
    assert "Founder and Managing Director" in context


def test_build_people_context_excludes_unrelated_pages() -> None:
    pages = [
        _page(
            "https://example.com/services",
            (
                "We provide accounting, payroll, "
                "tax and consulting services."
            ),
        ),
        _page(
            "https://example.com/team",
            (
                "Jan de Vries is the founder "
                "of Example BV."
            ),
        ),
    ]

    candidates = [
        _candidate("Jan de Vries"),
    ]

    context = _build_people_context(
        pages,
        candidates=candidates,
        max_chars=6_000,
        chars_per_match=600,
        max_matches_per_candidate=3,
    )

    assert "Jan de Vries" in context
    assert "accounting, payroll" not in context
    assert "https://example.com/services" not in context


def test_build_people_context_includes_multiple_candidates() -> None:
    pages = [
        _page(
            "https://example.com/",
            (
                "Jan de Vries is the founder "
                "of Example BV."
            ),
        ),
        _page(
            "https://example.com/team",
            (
                "Jane Smith is Operations Manager "
                "at Example BV."
            ),
        ),
    ]

    candidates = [
        _candidate("Jan de Vries"),
        _candidate("Jane Smith"),
    ]

    context = _build_people_context(
        pages,
        candidates=candidates,
        max_chars=6_000,
        chars_per_match=600,
        max_matches_per_candidate=3,
    )

    assert "CANDIDATE: Jan de Vries" in context
    assert "CANDIDATE: Jane Smith" in context


def test_build_people_context_respects_max_chars() -> None:
    pages = [
        _page(
            "https://example.com/team",
            (
                ("A" * 1_000)
                + " Jan de Vries "
                + ("B" * 1_000)
            ),
        ),
    ]

    candidates = [
        _candidate("Jan de Vries"),
    ]

    context = _build_people_context(
        pages,
        candidates=candidates,
        max_chars=250,
        chars_per_match=600,
        max_matches_per_candidate=3,
    )

    assert len(context) <= 250


def test_build_people_context_returns_empty_when_no_candidate_matches() -> None:
    pages = [
        _page(
            "https://example.com/",
            "Welcome to Example BV.",
        ),
        _page(
            "https://example.com/services",
            "Accounting and consulting services.",
        ),
    ]

    candidates = [
        _candidate("Jan de Vries"),
    ]

    context = _build_people_context(
        pages,
        candidates=candidates,
        max_chars=6_000,
        chars_per_match=600,
        max_matches_per_candidate=3,
    )

    assert context == ""


@pytest.mark.asyncio
async def test_refine_people_falls_back_when_no_context() -> None:
    class Provider:
        async def extract_people(self, **kwargs: object) -> object:
            pytest.fail(
                "Groq must not be called when no candidate context exists"
            )

    candidate = _candidate(
        "Jan de Vries",
        title="Founder",
    )

    result = await refine_people_with_ai(
        provider=Provider(),  # type: ignore[arg-type]
        company_name="Example BV",
        homepage_url="https://example.com/",
        pages=[
            _page(
                "https://example.com/",
                "No person information here.",
            ),
        ],
        candidates=[candidate],
    )

    assert len(result) == 1
    assert result[0].person == candidate
    assert result[0].ai_decision_maker is False
    assert result[0].role_group == "unknown"
    assert result[0].decision_maker_confidence == "low"