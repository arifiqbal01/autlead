from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from pydantic import HttpUrl, TypeAdapter

from app.models.schemas.people import PersonCandidate
from app.providers.llm.groq import GroqLLMProvider

PersonRoleGroup = Literal[
    "primary",
    "secondary",
    "professional",
    "other",
    "unknown",
]

DecisionMakerConfidence = Literal[
    "high",
    "medium",
    "low",
]

_http_url_adapter = TypeAdapter(HttpUrl)


@dataclass(frozen=True, slots=True)
class AIRefinedPerson:
    """
    Person candidate plus LLM semantic role assessment.

    Groq validates and interprets deterministic candidates.
    Final decision-maker qualification remains the responsibility
    of Autlead policy.
    """

    person: PersonCandidate
    ai_decision_maker: bool
    role_group: PersonRoleGroup
    decision_maker_confidence: DecisionMakerConfidence
    decision_maker_reason: str | None = None
    evidence: str | None = None


async def refine_people_with_ai(
    *,
    provider: GroqLLMProvider,
    company_name: str,
    homepage_url: str,
    pages: Sequence[object],
    candidates: list[PersonCandidate],
    max_context_chars: int = 6_000,
    context_chars_per_match: int = 600,
    max_matches_per_candidate: int = 3,
) -> list[AIRefinedPerson]:
    """
    Validate and classify deterministic person candidates using Groq.

    Deterministic extraction owns person discovery.

    Groq:
        - validates extracted candidates
        - removes clear false positives
        - corrects supported names/titles
        - merges duplicates
        - interprets professional roles
        - assesses decision-maker authority

    Supporting context is selected by locating candidate names across
    all crawled pages. Page type or URL does not determine priority.

    Final decision-maker qualification remains downstream in
    Autlead policy code.
    """

    if not candidates:
        return []

    website_text = _build_people_context(
        pages,
        candidates=candidates,
        max_chars=max_context_chars,
        chars_per_match=context_chars_per_match,
        max_matches_per_candidate=max_matches_per_candidate,
    )

    if not website_text:
        return _fallback_people(candidates)

    result = await provider.extract_people(
        company_name=company_name,
        website_url=homepage_url,
        website_text=website_text,
        candidates=candidates,
    )

    refined: list[AIRefinedPerson] = []

    for person in result.people:
        refined.append(
            AIRefinedPerson(
                person=PersonCandidate(
                    name=person.name,
                    title=person.title,
                    linkedin_url=_to_http_url(
                        person.linkedin_url
                    ),
                    source_url=_to_required_http_url(
                        person.source_url
                        or homepage_url
                    ),
                ),
                ai_decision_maker=person.decision_maker,
                role_group=person.role_group,
                decision_maker_confidence=(
                    person.decision_maker_confidence
                ),
                decision_maker_reason=(
                    person.decision_maker_reason
                ),
                evidence=person.evidence,
            )
        )

    return refined


def _fallback_people(
    candidates: list[PersonCandidate],
) -> list[AIRefinedPerson]:
    """
    Preserve deterministic candidates when Groq cannot be used.

    No AI authority classification is inferred.
    """

    return [
        AIRefinedPerson(
            person=candidate,
            ai_decision_maker=False,
            role_group="unknown",
            decision_maker_confidence="low",
            decision_maker_reason=None,
            evidence=None,
        )
        for candidate in candidates
    ]


def _build_people_context(
    pages: Sequence[object],
    *,
    candidates: list[PersonCandidate],
    max_chars: int,
    chars_per_match: int,
    max_matches_per_candidate: int,
) -> str:
    """
    Build bounded candidate-specific context from all crawled pages.

    Each candidate name is searched across every crawled page.
    Nearby text around each occurrence is collected instead of
    sending arbitrary full-page content to the LLM.

    Context is selected in rounds so one candidate cannot consume
    the entire context budget before other candidates are considered.
    """

    if (
        max_chars <= 0
        or chars_per_match <= 0
        or max_matches_per_candidate <= 0
        or not candidates
    ):
        return ""

    page_data = _collect_page_text(pages)

    if not page_data:
        return ""

    candidate_chunks: list[list[str]] = []

    for candidate in candidates:
        candidate_name = candidate.name.strip()

        if not candidate_name:
            candidate_chunks.append([])
            continue

        chunks = _build_candidate_chunks(
            candidate_name=candidate_name,
            page_data=page_data,
            chars_per_match=chars_per_match,
            max_matches=max_matches_per_candidate,
        )

        candidate_chunks.append(chunks)

    return _select_context_chunks(
        candidate_chunks,
        max_chars=max_chars,
        max_matches_per_candidate=max_matches_per_candidate,
    )


