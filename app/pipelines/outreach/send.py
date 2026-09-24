from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.load.postgres.email_messages import (
    load_email_message,
)
from app.models.persistence.email_message import (
    EmailMessage,
)
from app.models.schemas.email_send import (
    EmailSendRequest,
)
from app.providers.email.sending.protocol import (
    EmailSendingProvider,
)


async def send_email(
    session: AsyncSession,
    *,
    provider: EmailSendingProvider,
    person_id: int,
    company_id: int,
    request: EmailSendRequest,
) -> EmailMessage:
    """
    Send one outreach through the configured provider and persist
    the resulting provider message identifier.

    The caller owns the database transaction.

    This operation intentionally does not commit the session.
    """

    result = await provider.send(
        request
    )

    message = await load_email_message(
        session,
        person_id=person_id,
        company_id=company_id,
        provider_name=result.provider_name,
        provider_message_id=(
            result.provider_message_id
        ),
        from_email=str(
            request.from_email
        ),
        to_email=str(
            request.to_email
        ),
        reply_to=(
            str(request.reply_to)
            if request.reply_to is not None
            else None
        ),
        subject=request.subject,
    )

    return message