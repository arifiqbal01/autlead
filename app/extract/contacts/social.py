from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import urlparse

from app.models.schemas.contacts import (
    ContactEvidence,
    ContactExtractionResult,
)


SOCIAL_DOMAINS = {
    "linkedin.com": "linkedin",
    "facebook.com": "facebook",
    "instagram.com": "instagram",
    "x.com": "x",
    "twitter.com": "x",
    "youtube.com": "youtube",
    "github.com": "github",
    "tiktok.com": "tiktok",
}


FACEBOOK_IGNORED_PATHS = {
    "/login",
    "/recover",
    "/photo",
    "/profile.php",
    "/privacy",
    "/privacy/policy",
    "/policies",
    "/business",
    "/help",
}


INSTAGRAM_IGNORED_PATHS = {
    "/accounts/login",
    "/accounts/emailsignup",
    "/accounts/signup",
    "/legal/privacy",
    "/legal/terms",
    "/explore",
    "/explore/locations",
    "/popular",
    "/web/lite",
    "/accounts/meta_verified",
}


YOUTUBE_IGNORED_PATHS = {
    "/",
    "/about",
    "/feed",
    "/shorts",
}


TIKTOK_IGNORED_PATHS = {
    "/",
    "/login",
    "/signup",
}


def extract_social_urls(
    *,
    urls: Iterable[str],
    source_url,
    result: ContactExtractionResult,
    seen: set[str],
) -> None:
    """
    Classify and add useful social URLs.

    Duplicate canonical URLs are ignored across all crawled pages.
    """

    for url in urls:
        classified = classify_social_url(url)

        if classified is None:
            continue

        platform, canonical_url = classified

        if canonical_url in seen:
            continue

        seen.add(canonical_url)

        _add_social_result(
            platform=platform,
            url=canonical_url,
            source_url=source_url,
            result=result,
        )


def classify_social_url(
    url: str,
) -> tuple[str, str] | None:
    """
    Classify a URL as a useful social profile or page.

    Normalization performed here is extraction-level only:

    - lowercase hostname
    - remove ``www.``
    - remove query strings and fragments
    - normalize Twitter URLs to x.com
    - reject generic platform navigation URLs
    """

    raw_url = url.strip()

    if not raw_url:
        return None

    parsed = urlparse(raw_url)

    if parsed.scheme.casefold() not in {
        "http",
        "https",
    }:
        return None

    hostname = (
        parsed.hostname or ""
    ).casefold().removeprefix("www.")

    if not hostname:
        return None

    platform = SOCIAL_DOMAINS.get(
        hostname,
    )

    if platform is None:
        return None

    path = _normalize_path(
        parsed.path,
    )

    if not path:
        return None

    if platform == "facebook":
        if not _is_useful_facebook_path(path):
            return None

    elif platform == "instagram":
        if not _is_useful_instagram_path(path):
            return None

    elif platform == "linkedin":
        if not _is_useful_linkedin_path(path):
            return None

    elif platform == "youtube":
        if not _is_useful_youtube_path(path):
            return None

    elif platform == "tiktok":
        if not _is_useful_tiktok_path(path):
            return None

    elif platform == "github":
        if not _is_useful_github_path(path):
            return None

    elif platform == "x":
        if not _is_useful_x_path(path):
            return None

        # Canonicalize both twitter.com and x.com to x.com.
        hostname = "x.com"

    canonical_url = (
        f"https://{hostname}{path}"
    )

    return platform, canonical_url


