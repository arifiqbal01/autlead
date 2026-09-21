from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

DEFAULT_EMAIL_PATTERN_LIMIT = 8


def generate_person_email_candidates(
    *,
    name: str,
    domain: str,
    limit: int = DEFAULT_EMAIL_PATTERN_LIMIT,
) -> list[str]:
    """
    Generate deterministic email candidates from a person's name
    and a company domain.

    This function only generates candidates. It does not perform
    verification, persistence, qualification, or provider calls.

    Example:

        name="John Smith"
        domain="example.com"

        [
            "john.smith@example.com",
            "john@example.com",
            "jsmith@example.com",
            "johns@example.com",
            "johnsmith@example.com",
            "john_smith@example.com",
            "john-smith@example.com",
        ]
    """

    if limit < 1:
        return []

    normalized_domain = _normalize_domain(
        domain
    )

    if not normalized_domain:
        return []

    name_parts = _normalize_name_parts(
        name
    )

    if not name_parts:
        return []

    local_parts = _generate_local_parts(
        name_parts
    )

    candidates: list[str] = []

    for local_part in local_parts:
        if not local_part:
            continue

        email = (
            f"{local_part}@"
            f"{normalized_domain}"
        )

        if email in candidates:
            continue

        candidates.append(
            email
        )

        if len(candidates) >= limit:
            break

    return candidates


def _normalize_domain(
    domain: str,
) -> str:
    """
    Normalize a company domain into a bare hostname.

    Examples:

        https://www.example.com/about
            -> example.com

        www.example.com
            -> example.com

        example.com
            -> example.com
    """

    value = (
        domain.strip()
        .casefold()
    )

    if not value:
        return ""

    value = re.sub(
        r"^[a-z][a-z0-9+.-]*://",
        "",
        value,
    )

    value = value.split(
        "/",
        1,
    )[0]

    value = value.split(
        "?",
        1,
    )[0]

    value = value.split(
        "#",
        1,
    )[0]

    if value.startswith(
        "www."
    ):
        value = value[4:]

    # Remove a simple explicit port if one was provided.
    if ":" in value:
        hostname, separator, port = (
            value.rpartition(":")
        )

        if (
            separator
            and hostname
            and port.isdigit()
        ):
            value = hostname

    value = value.strip(
        "."
    )

    if not _looks_like_domain(
        value
    ):
        return ""

    return value


def _normalize_name_parts(
    name: str,
) -> list[str]:
    """
    Normalize a human name into ASCII-safe email components.

    Titles and punctuation are removed conservatively.

    Example:

        "Dr. José van Dijk"
            -> ["jose", "van", "dijk"]
    """

    normalized = _ascii_fold(
        name
    ).casefold()

    normalized = re.sub(
        r"[^a-z0-9\s'-]+",
        " ",
        normalized,
    )

    raw_parts = re.split(
        r"[\s'-]+",
        normalized,
    )

    parts = [
        part
        for part in raw_parts
        if part
        and part not in _NAME_TITLES
    ]

    return parts


def _generate_local_parts(
    parts: list[str],
) -> list[str]:
    """
    Generate common mailbox naming patterns in priority order.
    """

    if not parts:
        return []

    first = parts[0]

    if len(parts) == 1:
        return [
            first,
        ]

    last = parts[-1]
    middle = parts[1:-1]

    first_initial = (
        first[0]
        if first
        else ""
    )

    last_initial = (
        last[0]
        if last
        else ""
    )

    full_compact = "".join(
        parts
    )

    full_dotted = ".".join(
        parts
    )

    local_parts = [
        f"{first}.{last}",
        first,
        f"{first_initial}{last}",
        f"{first}{last_initial}",
        f"{first}{last}",
        full_dotted,
        full_compact,
        f"{first}_{last}",
        f"{first}-{last}",
    ]

    # For names such as:
    #
    #     Atif Ur Rehman
    #
    # include useful middle-name variants without letting the
    # candidate list grow indefinitely.
    if middle:
        local_parts.extend(
            [
                (
                    f"{first}."
                    f"{'.'.join(middle)}."
                    f"{last}"
                ),
                (
                    f"{first}"
                    f"{''.join(middle)}"
                    f"{last}"
                ),
                (
                    f"{first}."
                    f"{last}"
                ),
            ]
        )

    return _deduplicate(
        local_parts
    )


def _deduplicate(
    values: Iterable[str],
) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    for value in values:
        normalized = (
            value.strip()
            .casefold()
        )

        if (
            not normalized
            or normalized in seen
        ):
            continue

        seen.add(
            normalized
        )

        result.append(
            normalized
        )

    return result


def _ascii_fold(
    value: str,
) -> str:
    normalized = unicodedata.normalize(
        "NFKD",
        value,
    )

    return "".join(
        character
        for character in normalized
        if not unicodedata.combining(
            character
        )
    )


def _looks_like_domain(
    value: str,
) -> bool:
    if not value:
        return False

    if "@" in value:
        return False

    if "." not in value:
        return False

    if (
        value.startswith(".")
        or value.endswith(".")
    ):
        return False

    labels = value.split(
        "."
    )

    if len(labels) < 2:
        return False

    for label in labels:
        if not label:
            return False

        if (
            label.startswith("-")
            or label.endswith("-")
        ):
            return False

        if not re.fullmatch(
            r"[a-z0-9-]+",
            label,
        ):
            return False

    return True


_NAME_TITLES = {
    "mr",
    "mrs",
    "ms",
    "miss",
    "dr",
    "prof",
    "sir",
}