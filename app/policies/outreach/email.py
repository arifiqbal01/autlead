# app/policies/outreach/email.py

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmailSendContext:
    verification_status: str | None
    verification_confidence: float | None
    already_sent: bool
    suppressed: bool = False


@dataclass(frozen=True)
class EmailSendDecision:
    allowed: bool
    reason: str


def can_send_email(
    context: EmailSendContext,
    *,
    minimum_confidence: float,
    allowed_statuses: set[str],
    skip_previously_sent: bool = True,
) -> EmailSendDecision:
    if context.suppressed:
        return EmailSendDecision(
            allowed=False,
            reason="suppressed",
        )

    if (
        skip_previously_sent
        and context.already_sent
    ):
        return EmailSendDecision(
            allowed=False,
            reason="already_sent",
        )

    if (
        context.verification_status
        not in allowed_statuses
    ):
        return EmailSendDecision(
            allowed=False,
            reason="verification_status_not_allowed",
        )

    if context.verification_confidence is None:
        return EmailSendDecision(
            allowed=False,
            reason="verification_confidence_missing",
        )

    if (
        context.verification_confidence
        < minimum_confidence
    ):
        return EmailSendDecision(
            allowed=False,
            reason="verification_confidence_too_low",
        )

    return EmailSendDecision(
        allowed=True,
        reason="eligible",
    )