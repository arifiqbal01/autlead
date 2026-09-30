# app/extract/people/linkedin.py

from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from app.models.schemas.people import PersonCandidate

from .names import extract_best_name
from .patterns import LINKEDIN_PROFILE_RE
from .regions import find_person_regions
from .titles import extract_nearby_title


def extract_linkedin_candidates(
    *,
    html: str,
    source_url: str,
    language: str,
) -> list[PersonCandidate]:
    """
    Extract person candidates associated with LinkedIn /in/ profiles.

    LinkedIn is strong identity evidence, but profile URLs alone do not
    prove the nearby text represents the person's real name.

    DOM-scoped person regions are preferred over arbitrary HTML proximity.
    """

    if not html or not source_url:
        return []

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    candidates: list[PersonCandidate] = []
    seen: set[str] = set()

    # Build shared person-region candidates once.
    person_regions = find_person_regions(
        html,
        min_score=6,
    )

    for anchor in soup.find_all(
        "a",
        href=True,
    ):
        href = anchor.get("href")

        if not isinstance(href, str):
            continue

        linkedin_url = normalize_linkedin_url(
            href
        )

        if not linkedin_url:
            continue

        if linkedin_url in seen:
            continue

        seen.add(linkedin_url)

        region = _find_matching_person_region(
            anchor=anchor,
            regions=person_regions,
        )

        if region is not None:
            nearby = region.get_text(
                " ",
                strip=True,
            )
        else:
            nearby = _fallback_anchor_region_text(
                anchor
            )

        name = extract_best_name(
            nearby
        )

        if not name:
            name = name_from_linkedin_slug(
                linkedin_url
            )

        if not name:
            continue

        title = extract_nearby_title(
            nearby,
            language=language,
        )

        candidates.append(
            PersonCandidate(
                name=name,
                title=title,
                linkedin_url=linkedin_url,
                source_url=source_url,
            )
        )

    return candidates


def extract_linkedin_profiles(
    html: str,
) -> list[str]:
    """
    Extract normalized LinkedIn /in/ profile URLs.

    DOM anchors are preferred, with regex fallback for JSON-LD,
    scripts, and other non-anchor locations.
    """

    if not html:
        return []

    found: set[str] = set()

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    # ---------------------------------------------------------
    # DOM links
    # ---------------------------------------------------------

    for anchor in soup.find_all(
        "a",
        href=True,
    ):
        href = anchor.get("href")

        if not isinstance(href, str):
            continue

        linkedin_url = normalize_linkedin_url(
            href
        )

        if linkedin_url:
            found.add(
                linkedin_url
            )

    # ---------------------------------------------------------
    # Raw HTML fallback
    # ---------------------------------------------------------

    for match in LINKEDIN_PROFILE_RE.finditer(
        html
    ):
        linkedin_url = normalize_linkedin_url(
            match.group(0)
        )

        if linkedin_url:
            found.add(
                linkedin_url
            )

    return sorted(found)


def normalize_linkedin_url(
    url: str,
) -> str | None:
    """
    Normalize a LinkedIn personal-profile URL.

    Only /in/ URLs are accepted.

    Examples:
        https://linkedin.com/in/john-smith/
            -> https://www.linkedin.com/in/john-smith

        https://www.linkedin.com/in/john-smith/?trk=foo
            -> https://www.linkedin.com/in/john-smith
    """

    value = url.strip()

    if not value:
        return None

    if not re.match(
        r"^https?://",
        value,
        flags=re.IGNORECASE,
    ):
        value = f"https://{value}"

    try:
        parsed = urlparse(
            value
        )

        hostname = (
            parsed.hostname or ""
        ).casefold().removeprefix("www.")

    except ValueError:
        # Scraped hrefs may contain malformed placeholders such as
        # [#DSR_FORM_URL#], which urllib interprets as invalid
        # bracketed/IPv6 host syntax.
        return None

    if hostname != "linkedin.com":
        return None

    path = parsed.path.rstrip("/")

    match = re.fullmatch(
        r"/in/([^/]+)",
        path,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    slug = match.group(1).strip()

    if not slug:
        return None

    return (
        "https://www.linkedin.com/in/"
        f"{slug}"
    )


def name_from_linkedin_slug(
    url: str,
) -> str | None:
    """
    Derive a conservative fallback name from a LinkedIn slug.

    This is fallback evidence only. LinkedIn slugs are not guaranteed
    to contain a person's real name.
    """

    normalized = normalize_linkedin_url(
        url
    )

    if not normalized:
        return None

    parsed = urlparse(
        normalized
    )

    slug = (
        parsed.path
        .rstrip("/")
        .split("/")[-1]
    )

    # Require at least two alphabetic name-like pieces.
    #
    # Reject slugs such as:
    #
    #     john123
    #     company-name-123
    #     user
    #
    if not re.fullmatch(
        r"[A-Za-zÀ-ÖØ-öø-ÿ]+"
        r"(?:[-_][A-Za-zÀ-ÖØ-öø-ÿ]+){1,4}",
        slug,
    ):
        return None

    parts = re.split(
        r"[-_]",
        slug,
    )

    if not 2 <= len(parts) <= 5:
        return None

    return " ".join(
        part.capitalize()
        for part in parts
    )


def _find_matching_person_region(
    *,
    anchor: Tag,
    regions,
) -> Tag | None:
    """
    Find the smallest detected person region containing this LinkedIn anchor.

    Regions have already been structurally scored by regions.py.
    """

    matches: list[Tag] = []

    for region in regions:
        element = region.element

        if (
            anchor is element
            or element in anchor.parents
        ):
            matches.append(
                element
            )

    if not matches:
        return None

    # Prefer the deepest/smallest containing region.
    return max(
        matches,
        key=_element_depth,
    )


def _fallback_anchor_region_text(
    anchor: Tag,
    *,
    max_parents: int = 3,
) -> str:
    """
    Conservative fallback when the shared region detector did not identify
    a person block.

    Walk only a few parents and stop before large/noisy containers.
    """

    current: Tag | None = anchor

    for _ in range(
        max_parents
    ):
        if current is None:
            break

        text = current.get_text(
            " ",
            strip=True,
        )

        if 3 <= len(text) <= 500:
            if current.find(
                (
                    "h1",
                    "h2",
                    "h3",
                    "h4",
                    "h5",
                    "h6",
                )
            ):
                return text

        parent = current.parent

        if not isinstance(
            parent,
            Tag,
        ):
            break

        current = parent

    return ""


def _element_depth(
    element: Tag,
) -> int:
    return sum(
        1
        for _ in element.parents
    )


__all__ = [
    "extract_linkedin_candidates",
    "extract_linkedin_profiles",
    "name_from_linkedin_slug",
    "normalize_linkedin_url",
]