def _add_social_result(
    *,
    platform: str,
    url: str,
    source_url,
    result: ContactExtractionResult,
) -> None:
    """
    Add a classified social URL to ContactExtractionResult and
    retain provenance through ContactEvidence.
    """

    if platform == "linkedin":
        path = urlparse(url).path.casefold()

        if (
            path.startswith("/company/")
            or path.startswith("/school/")
        ):
            result.linkedin_company_urls.append(
                url
            )
            kind = "linkedin_company"

        elif path.startswith("/in/"):
            result.linkedin_profile_urls.append(
                url
            )
            kind = "linkedin_profile"

        else:
            return

    elif platform == "facebook":
        result.facebook_urls.append(url)
        kind = "facebook"

    elif platform == "instagram":
        result.instagram_urls.append(url)
        kind = "instagram"

    elif platform == "x":
        result.x_urls.append(url)
        kind = "x"

    elif platform == "youtube":
        result.youtube_urls.append(url)
        kind = "youtube"

    elif platform == "github":
        result.github_urls.append(url)
        kind = "github"

    elif platform == "tiktok":
        result.tiktok_urls.append(url)
        kind = "tiktok"

    else:
        return

    result.evidence.append(
        ContactEvidence(
            value=url,
            source_url=source_url,
            kind=kind,
        )
    )


def _normalize_path(
    path: str,
) -> str:
    """
    Normalize a social URL path without changing its identity.

    Root URLs are preserved as ``/`` so platform-specific filters
    can reject them explicitly.
    """

    path = path.strip()

    if not path:
        return "/"

    if not path.startswith("/"):
        path = f"/{path}"

    if path != "/":
        path = path.rstrip("/")

    return path


def _is_useful_facebook_path(
    path: str,
) -> bool:
    path_lower = path.casefold()

    if path_lower in FACEBOOK_IGNORED_PATHS:
        return False

    if any(
        path_lower.startswith(prefix)
        for prefix in (
            "/login/",
            "/recover/",
            "/privacy/",
            "/policies/",
            "/help/",
            "/business/",
        )
    ):
        return False

    return path_lower != "/"


def _is_useful_instagram_path(
    path: str,
) -> bool:
    path_lower = path.casefold()

    if path_lower in INSTAGRAM_IGNORED_PATHS:
        return False

    if path_lower.startswith(
        (
            "/accounts/",
            "/legal/",
        )
    ):
        return False

    return path_lower != "/"


def _is_useful_linkedin_path(
    path: str,
) -> bool:
    path_lower = path.casefold()

    return (
        path_lower.startswith("/company/")
        or path_lower.startswith("/school/")
        or path_lower.startswith("/in/")
    )


def _is_useful_youtube_path(
    path: str,
) -> bool:
    path_lower = path.casefold()

    if path_lower in YOUTUBE_IGNORED_PATHS:
        return False

    return (
        path_lower.startswith("/@")
        or path_lower.startswith("/channel/")
        or path_lower.startswith("/c/")
        or path_lower.startswith("/user/")
    )


def _is_useful_tiktok_path(
    path: str,
) -> bool:
    path_lower = path.casefold()

    if path_lower in TIKTOK_IGNORED_PATHS:
        return False

    return path_lower.startswith("/@")


def _is_useful_github_path(
    path: str,
) -> bool:
    """
    Accept GitHub user or organization profile URLs while rejecting
    common platform-level navigation URLs.
    """

    path_lower = path.casefold()

    ignored = {
        "/",
        "/login",
        "/signup",
        "/features",
        "/pricing",
        "/enterprise",
        "/marketplace",
        "/explore",
        "/topics",
        "/trending",
    }

    if path_lower in ignored:
        return False

    parts = [
        part
        for part in path_lower.split("/")
        if part
    ]

    # A GitHub profile normally has at least one path segment.
    return bool(parts)


def _is_useful_x_path(
    path: str,
) -> bool:
    """
    Accept X/Twitter profile URLs while rejecting platform routes.
    """

    path_lower = path.casefold()

    ignored = {
        "/",
        "/home",
        "/explore",
        "/search",
        "/notifications",
        "/messages",
        "/i",
        "/settings",
        "/login",
        "/signup",
    }

    if path_lower in ignored:
        return False

    if path_lower.startswith(
        (
            "/i/",
            "/settings/",
            "/search/",
        )
    ):
        return False

    parts = [
        part
        for part in path_lower.split("/")
        if part
    ]

    return bool(parts)


__all__ = [
    "classify_social_url",
    "extract_social_urls",
]