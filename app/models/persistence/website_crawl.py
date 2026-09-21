# app/models/database/website_crawl_status.py

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.persistence.website_crawl_link import WebsiteCrawlLink

class WebsiteCrawl(Base):
    __tablename__ = "website_crawls"

    id: Mapped[int] = mapped_column(primary_key=True)

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id"),
        nullable=False,
        index=True,
    )

    url: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
    )

    status_code: Mapped[int | None] = mapped_column(
        Integer,
    )

    html: Mapped[str | None] = mapped_column(
        Text,
    )

    text: Mapped[str | None] = mapped_column(
        Text,
    )

    title: Mapped[str | None] = mapped_column(
        String(500),
    )

    meta_description: Mapped[str | None] = mapped_column(
        Text,
    )

    content_hash: Mapped[str | None] = mapped_column(
        String(64),
        index=True,
    )

    provider_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    links: Mapped[list["WebsiteCrawlLink"]] = relationship(
        back_populates="website_crawl",
        cascade="all, delete-orphan",
    )