from __future__ import annotations

import re
from collections.abc import Iterable
from urllib.parse import unquote


EMAIL_RE = re.compile(
    r"(?<![\w.+-])"
    r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+"
    r"@"
    r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+"
    r"(?![\w.-])",
    re.IGNORECASE,
)


def extract_emails(
    *,
    text: str,
    mailto_links: Iterable[str] = (),
) -> list[str]:
    """
    Extract email candidates from website content.

    Extraction identifies plausible email-shaped values only.
    Canonical validation and classification belong to the
    transform/normalization layer.
    """

    found: set[str] = set()

    for match in EMAIL_RE.findall(text):
        value = _clean_candidate(match)

        if value:
            found.add(value)

    for link in mailto_links:
        value = _extract_mailto(link)

        if value:
            found.add(value)

    return sorted(found)


def _extract_mailto(
    value: str,
) -> str | None:
    value = unquote(value).strip()

    if value.casefold().startswith("mailto:"):
        value = value[7:]

    value = value.split("?", 1)[0]
    value = value.split("#", 1)[0]

    return _clean_candidate(value)


def _clean_candidate(
    value: str,
) -> str | None:
    value = unquote(value).strip()

    if not value:
        return None

    # Avoid obvious crawler/path artifacts.
    if any(
        marker in value
        for marker in (
            "//",
            "/",
            "\\",
        )
    ):
        return None

    return value