def _build_candidate_chunks(
    *,
    candidate_name: str,
    page_data: list[tuple[str, str]],
    chars_per_match: int,
    max_matches: int,
) -> list[str]:
    """
    Find bounded evidence snippets for one candidate.
    """

    chunks: list[str] = []
    seen: set[tuple[str, str]] = set()

    for url, text in page_data:
        matches = _find_name_matches(
            text,
            candidate_name,
        )

        for match in matches:
            snippet = _extract_match_context(
                text,
                match_start=match.start(),
                match_end=match.end(),
                max_chars=chars_per_match,
            )

            if not snippet:
                continue

            dedup_key = (
                url,
                snippet.casefold(),
            )

            if dedup_key in seen:
                continue

            seen.add(dedup_key)

            chunks.append(
                
                    f"CANDIDATE: {candidate_name}\n"
                    f"SOURCE: {url}\n"
                    f"CONTEXT: {snippet}"
                
            )

            if len(chunks) >= max_matches:
                return chunks

    return chunks


def _select_context_chunks(
    candidate_chunks: list[list[str]],
    *,
    max_chars: int,
    max_matches_per_candidate: int,
) -> str:
    """
    Select candidate evidence using round-robin ordering.

    The first snippet for each candidate is considered before a
    second snippet for any candidate. This prevents candidates with
    many occurrences from starving later candidates of context.
    """

    selected: list[str] = []
    used_chars = 0

    for match_index in range(
        max_matches_per_candidate
    ):
        for chunks in candidate_chunks:
            if match_index >= len(chunks):
                continue

            chunk = chunks[match_index]

            separator_chars = (
                2 if selected else 0
            )

            remaining = (
                max_chars
                - used_chars
                - separator_chars
            )

            if remaining <= 0:
                return "\n\n".join(
                    selected
                )

            if len(chunk) > remaining:
                chunk = chunk[:remaining].rstrip()

            if not chunk:
                return "\n\n".join(
                    selected
                )

            selected.append(chunk)

            used_chars += (
                separator_chars
                + len(chunk)
            )

            if used_chars >= max_chars:
                return "\n\n".join(
                    selected
                )

    return "\n\n".join(selected)


def _collect_page_text(
    pages: Sequence[object],
) -> list[tuple[str, str]]:
    """
    Extract URL and readable text from crawled page objects.
    """

    collected: list[tuple[str, str]] = []

    for page in pages:
        content = getattr(
            page,
            "content",
            page,
        )

        text_value = getattr(
            content,
            "text",
            "",
        )

        if not isinstance(
            text_value,
            str,
        ):
            continue

        text = text_value.strip()

        if not text:
            continue

        content_url = getattr(
            content,
            "url",
            None,
        )

        page_url = getattr(
            page,
            "url",
            None,
        )

        url_value = (
            content_url
            or page_url
            or ""
        )

        url = str(url_value)

        collected.append(
            (
                url,
                text,
            )
        )

    return collected


def _find_name_matches(
    text: str,
    name: str,
) -> list[re.Match[str]]:
    """
    Find case-insensitive candidate-name matches.

    Whitespace between name components is flexible so names split
    across spaces or newlines can still be matched.
    """

    parts = name.split()

    if not parts:
        return []

    pattern = r"\s+".join(
        re.escape(part)
        for part in parts
    )

    return list(
        re.finditer(
            pattern,
            text,
            flags=re.IGNORECASE,
        )
    )


def _extract_match_context(
    text: str,
    *,
    match_start: int,
    match_end: int,
    max_chars: int,
) -> str:
    """
    Extract bounded text surrounding a candidate-name match.
    """

    if max_chars <= 0:
        return ""

    match_length = (
        match_end - match_start
    )

    surrounding_chars = max(
        0,
        max_chars - match_length,
    )

    before = (
        surrounding_chars // 2
    )

    after = (
        surrounding_chars - before
    )

    start = max(
        0,
        match_start - before,
    )

    end = min(
        len(text),
        match_end + after,
    )

    snippet = text[
        start:end
    ]

    return " ".join(
        snippet.split()
    )


def _to_http_url(
    value: str | HttpUrl | None,
) -> HttpUrl | None:
    """
    Validate an optional URL at the PersonCandidate boundary.
    """

    if value is None:
        return None

    if isinstance(value, HttpUrl):
        return value

    return _http_url_adapter.validate_python(
        value
    )


def _to_required_http_url(
    value: str | HttpUrl,
) -> HttpUrl:
    """
    Validate a required URL at the PersonCandidate boundary.
    """

    if isinstance(value, HttpUrl):
        return value

    return _http_url_adapter.validate_python(
        value
    )