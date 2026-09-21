# app/transform/analysis/website_pages.py

from __future__ import annotations

from urllib.parse import urlparse

from app.models.schemas.website_pages import WebsitePageCandidate


HIGH_VALUE_SEGMENTS: dict[str, int] = {
    "team": 100,
    "our-team": 100,
    "ons-team": 100,
    "people": 95,
    "our-people": 95,
    "staff": 95,
    "leadership": 95,
    "management": 90,
    "directie": 95,
    "bestuur": 90,
    "medewerkers": 90,
    "about": 80,
    "about-us": 85,
    "over-ons": 85,
    "company": 70,
    "organisation": 70,
    "organization": 70,
    "contact": 60,
    "contact-us": 60,
}


REJECT_SEGMENTS: frozenset[str] = frozenset(
    {
        "product",
        "products",
        "collection",
        "collections",
        "category",
        "categories",
        "shop",
        "cart",
        "checkout",
        "account",
        "login",
        "register",
        "wishlist",
        "catalog",
        "sale",
        "offers",
        "blog",
        "blogs",
        "news",
        "nieuws",
        "article",
        "articles",
        "tag",
        "tags",
        "search",
        "faq",
        "privacy",
        "privacy-policy",
        "terms",
        "terms-and-conditions",
        "voorwaarden",
        "cookies",
        "cookie-policy",
    }
)


def select_business_pages(
    candidates: list[WebsitePageCandidate],
    *,
    limit: int = 5,
) -> list[WebsitePageCandidate]:
    """
    Select and rank business-relevant website pages.

    This transformation prefers pages likely to contain useful
    company or people information, such as:

    - team
    - people
    - leadership
    - management
    - about
    - contact

    Ecommerce, catalog, blog, legal, account, and other low-value
    navigation pages are rejected.

    This function does not:

    - crawl pages
    - persist pages
    - extract people
    - perform contact extraction
    - score leads
    """

    if limit <= 0:
        return []

    scored: list[
        tuple[
            int,
            int,
            WebsitePageCandidate,
        ]
    ] = []

    seen: set[str] = set()

    for candidate in candidates:
        url = str(candidate.url)

        if url in seen:
            continue

        seen.add(url)

        parsed = urlparse(url)

        path_parts = _path_parts(
            parsed.path,
        )

        if not path_parts:
            continue

        if _contains_rejected_segment(
            path_parts,
        ):
            continue

        score = _score_path(
            path_parts,
        )

        if score <= 0:
            continue

        # Prefer shorter, more canonical-looking URLs when
        # two pages have the same relevance score.
        path_length = len(
            parsed.path.rstrip("/")
        )

        scored.append(
            (
                score,
                path_length,
                candidate,
            )
        )

    scored.sort(
        key=lambda item: (
            -item[0],
            item[1],
            str(item[2].url),
        )
    )

    return [
        candidate
        for _, _, candidate in scored[:limit]
    ]


def score_business_page(
    candidate: WebsitePageCandidate,
) -> int:
    """
    Return the relevance score for one website page candidate.

    A score of 0 means the page should not be selected.
    """

    parsed = urlparse(
        str(candidate.url),
    )

    path_parts = _path_parts(
        parsed.path,
    )

    if not path_parts:
        return 0

    if _contains_rejected_segment(
        path_parts,
    ):
        return 0

    return _score_path(
        path_parts,
    )


def _score_path(
    path_parts: list[str],
) -> int:
    """
    Score a URL path using exact path-segment matches.

    Exact segment matching avoids false positives such as:

        /catalog/steampunk-sculptures/

    accidentally matching:

        team
    """

    score = 0

    for part in path_parts:
        part_score = HIGH_VALUE_SEGMENTS.get(
            part,
            0,
        )

        if part_score > score:
            score = part_score

    return score


def _contains_rejected_segment(
    path_parts: list[str],
) -> bool:
    """
    Determine whether a path contains a known low-value segment.
    """

    return any(
        part in REJECT_SEGMENTS
        for part in path_parts
    )


def _path_parts(
    path: str,
) -> list[str]:
    """
    Normalize a URL path into meaningful path components.

    Important:

    We keep complete path components intact.

    Example:

        /pages/about-us

    becomes:

        ["pages", "about-us"]

    rather than splitting "about-us" into "about" and "us".

    This prevents accidental substring matches.
    """

    return [
        part.casefold().strip()
        for part in path.split("/")
        if part.strip()
    ]