from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base



class AcquisitionRun(Base):
    __tablename__ = "acquisition_runs"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    plan_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    segment: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    keyword: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    country_code: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
    )

    city: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )