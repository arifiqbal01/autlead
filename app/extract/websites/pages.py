# app/extract/website/pages.py

from __future__ import annotations

from urllib.parse import urlparse

from app.models.schemas.website_pages import WebsitePageCandidate


def extract_page_candidates(
    *,
    links: list[str],
) -> list[WebsitePageCandidate]:
    """
    Convert discovered website links into page candidates.

    This layer performs structural extraction only.

    It does not:
    - decide whether a page is relevant
    - score pages
    - crawl pages
    - persist pages
    - perform people extraction

    Filtering and ranking belong in the transform layer.
    """

    candidates: list[WebsitePageCandidate] = []
    seen: set[str] = set()

    for raw_url in links:
        url = raw_url.strip()

        if not url:
            continue

        if url in seen:
            continue

        parsed = urlparse(url)

        if parsed.scheme.casefold() not in {
            "http",
            "https",
        }:
            continue

        if not parsed.hostname:
            continue

        seen.add(url)

        candidates.append(
            WebsitePageCandidate(
                url=url,
                path=parsed.path or "/",
            )
        )

    return candidates


