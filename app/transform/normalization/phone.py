from __future__ import annotations

from collections.abc import Iterable

import phonenumbers
from phonenumbers import NumberParseException
from phonenumbers.phonenumberutil import PhoneNumberType


# ISO 3166-1 alpha-2 country codes commonly useful for Autlead.
# This is mainly a convenience layer; phonenumbers supports many more.
SUPPORTED_REGIONS = {
    "PK": "Pakistan",
    "GB": "United Kingdom",
    "US": "United States",
    "CA": "Canada",
    "AU": "Australia",
    "NL": "Netherlands",
    "DE": "Germany",
    "FR": "France",
    "BE": "Belgium",
    "ES": "Spain",
    "IT": "Italy",
    "PT": "Portugal",
    "IE": "Ireland",
    "AT": "Austria",
    "CH": "Switzerland",
    "SE": "Sweden",
    "NO": "Norway",
    "DK": "Denmark",
    "FI": "Finland",
    "PL": "Poland",
    "CZ": "Czech Republic",
    "HU": "Hungary",
    "RO": "Romania",
    "GR": "Greece",
    "AE": "United Arab Emirates"
}


def normalize_phone(
    value: str,
    *,
    region: str | None = None,
) -> str | None:
    """
    Normalize a phone number to E.164 format.

    ``region`` is required for national numbers without a country
    code and should be the ISO 3166-1 alpha-2 country code.

    Examples:

        normalize_phone("+92 333 214226")
        -> "+92333214226"

        normalize_phone("0333 214226", region="PK")
        -> "+92333214226"

        normalize_phone("020 7946 0018", region="GB")
        -> "+442079460018"

        normalize_phone("(212) 555-0123", region="US")
        -> "+12125550123"

        normalize_phone("020 1234 5678", region="NL")
        -> "+312012345678"
    """

    value = value.strip()

    if not value:
        return None

    region = _normalize_region(region)

    try:
        parsed = phonenumbers.parse(value, region)
    except NumberParseException:
        return None

    if not phonenumbers.is_possible_number(parsed):
        return None

    if not phonenumbers.is_valid_number(parsed):
        return None

    return phonenumbers.format_number(
        parsed,
        phonenumbers.PhoneNumberFormat.E164,
    )


def normalize_phones(
    values: Iterable[str],
    *,
    region: str | None = None,
) -> list[str]:
    """
    Normalize and deduplicate phone numbers.

    Invalid numbers are discarded.
    Results are returned in deterministic order.
    """

    normalized: set[str] = set()

    for value in values:
        phone = normalize_phone(
            value,
            region=region,
        )

        if phone:
            normalized.add(phone)

    return sorted(normalized)


def is_valid_phone(
    value: str,
    *,
    region: str | None = None,
) -> bool:
    """Return whether a phone number is valid for the supplied region."""

    return normalize_phone(
        value,
        region=region,
    ) is not None


def phone_type(
    value: str,
    *,
    region: str | None = None,
) -> str | None:
    """
    Return the libphonenumber phone type.

    Examples include:

        mobile
        fixed_line
        fixed_line_or_mobile
        toll_free
        premium_rate
        unknown
    """

    normalized = normalize_phone(
        value,
        region=region,
    )

    if normalized is None:
        return None

    try:
        parsed = phonenumbers.parse(normalized, None)
    except NumberParseException:
        return None

    number_type = phonenumbers.number_type(parsed)

    mapping = {
        PhoneNumberType.MOBILE: "mobile",
        PhoneNumberType.FIXED_LINE: "fixed_line",
        PhoneNumberType.FIXED_LINE_OR_MOBILE: "fixed_line_or_mobile",
        PhoneNumberType.TOLL_FREE: "toll_free",
        PhoneNumberType.PREMIUM_RATE: "premium_rate",
        PhoneNumberType.SHARED_COST: "shared_cost",
        PhoneNumberType.VOIP: "voip",
        PhoneNumberType.PERSONAL_NUMBER: "personal_number",
        PhoneNumberType.PAGER: "pager",
        PhoneNumberType.UAN: "uan",
        PhoneNumberType.VOICEMAIL: "voicemail",
        PhoneNumberType.UNKNOWN: "unknown",
    }

    return mapping.get(number_type, "unknown")


def _normalize_region(region: str | None) -> str | None:
    """Normalize and validate an ISO country/region code."""

    if region is None:
        return None

    normalized = region.strip().upper()

    if not normalized:
        return None

    if len(normalized) != 2:
        raise ValueError(
            f"Invalid phone region {region!r}. "
            "Expected an ISO 3166-1 alpha-2 country code."
        )

    if normalized not in SUPPORTED_REGIONS:
        raise ValueError(
            f"Unsupported phone region {normalized!r}. "
            "Add the ISO country code to SUPPORTED_REGIONS."
        )

    return normalized