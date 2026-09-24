# app/providers/outreach/verification/models.py

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


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

SmtpVerdict = Literal[
    "deliverable",
    "undeliverable",
    "catch_all",
    "greylisted",
    "blocked",
    "timeout",
    "skipped",
    "unknown",
]



class EmailVerificationRequest(BaseModel):
    email: str = Field(
        min_length=3,
    )


class EmailSmtpResult(BaseModel):
    verdict: SmtpVerdict
    code: int | None = None
    message: str | None = None
    catch_all: bool = False
    latency_ms: int | None = None


class EmailVerificationResult(BaseModel):
    email: str | None = None
    canonical: str | None = None

    status: EmailVerificationStatus
    valid: bool

    score: int = Field(
        ge=0,
        le=100,
    )

    risk: EmailVerificationRisk

    reasons: list[str] = Field(
        default_factory=list,
    )

    smtp: EmailSmtpResult

    provider: str