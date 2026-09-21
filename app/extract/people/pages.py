# app/extract/people/pages.py

from __future__ import annotations

from html import unescape
from urllib.parse import urljoin, urlparse

from .patterns import ANCHOR_RE
from .words import (
    combined_person_page_paths,
    normalize_language,
    person_page_paths,
)


# ---------------------------------------------------------------------------
# Page scoring
# ---------------------------------------------------------------------------

# Positive path/anchor signals.
#
# These are intentionally broader than the exact configured paths because
# real websites use many variations.
POSITIVE_PATH_TERMS = frozenset(
    {
        "about",
        "about-us",
        "team",
        "our-team",
        "our-people",
        "people",
        "leadership",
        "management",
        "board",
        "staff",
        "over-ons",
        "ons-team",
        "onze-mensen",
        "mensen",
        "directie",
        "bestuur",
        "medewerkers",
        "organisatie",
        "over-de-praktijk",
    }
)


# Pages that are usually poor people-page candidates.
#
# Contact is deliberately NOT included here because a contact page can
# contain an owner, founder, or team member.
NEGATIVE_PATH_TERMS = frozenset(
    {
        "privacy",
        "privacy-policy",
        "cookie",
        "cookies",
        "terms",
        "terms-and-conditions",
        "voorwaarden",
        "faq",
        "blog",
        "news",
        "nieuws",
        "vacature",
        "vacatures",
        "careers",
        "career",
        "shop",
        "products",
        "product",
        "diensten",
        "services",
        "contactformulier",
    }
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def find_people_page_urls(
    *,
    html: str,
    source_url: str,
    language: str | None = None,
    max_results: int = 10,
) -> list[str]:
    """
    Discover likely people/team pages from internal website links.

    This function only discovers and ranks URLs.

    It does NOT:

        - crawl pages
        - extract people
        - resolve people
        - score people
        - perform external search

    Only same-host URLs are returned.

    ``language`` controls language-specific page-path vocabulary, while
    English + Dutch signals are still considered together because Dutch
    websites frequently mix both languages.
    """

    if not html or not source_url:
        return []

    if max_results <= 0:
        return []

    language = normalize_language(
        language,
    )

    source = urlparse(
        source_url,
    )

    source_host = (
        source.hostname or ""
    ).casefold()

    if not source_host:
        return []

    # Language-specific paths are strongest.
    configured_paths = {
        path.casefold().rstrip("/")
        for path in person_page_paths(
            language,
        )
    }

    # Keep bilingual support.
    configured_paths.update(
        path.casefold().rstrip("/")
        for path in combined_person_page_paths()
    )

    candidates: dict[str, int] = {}

    for match in ANCHOR_RE.finditer(html):
        href = (
            match.group(1)
            or match.group(2)
            or match.group(3)
            or ""
        ).strip()

        anchor_text = _clean_anchor_text(
            match.group(4),
        )

        if not href:
            continue

        absolute_url = urljoin(
            source_url,
            unescape(href),
        )

        parsed = urlparse(
            absolute_url,
        )

        # ---------------------------------------------------------
        # Only HTTP(S)
        # ---------------------------------------------------------

        if parsed.scheme.lower() not in {
            "http",
            "https",
        }:
            continue

        # ---------------------------------------------------------
        # Same host only
        # ---------------------------------------------------------

        page_host = (
            parsed.hostname or ""
        ).casefold()

        if page_host != source_host:
            continue

        # ---------------------------------------------------------
        # Ignore fragments
        # ---------------------------------------------------------

        path = (
            parsed.path
            or "/"
        ).rstrip("/")

        if not path:
            path = "/"

        normalized_path = path.casefold()

        # ---------------------------------------------------------
        # Ignore the current page
        # ---------------------------------------------------------

        source_path = (
            source.path
            or "/"
        ).rstrip("/")

        if not source_path:
            source_path = "/"

        if normalized_path == source_path.casefold():
            continue

        # ---------------------------------------------------------
        # Score candidate
        # ---------------------------------------------------------

        score = _score_page(
            path=normalized_path,
            anchor_text=anchor_text,
            configured_paths=configured_paths,
        )

        if score <= 0:
            continue

        canonical_url = _canonical_url(
            parsed,
        )

        previous = candidates.get(
            canonical_url,
            0,
        )

        candidates[
            canonical_url
        ] = max(
            previous,
            score,
        )

    ranked = sorted(
        candidates.items(),
        key=lambda item: (
            -item[1],
            item[0],
        ),
    )

    return [
        url
        for url, _score in ranked[
            :max_results
        ]
    ]


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def _score_page(
    *,
    path: str,
    anchor_text: str,
    configured_paths: set[str],
) -> int:
    """
    Score a candidate URL for people-page relevance.

    Higher scores indicate stronger evidence.
    """

    score = 0

    normalized_path = path.rstrip("/") or "/"

    # ---------------------------------------------------------
    # Exact configured person-page path
    # ---------------------------------------------------------

    if normalized_path in configured_paths:
        score += 100

    # ---------------------------------------------------------
    # Path segments
    # ---------------------------------------------------------

    segments = {
        segment
        for segment in normalized_path.split("/")
        if segment
    }

    positive_hits = segments & POSITIVE_PATH_TERMS

    score += len(
        positive_hits,
    ) * 25

    # ---------------------------------------------------------
    # Anchor text
    # ---------------------------------------------------------

    anchor_words = _tokenize(
        anchor_text,
    )

    positive_anchor_terms = (
        POSITIVE_PATH_TERMS
        | {
            "team",
            "people",
            "staff",
            "leadership",
            "management",
            "directie",
            "medewerkers",
            "bestuur",
            "ons",
            "onze",
            "mensen",
        }
    )

    anchor_hits = (
        anchor_words
        & positive_anchor_terms
    )

    score += len(
        anchor_hits,
    ) * 15

    # ---------------------------------------------------------
    # Negative path evidence
    # ---------------------------------------------------------

    negative_hits = segments & NEGATIVE_PATH_TERMS

    score -= len(
        negative_hits,
    ) * 35

    # ---------------------------------------------------------
    # Keep obvious contact pages possible.
    #
    # Contact pages can contain decision makers.
    # They are not strong people-page candidates, but should not
    # automatically be discarded.
    # ---------------------------------------------------------

    if "contact" in segments:
        score += 5

    return score


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------


def _canonical_url(
    parsed,
) -> str:
    """
    Canonicalize a discovered URL for deduplication.

    Query parameters and fragments are removed because tracking parameters
    should not create multiple copies of the same people page.
    """

    scheme = parsed.scheme.lower()

    hostname = (
        parsed.hostname or ""
    ).lower()

    path = (
        parsed.path
        or "/"
    ).rstrip("/")

    if not path:
        path = "/"

    return (
        f"{scheme}://{hostname}{path}"
    )


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


def _clean_anchor_text(
    value: str,
) -> str:
    """
    Convert anchor HTML/text into simple searchable text.
    """

    value = unescape(
        value or "",
    )

    # Strip simple HTML tags from anchor content.
    result: list[str] = []
    inside_tag = False

    for character in value:
        if character == "<":
            inside_tag = True
            continue

        if character == ">":
            inside_tag = False
            continue

        if not inside_tag:
            result.append(character)

    return " ".join(
        "".join(result).split(),
    ).casefold()


def _tokenize(
    value: str,
) -> set[str]:
    """
    Tokenize path/anchor text.

    Hyphens and underscores are treated as separators.
    """

    normalized = (
        value.casefold()
        .replace("-", " ")
        .replace("_", " ")
        .replace("/", " ")
    )

    return {
        token
        for token in normalized.split()
        if token
    }


__all__ = [
    "find_people_page_urls",
]