from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base


class EmailMessage(Base):
    __tablename__ = "email_messages"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    person_id: Mapped[int] = mapped_column(
        ForeignKey("people.id"),
        nullable=False,
        index=True,
    )

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id"),
        nullable=False,
        index=True,
    )

    provider_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    provider_message_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )

    from_email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
    )

    to_email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
    )

    reply_to: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
    )

    subject: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )