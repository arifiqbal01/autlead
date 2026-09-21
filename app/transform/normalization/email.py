# app/transform/normalization/email.py

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import unquote


EMAIL_RE = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+"
    r"@"
    r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$",
    re.IGNORECASE,
)


FREE_EMAIL_PROVIDERS = frozenset(
    {
        "gmail.com",
        "googlemail.com",
        "outlook.com",
        "hotmail.com",
        "live.com",
        "msn.com",
        "yahoo.com",
        "yahoo.co.uk",
        "icloud.com",
        "me.com",
        "mac.com",
        "proton.me",
        "protonmail.com",
        "zoho.com",
        "aol.com",
        "gmx.com",
        "gmx.net",
        "mail.com",
        "yandex.com",
        "yandex.ru",
    }
)


ROLE_EMAIL_PREFIXES = frozenset(
    {
        "admin",
        "contact",
        "enquiries",
        "enquiry",
        "hello",
        "help",
        "info",
        "inquiries",
        "inquiry",
        "marketing",
        "office",
        "sales",
        "support",
    }
)


@dataclass(frozen=True, slots=True)
class NormalizedEmail:
    """Normalized and classified email address."""

    address: str
    local_part: str
    domain: str
    provider: str | None
    is_free_provider: bool
    is_role_address: bool


def normalize_email(value: str) -> str | None:
    """
    Normalize and validate an email address.

    This function performs deterministic normalization only. It does
    not verify whether the mailbox actually exists.
    """

    email = unquote(value).strip().lower()

    if email.startswith("mailto:"):
        email = email[7:]

    email = email.split("?", 1)[0]
    email = email.split("#", 1)[0]
    email = email.strip()

    if not EMAIL_RE.fullmatch(email):
        return None

    local_part, domain = email.rsplit("@", 1)

    if not local_part or not domain:
        return None

    if domain.startswith(".") or domain.endswith("."):
        return None

    if ".." in domain:
        return None

    return email


def normalize_emails(values: list[str] | tuple[str, ...]) -> list[str]:
    """Normalize emails and remove duplicates."""

    found: set[str] = set()

    for value in values:
        email = normalize_email(value)

        if email:
            found.add(email)

    return sorted(found)


def parse_email(value: str) -> NormalizedEmail | None:
    """
    Normalize an email and derive useful deterministic attributes.

    Provider classification is based on a known free-email-provider
    list. Unknown domains remain business/custom domains rather than
    being incorrectly classified.
    """

    email = normalize_email(value)

    if email is None:
        return None

    local_part, domain = email.rsplit("@", 1)

    provider = domain if domain in FREE_EMAIL_PROVIDERS else None

    return NormalizedEmail(
        address=email,
        local_part=local_part,
        domain=domain,
        provider=provider,
        is_free_provider=provider is not None,
        is_role_address=is_role_email(local_part),
    )


def email_domain(value: str) -> str | None:
    """Return the normalized domain portion of an email."""

    email = normalize_email(value)

    if email is None:
        return None

    return email.rsplit("@", 1)[1]


def email_local_part(value: str) -> str | None:
    """Return the normalized local portion of an email."""

    email = normalize_email(value)

    if email is None:
        return None

    return email.rsplit("@", 1)[0]


def is_free_email_provider(value: str) -> bool:
    """Return whether the email uses a known free email provider."""

    domain = email_domain(value)

    return domain in FREE_EMAIL_PROVIDERS if domain else False


def is_role_email(value: str) -> bool:
    """
    Return whether the local part represents a generic business role.

    Examples:
        info@example.com
        sales@example.com
        support@example.com
    """

    local_part = email_local_part(value)

    if local_part is None:
        return False

    # Handle common role aliases such as info+leads@example.com.
    role = local_part.split("+", 1)[0]

    return role in ROLE_EMAIL_PREFIXES


def email_quality(value: str) -> str | None:
    """
    Return a simple deterministic email quality classification.

    Values:
        business_role
        business_individual
        free_provider
    """

    parsed = parse_email(value)

    if parsed is None:
        return None

    if parsed.is_free_provider:
        return "free_provider"

    if parsed.is_role_address:
        return "business_role"

    return "business_individual"