from __future__ import annotations

import pytest

from app.transform.normalization.phone import (
    is_valid_phone,
    normalize_phone,
    normalize_phones,
    phone_type,
)


@pytest.mark.parametrize(
    ("value", "region", "expected"),
    [
        # Pakistan
        ("0333 3214226", "PK", "+923333214226"),
        ("+92 333 3214226", None, "+923333214226"),
        ("0303-2737773", "PK", "+923032737773"),

        # United Kingdom
        ("020 7946 0018", "GB", "+442079460018"),
        ("+44 20 7946 0018", None, "+442079460018"),

        # United States
        ("(212) 555-0123", "US", "+12125550123"),
        ("+1 212 555 0123", None, "+12125550123"),

        # Canada
        ("416-555-0123", "CA", "+14165550123"),

        # Netherlands
        ("020 123 4567", "NL", "+31201234567"),
        ("+31 20 123 4567", None, "+31201234567"),

        # Australia
        ("02 9374 4000", "AU", "+61293744000"),
        ("+61 2 9374 4000", None, "+61293744000"),
    ],
)
def test_normalize_phone(
    value: str,
    region: str | None,
    expected: str,
) -> None:
    assert normalize_phone(
        value,
        region=region,
    ) == expected


@pytest.mark.parametrize(
    ("value", "region"),
    [
        ("20230922", "PK"),
        ("202209232028", "PK"),
        ("20240913", "PK"),
        ("20260108", "PK"),
        ("1111111111", "PK"),
        ("123", "PK"),
        ("not a phone", "PK"),
    ],
)
def test_reject_invalid_phone(
    value: str,
    region: str,
) -> None:
    assert normalize_phone(
        value,
        region=region,
    ) is None

    assert not is_valid_phone(
        value,
        region=region,
    )


def test_normalize_phones_deduplicates_formats() -> None:
    values = [
        "+923333214226",
        "0333 3214226",
        "+92 333 3214226",
        "0333-3214226",
    ]

    result = normalize_phones(
        values,
        region="PK",
    )

    assert result == [
        "+923333214226",
    ]


@pytest.mark.parametrize(
    ("value", "region", "expected_type"),
    [
        ("0333 3214226", "PK", "mobile"),
        ("0303 2737773", "PK", "mobile"),
        ("020 7946 0018", "GB", "fixed_line"),
    ],
)
def test_phone_type(
    value: str,
    region: str,
    expected_type: str,
) -> None:
    assert phone_type(
        value,
        region=region,
    ) == expected_type


@pytest.mark.parametrize(
    ("value", "region"),
    [
        ("20230922", "PK"),
        ("202209232028", "PK"),
        ("20240913", "PK"),
        ("20260108", "PK"),
        ("0333 214226", "PK"),  # incomplete Pakistani mobile number
        ("1111111111", "PK"),
        ("123", "PK"),
        ("not a phone", "PK"),
    ],
)
def test_reject_invalid_phone(
    value: str,
    region: str,
) -> None:
    assert normalize_phone(
        value,
        region=region,
    ) is None

    assert not is_valid_phone(
        value,
        region=region,
    )