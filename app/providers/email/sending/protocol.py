from __future__ import annotations

from typing import Protocol

from app.models.schemas.email_send import EmailSendRequest, EmailSendResult


class EmailSendingProvider(Protocol):
    async def send(
        self,
        request: EmailSendRequest,
    ) -> EmailSendResult:
        """Send one outreach and return the provider result."""
        ...