from __future__ import annotations

import pytest

from app.providers.email.verification.errors import (
    MrEmailCheckerTimeoutError,
)
from app.providers.email.verification.models import (
    EmailVerificationRequest,
)
from app.providers.email.verification.mr_email_checker import (
    MrEmailCheckerProvider,
)


pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


def _create_provider() -> MrEmailCheckerProvider:
    return MrEmailCheckerProvider(
        timeout_seconds=30.0,
        smtp_enabled=True,
        smtp_from="verify@enrichment.nl",
        smtp_helo_host="enrichment.nl",
        smtp_timeout_ms=10_000,
        detect_catch_all=False,
    )


async def test_mr_email_checker_known_webartsy_email() -> None:
    email = "arif@enrichment.nl"
    provider = _create_provider()

    try:
        result = await provider.verify(
            EmailVerificationRequest(
                email=email,
            )
        )
    except MrEmailCheckerTimeoutError:
        pytest.skip(
            "Live mr-email-checker verification timed out."
        )

    print()
    print("email:", result.email)
    print("canonical:", result.canonical)
    print("status:", result.status)
    print("valid:", result.valid)
    print("score:", result.score)
    print("risk:", result.risk)
    print(
        "smtp verdict:",
        result.smtp.verdict,
    )
    print(
        "smtp code:",
        result.smtp.code,
    )
    print(
        "smtp message:",
        result.smtp.message,
    )
    print(
        "catch all:",
        result.smtp.catch_all,
    )
    print(
        "smtp latency ms:",
        result.smtp.latency_ms,
    )
    print(
        "reasons:",
        result.reasons,
    )

    assert result.provider == "mr_email_checker"
    assert result.email == email

    assert result.status in {
        "deliverable",
        "risky",
        "undeliverable",
        "unknown",
    }

    assert result.smtp.verdict in {
        "deliverable",
        "undeliverable",
        "catch_all",
        "greylisted",
        "blocked",
        "timeout",
        "skipped",
        "unknown",
    }

    assert isinstance(
        result.smtp.catch_all,
        bool,
    )


async def test_mr_email_checker_agroasia_response_parses() -> None:
    email = "atif.rehman@agroasiatractors.ae"
    provider = _create_provider()

    try:
        result = await provider.verify(
            EmailVerificationRequest(
                email=email,
            )
        )
    except MrEmailCheckerTimeoutError:
        pytest.skip(
            "Live mr-email-checker verification timed out."
        )

    print()
    print("email:", result.email)
    print("canonical:", result.canonical)
    print("status:", result.status)
    print("valid:", result.valid)
    print("score:", result.score)
    print("risk:", result.risk)
    print(
        "smtp verdict:",
        result.smtp.verdict,
    )
    print(
        "smtp code:",
        result.smtp.code,
    )
    print(
        "smtp message:",
        result.smtp.message,
    )
    print(
        "catch all:",
        result.smtp.catch_all,
    )
    print(
        "smtp latency ms:",
        result.smtp.latency_ms,
    )
    print(
        "reasons:",
        result.reasons,
    )

    assert result.provider == "mr_email_checker"
    assert result.email == email

    assert result.status in {
        "deliverable",
        "risky",
        "undeliverable",
        "unknown",
    }

    assert result.smtp.verdict in {
        "deliverable",
        "undeliverable",
        "catch_all",
        "greylisted",
        "blocked",
        "timeout",
        "skipped",
        "unknown",
    }

    assert isinstance(
        result.smtp.catch_all,
        bool,
    )

    if (
        result.smtp.message
        and "spamhaus"
        in result.smtp.message.casefold()
    ):
        assert result.smtp.verdict == "blocked"
        assert result.status == "unknown"
        assert result.valid is False
        assert (
            "mailbox_not_found"
            not in result.reasons
        )
        assert "smtp_blocked" in result.reasons