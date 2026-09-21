from __future__ import annotations

import re
from collections.abc import Iterable
from urllib.parse import unquote


PHONE_RE = re.compile(
    r"""
    (?<![\d@])
    (?:
        # Explicit international number.
        \+
        \d{1,3}
        [\s().-]?
        (?:\d[\s().-]?){6,13}

        |

        # Formatted national number.
        (?:
            \(\d{2,5}\)
            |
            \d{2,5}
        )
        [\s.-]
        \d{2,5}
        (?:[\s.-]\d{2,5}){1,3}
    )
    (?![\d@])
    """,
    re.VERBOSE,
)


def extract_phones(
    *,
    text: str,
    tel_links: Iterable[str] = (),
) -> list[str]:
    """
    Extract phone-number candidates from visible text and tel links.

    This is extraction only. It does not perform country-aware
    validation or international conversion.

    Country-aware normalization and validation belong in:

        app.transform.normalization.phone
    """

    found: dict[str, str] = {}

    # ---------------------------------------------------------
    # Numbers in visible text.
    # ---------------------------------------------------------

    for match in PHONE_RE.finditer(text):
        phone = normalize_phone(match.group())

        if not is_plausible_phone(phone):
            continue

        found.setdefault(
            phone_identity(phone),
            phone,
        )

    # ---------------------------------------------------------
    # Explicit tel: links.
    #
    # These are strong evidence and may contain compact numbers
    # that would not match PHONE_RE.
    # ---------------------------------------------------------

    for value in tel_links:
        phone = normalize_phone(value)

        if not is_plausible_phone(phone):
            continue

        found.setdefault(
            phone_identity(phone),
            phone,
        )

    return sorted(found.values())


def normalize_phone(value: str) -> str:
    """
    Normalize phone formatting without country-specific rules.

    Examples:

        "+92 333-214226"
            -> "+92333214226"

        "0333 214226"
            -> "0333214226"

        "tel:+31 (0)20 123 4567"
            -> "+310201234567"

    National-to-international conversion is deliberately not done
    here because extraction does not know the company's country.
    """

    value = unquote(value).strip()

    if value.lower().startswith("tel:"):
        value = value[4:]

    # Remove tel URI parameters such as:
    #
    # tel:+92333214226;ext=123
    #
    value = value.split("?", 1)[0]
    value = value.split(";", 1)[0].strip()

    has_plus = value.startswith("+")
    digits = re.sub(r"\D", "", value)

    if not digits:
        return ""

    if has_plus:
        return f"+{digits}"

    return digits


def phone_identity(value: str) -> str:
    """
    Return a digits-only identity for extraction-level deduplication.

    This intentionally does not perform country-aware equivalence.

    For example:

        "+92333214226"
        "92333214226"

    have the same extraction identity.
    """

    return re.sub(r"\D", "", value)


def is_plausible_phone(value: str) -> bool:
    """
    Perform conservative country-agnostic candidate filtering.

    This is NOT phone-number validation.

    It only rejects values that are clearly unsuitable as phone
    candidates, such as extremely short, extremely long, or
    repeated-digit values.

    Proper country-aware validation belongs in the Transform layer.
    """

    digits = phone_identity(value)

    if not 7 <= len(digits) <= 15:
        return False

    # Reject obvious dummy values such as:
    #
    # 0000000000
    # 1111111111
    # 999999999999
    #
    if len(set(digits)) == 1:
        return False

    return True