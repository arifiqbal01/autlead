from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base


class WebsitePerformance(Base):
    __tablename__ = "website_performance"

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

    performance_score: Mapped[int | None] = mapped_column(Integer)

    first_contentful_paint_ms: Mapped[float | None] = mapped_column(Float)
    largest_contentful_paint_ms: Mapped[float | None] = mapped_column(Float)
    cumulative_layout_shift: Mapped[float | None] = mapped_column(Float)
    total_blocking_time_ms: Mapped[float | None] = mapped_column(Float)
    speed_index_ms: Mapped[float | None] = mapped_column(Float)

    seo_score: Mapped[int | None] = mapped_column(Integer)

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