from __future__ import annotations

from app.models.schemas.people import PersonCandidate

from .candidates import append_candidate
from .cards import extract_person_cards
from .linkedin import extract_linkedin_candidates
from .names import (
    extract_name_title_candidates,
    extract_title_name_candidates,
)
from .regions import find_person_regions
from .structured import extract_structured_people
from .words import normalize_language


def extract_people_from_website(
    *,
    text: str,
    html: str = "",
    source_url: str,
    language: str = "en",
) -> list[PersonCandidate]:
    """
    Extract person candidates from one already-crawled website page.

    This is the deterministic first-pass extractor.

    Extraction priority:

        1. Structured data
           - JSON-LD Schema.org Person
           - Schema.org Person microdata

        2. DOM person/team cards
           - team/member/profile regions
           - nearby title
           - LinkedIn profile inside the same region

        3. LinkedIn profile evidence

        4. Explicit title + name combinations

        5. Name + nearby professional title

    The returned candidates may contain false positives.

    AI refinement happens after candidates from all relevant website
    pages have been collected. This prevents one Gemini request per
    page and allows the AI step to reason over company-wide evidence.

    This function does not:

        - crawl pages
        - discover additional pages
        - call an AI/LLM provider
        - persist data
        - normalize canonical people
        - resolve identities
        - score decision makers
    """

    if not source_url:
        return []

    if not text and not html:
        return []

    language = normalize_language(
        language,
    )

    candidates: list[PersonCandidate] = []

    # Extraction-level deduplication only.
    #
    # Full identity/entity resolution belongs downstream after
    # optional AI refinement.
    seen: set[
        tuple[str, str | None]
    ] = set()

    # ---------------------------------------------------------
    # 1. Structured data
    # ---------------------------------------------------------

    if html:
        for candidate in extract_structured_people(
            html=html,
            source_url=source_url,
            language=language,
        ):
            append_candidate(
                candidates=candidates,
                seen=seen,
                candidate=candidate,
            )

    # ---------------------------------------------------------
    # 2. DOM person/team cards
    # ---------------------------------------------------------

    if html:
        regions = find_person_regions(
            html,
        )

        cards = extract_person_cards(
            [
                region.element
                for region in regions
            ],
            source_url=source_url,
            language=language,
        )

        for card in cards:
            candidate = PersonCandidate(
                name=card.name,
                title=card.title,
                linkedin_url=card.linkedin_url,
                source_url=(
                    card.source_url
                    or source_url
                ),
            )

            append_candidate(
                candidates=candidates,
                seen=seen,
                candidate=candidate,
            )

    # ---------------------------------------------------------
    # 3. LinkedIn profile evidence
    # ---------------------------------------------------------

    if html:
        for candidate in extract_linkedin_candidates(
            html=html,
            source_url=source_url,
            language=language,
        ):
            append_candidate(
                candidates=candidates,
                seen=seen,
                candidate=candidate,
            )

    # ---------------------------------------------------------
    # 4. Explicit title + name
    # ---------------------------------------------------------

    if text:
        for candidate in extract_title_name_candidates(
            text=text,
            source_url=source_url,
            language=language,
        ):
            append_candidate(
                candidates=candidates,
                seen=seen,
                candidate=candidate,
            )

    # ---------------------------------------------------------
    # 5. Name + nearby professional title
    # ---------------------------------------------------------

    if text:
        for candidate in extract_name_title_candidates(
            text=text,
            source_url=source_url,
            language=language,
        ):
            append_candidate(
                candidates=candidates,
                seen=seen,
                candidate=candidate,
            )

    return candidates