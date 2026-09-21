from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


SOCIAL_DOMAINS = {
    "linkedin.com": "linkedin",
    "www.linkedin.com": "linkedin",
    "instagram.com": "instagram",
    "www.instagram.com": "instagram",
    "facebook.com": "facebook",
    "www.facebook.com": "facebook",
    "x.com": "x",
    "www.x.com": "x",
    "twitter.com": "x",
    "www.twitter.com": "x",
    "youtube.com": "youtube",
    "www.youtube.com": "youtube",
    "youtu.be": "youtube",
    "github.com": "github",
    "www.github.com": "github",
    "tiktok.com": "tiktok",
    "www.tiktok.com": "tiktok",
}


def normalize_social_url(value: str) -> str | None:
    """
    Normalize a supported social-media URL.

    The result is suitable for deterministic deduplication.

    Examples:

        https://www.linkedin.com/company/example/
        -> https://linkedin.com/company/example

        https://www.instagram.com/example/?hl=en
        -> https://instagram.com/example

        https://twitter.com/example/
        -> https://x.com/example
    """

    value = value.strip()

    if not value:
        return None

    if not value.lower().startswith(("http://", "https://")):
        return None

    try:
        parsed = urlsplit(value)
    except ValueError:
        return None

    if parsed.scheme.lower() not in {"http", "https"}:
        return None

    hostname = (parsed.hostname or "").lower().rstrip(".")

    if hostname not in SOCIAL_DOMAINS:
        return None

    platform = SOCIAL_DOMAINS[hostname]

    path = _normalize_path(
        parsed.path,
        platform=platform,
    )

    if path is None:
        return None

    # Social profile URLs generally do not need crawler-generated
    # query parameters. Preserve only query parameters that identify
    # the actual resource.
    query = _normalize_query(
        parsed.query,
        platform=platform,
    )

    canonical_hostname = _canonical_hostname(platform)

    return urlunsplit(
        (
            "https",
            canonical_hostname,
            path,
            query,
            "",
        )
    )


def normalize_social_urls(
    values: Iterable[str],
) -> list[str]:
    """Normalize social URLs and remove duplicates."""

    found: set[str] = set()

    for value in values:
        normalized = normalize_social_url(value)

        if normalized:
            found.add(normalized)

    return sorted(found)


def social_platform(value: str) -> str | None:
    """Return the supported social platform for a URL."""

    normalized = normalize_social_url(value)

    if normalized is None:
        return None

    hostname = (urlsplit(normalized).hostname or "").lower()

    return SOCIAL_DOMAINS.get(hostname)


def _canonical_hostname(platform: str) -> str:
    """Return the canonical hostname used for a social platform."""

    return {
        "linkedin": "linkedin.com",
        "instagram": "instagram.com",
        "facebook": "facebook.com",
        "x": "x.com",
        "youtube": "youtube.com",
        "github": "github.com",
        "tiktok": "tiktok.com",
    }[platform]


def _normalize_path(
    path: str,
    *,
    platform: str,
) -> str | None:
    """Normalize the path portion of a social URL."""

    path = path.strip()

    if not path:
        return "/"

    # Collapse repeated slashes and ensure one leading slash.
    parts = [
        part
        for part in path.split("/")
        if part
    ]

    if not parts:
        return "/"

    normalized_parts: list[str] = []

    for part in parts:
        part = part.strip()

        if not part:
            continue

        if any(character.isspace() for character in part):
            return None

        normalized_parts.append(part)

    if not normalized_parts:
        return "/"

    normalized = "/" + "/".join(normalized_parts)

    # Remove trailing slash except for the root URL.
    if normalized != "/":
        normalized = normalized.rstrip("/")

    return normalized


def _normalize_query(
    query: str,
    *,
    platform: str,
) -> str:
    """
    Remove tracking/crawler query parameters.

    Most social profile URLs do not require query parameters for
    canonical identity. Platform-specific resource parameters that
    materially identify a resource can be preserved here later.
    """

    if not query:
        return ""

    ignored_prefixes = (
        "utm_",
        "fbclid",
        "gclid",
        "mc_",
    )

    pairs = parse_qsl(
        query,
        keep_blank_values=False,
    )

    filtered = [
        (key, value)
        for key, value in pairs
        if not key.lower().startswith(ignored_prefixes)
    ]

    if not filtered:
        return ""

    # For company/profile URLs, query parameters are normally
    # unnecessary and can create duplicate identities.
    if platform in {
        "linkedin",
        "instagram",
        "facebook",
        "x",
        "github",
        "tiktok",
    }:
        return ""

    return urlencode(
        filtered,
        doseq=True,
    )