# app/policies/qualification/email.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


EmailVerificationStatus = Literal[
    "deliverable",
    "risky",
    "undeliverable",
    "unknown",
]

EmailVerificationRisk = Literal[
    "low",
    "medium",
    "high",
]

EmailSmtpVerdict = Literal[
    "deliverable",
    "undeliverable",
    "catch_all",
    "greylisted",
    "blocked",
    "timeout",
    "skipped",
]


@dataclass(frozen=True, slots=True)
class EmailVerificationAssessment:
    status: EmailVerificationStatus
    valid: bool
    score: int
    risk: EmailVerificationRisk
    smtp_verdict: EmailSmtpVerdict
    is_role_account: bool = False
    is_disposable: bool = False


@dataclass(frozen=True, slots=True)
class EmailQualificationDecision:
    is_qualified: bool
    status: EmailVerificationStatus
    confidence: float
    reason: str


def evaluate_email_qualification(
    assessment: EmailVerificationAssessment,
) -> EmailQualificationDecision:
    """
    Apply Autlead's email qualification policy.

    The verification provider supplies technical evidence about
    syntax, DNS/MX, SMTP, domain type, and deliverability.

    This function determines whether Autlead accepts the email
    address for downstream use.

    Network uncertainty such as greylisting, SMTP blocking, or
    timeouts must not be treated as proof that an email is invalid.
    """

    confidence = max(
        0.0,
        min(assessment.score / 100, 1.0),
    )

    if not assessment.valid:
        return EmailQualificationDecision(
            is_qualified=False,
            status=assessment.status,
            confidence=confidence,
            reason="Verifier marked the email as invalid.",
        )

    if assessment.status == "undeliverable":
        return EmailQualificationDecision(
            is_qualified=False,
            status="undeliverable",
            confidence=confidence,
            reason="Email is proven undeliverable.",
        )

    if assessment.smtp_verdict == "undeliverable":
        return EmailQualificationDecision(
            is_qualified=False,
            status=assessment.status,
            confidence=confidence,
            reason="SMTP rejected the mailbox.",
        )

    if assessment.is_disposable:
        return EmailQualificationDecision(
            is_qualified=False,
            status=assessment.status,
            confidence=confidence,
            reason="Disposable email addresses are not qualified.",
        )

    if assessment.status == "deliverable":
        return EmailQualificationDecision(
            is_qualified=True,
            status="deliverable",
            confidence=confidence,
            reason=_deliverable_reason(
                assessment.smtp_verdict,
            ),
        )

    if assessment.status == "risky":
        return EmailQualificationDecision(
            is_qualified=False,
            status="risky",
            confidence=confidence,
            reason=_risky_reason(
                assessment.smtp_verdict,
            ),
        )

    return EmailQualificationDecision(
        is_qualified=False,
        status="unknown",
        confidence=confidence,
        reason=_unknown_reason(
            assessment.smtp_verdict,
        ),
    )


def _deliverable_reason(
    smtp_verdict: EmailSmtpVerdict,
) -> str:
    if smtp_verdict == "deliverable":
        return "Mailbox was accepted by SMTP."

    if smtp_verdict == "greylisted":
        return (
            "Email is deliverable, but the SMTP probe "
            "was temporarily greylisted."
        )

    if smtp_verdict == "catch_all":
        return (
            "Domain accepts mail, but the mailbox cannot "
            "be individually confirmed because it is catch-all."
        )

    if smtp_verdict == "blocked":
        return (
            "Email is deliverable based on available evidence; "
            "the SMTP probe was blocked."
        )

    if smtp_verdict == "timeout":
        return (
            "Email is deliverable based on available evidence; "
            "the SMTP probe timed out."
        )

    if smtp_verdict == "skipped":
        return (
            "Email is deliverable based on non-SMTP "
            "verification evidence."
        )

    return "Email passed deliverability qualification."


def _risky_reason(
    smtp_verdict: EmailSmtpVerdict,
) -> str:
    if smtp_verdict == "catch_all":
        return (
            "Catch-all domain prevents confirmation of the "
            "individual mailbox."
        )

    return "Verifier classified the email as risky."


def _unknown_reason(
    smtp_verdict: EmailSmtpVerdict,
) -> str:
    if smtp_verdict == "blocked":
        return (
            "SMTP verification was blocked; mailbox "
            "deliverability remains unknown."
        )

    if smtp_verdict == "timeout":
        return (
            "SMTP verification timed out; mailbox "
            "deliverability remains unknown."
        )

    if smtp_verdict == "greylisted":
        return (
            "SMTP server temporarily greylisted the probe; "
            "mailbox deliverability remains unconfirmed."
        )

    return "Verification evidence is insufficient."