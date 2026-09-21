# app/models/persistence/person_email_observation.py

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base


class PersonEmailObservation(Base):
    __tablename__ = "person_email_observations"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    person_id: Mapped[int] = mapped_column(
        ForeignKey(
            "people.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    company_id: Mapped[int] = mapped_column(
        ForeignKey(
            "companies.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    source_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "sources.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    provider_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
    )

    normalized_email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
        index=True,
    )

    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    verification_method: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    verification_result: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    pattern_inferred: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    source_urls: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    found_public_emails: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )