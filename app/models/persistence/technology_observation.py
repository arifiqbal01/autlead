from datetime import datetime

from sqlalchemy import DateTime, Integer, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base


class TechnologyObservation(Base):
    __tablename__ = "technology_observations"

    id: Mapped[int] = mapped_column(primary_key=True)

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    provider_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    version: Mapped[str | None] = mapped_column(
        String(100),
    )

    confidence: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    categories: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    groups: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
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