from __future__ import annotations

from typing import Protocol

from app.providers.email.verification.models import (
    EmailVerificationRequest,
    EmailVerificationResult,
)


class EmailVerificationProvider(Protocol):
    async def verify(
        self,
        request: EmailVerificationRequest,
    ) -> EmailVerificationResult:
        """Verify a known email address."""
        ...