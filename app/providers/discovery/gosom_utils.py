from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

from app.providers.discovery.exceptions import (
    BusinessDiscoveryProviderError,
)


def parse_location(
    location: str | None,
) -> tuple[str | None, str | None]:
    if not location:
        return None, None

    parts = [
        part.strip()
        for part in location.split(",")
        if part.strip()
    ]

    if len(parts) >= 2:
        return (
            parts[0],
            parts[-1],
        )

    return (
        parts[0],
        None,
    )


def deduplicate(
    businesses: list[
        Mapping[str, Any]
    ],
) -> list[
    Mapping[str, Any]
]:
    """
    Deduplicate repeated Google Maps listings from Gosom.

    Provider-level identity should use Google Maps identifiers.

    Website/domain is deliberately NOT used here because multiple
    legitimate Maps listings may share the same company website.
    """

    seen_ids: set[str] = set()

    result: list[
        Mapping[str, Any]
    ] = []

    for business in businesses:
        external_id = extract_external_id(
            business
        )

        if (
            external_id is not None
            and external_id in seen_ids
        ):
            continue

        if external_id is not None:
            seen_ids.add(
                external_id
            )

        result.append(
            business
        )

    return result


def extract_external_id(
    business: Mapping[str, Any],
) -> str | None:
    """
    Return the strongest available Google Maps identity.

    Preference:
        place_id
        cid
        data_id

    `link` is not used as an identity fallback.
    """

    for field in (
        "place_id",
        "cid",
        "data_id",
    ):
        value = optional_text(
            business.get(field)
        )

        if value is not None:
            return value

    return None


def extract_domain(
    value: str | None,
) -> str | None:
    if not value:
        return None

    value = value.strip()

    if not value:
        return None

    if "://" not in value:
        value = f"https://{value}"

    parsed = urlparse(
        value
    )

    hostname = parsed.hostname

    if not hostname:
        return None

    hostname = hostname.lower()

    if hostname.startswith(
        "www."
    ):
        hostname = hostname[4:]

    return hostname


def optional_text(
    value: object,
) -> str | None:
    if value is None:
        return None

    text = str(
        value
    ).strip()

    return (
        text
        or None
    )


def required_text(
    value: object,
    field_name: str,
) -> str:
    text = optional_text(
        value
    )

    if text is None:
        raise BusinessDiscoveryProviderError(
            "Missing required discovery field: "
            f"{field_name}"
        )

    return text