# app/extract/people/ai.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

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


@dataclass(frozen=True, slots=True)
class AIRefinedPerson:
    """
    Person candidate plus LLM semantic role assessment.

    Groq provides interpretation.

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
    pages: list,
    candidates: list[PersonCandidate],
    max_context_chars: int = 12_000,
) -> list[AIRefinedPerson]:
    """
    Refine deterministic person candidates using Groq.

    Groq is called once per company only when deterministic
    person candidates were extracted.

    Groq may:
        - validate extracted candidates
        - remove clear false positives
        - correct supported names/titles
        - merge duplicates
        - interpret professional roles
        - assess decision-maker authority

    Groq is not responsible for discovering arbitrary people
    from the entire website.

    Final Autlead decision-maker qualification remains downstream
    in policy code.
    """

    # Deterministic extraction owns person discovery.
    # If nothing was extracted, there is nothing for the LLM
    # refinement stage to validate or classify.
    if not candidates:
        return []

    # Keep website context deliberately bounded.
    #
    # This is temporary supporting evidence for candidate
    # validation/classification. It must not become an entire
    # website dump because provider token limits are substantially
    # smaller than arbitrary crawled-page content.
    website_text = _build_people_context(
        pages,
        max_chars=max_context_chars,
    )

    # Preserve deterministic candidates when no useful website
    # context is available.
    if not website_text:
        return _fallback_people(
            candidates
        )

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
                    linkedin_url=person.linkedin_url,
                    source_url=(
                        person.source_url
                        or homepage_url
                    ),
                ),
                ai_decision_maker=(
                    person.decision_maker
                ),
                role_group=(
                    person.role_group
                ),
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
    pages: list,
    *,
    max_chars: int,
) -> str:
    """
    Combine relevant crawled pages into one bounded LLM context.
    """

    if max_chars <= 0:
        return ""

    chunks: list[str] = []
    remaining = max_chars

    for page in pages:
        content = getattr(
            page,
            "content",
            page,
        )

        text = (
            getattr(
                content,
                "text",
                "",
            )
            or ""
        ).strip()

        if not text:
            continue

        url = (
            getattr(
                content,
                "url",
                None,
            )
            or getattr(
                page,
                "url",
                None,
            )
            or ""
        )

        chunk = (
            f"PAGE URL: {url}\n"
            f"{text}\n"
        )

        if len(chunk) > remaining:
            chunk = chunk[:remaining]

        chunks.append(
            chunk
        )

        remaining -= len(
            chunk
        )

        if remaining <= 0:
            break

    return "\n\n".join(
        chunks
    ).strip()