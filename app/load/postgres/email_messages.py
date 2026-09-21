from __future__ import annotations

from datetime import datetime
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.persistence.email_message import (
    EmailMessage,
)


async def load_email_message(
    session: AsyncSession,
    *,
    person_id: int,
    company_id: int,
    provider_name: str,
    provider_message_id: str,
    from_email: str,
    to_email: str,
    subject: str,
    reply_to: str | None = None,
    sent_at: datetime | None = None,
) -> EmailMessage:
    now = datetime.now().astimezone()

    if sent_at is None:
        sent_at = now

    message = EmailMessage(
        person_id=person_id,
        company_id=company_id,
        provider_name=provider_name,
        provider_message_id=provider_message_id,
        from_email=from_email,
        to_email=to_email,
        reply_to=reply_to,
        subject=subject,
        sent_at=sent_at,
        created_at=now,
    )

    session.add(message)
    await session.flush()

    return message


async def email_was_already_sent(
    session: AsyncSession,
    *,
    email: str,
) -> bool:
    statement = select(
        exists().where(
            EmailMessage.to_email == email
        )
    )

    result = await session.scalar(statement)

    return bool(result)