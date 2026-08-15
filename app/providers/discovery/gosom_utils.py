from __future__ import annotations

import csv
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.providers.discovery.exceptions import BusinessDiscoveryProviderError


def read_results(
    results_file: Path,
) -> list[Mapping[str, Any]]:
    with results_file.open(
        newline="",
        encoding="utf-8",
    ) as file:
        return list(csv.DictReader(file))


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
        return parts[0], parts[-1]

    return parts[0], None


def deduplicate(
    businesses: list[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    seen: set[str] = set()
    result: list[Mapping[str, Any]] = []

    for business in businesses:
        place_id = optional_text(
            business.get("place_id")
            or business.get("cid")
            or business.get("link")
        )

        if place_id is None:
            result.append(business)
            continue

        if place_id in seen:
            continue

        seen.add(place_id)
        result.append(business)

    return result


def extract_domain(
    value: str | None,
) -> str | None:
    if not value:
        return None

    parsed = urlparse(value)

    hostname = parsed.hostname
    if not hostname:
        return None

    hostname = hostname.lower()

    if hostname.startswith("www."):
        hostname = hostname[4:]

    return hostname


def optional_text(
    value: object,
) -> str | None:
    if value is None:
        return None

    text = str(value).strip()

    return text or None


def required_text(
    value: object,
    field_name: str,
) -> str:
    text = optional_text(value)

    if text is None:
        raise BusinessDiscoveryProviderError(
            f"Missing required discovery field: {field_name}"
        )

    return text