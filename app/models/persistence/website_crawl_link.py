from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.persistence.website_crawl import WebsiteCrawl

class WebsiteCrawlLink(Base):
    __tablename__ = "website_crawl_links"

    __table_args__ = (
        UniqueConstraint(
            "website_crawl_id",
            "url",
            name="uq_website_crawl_links_crawl_url",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    website_crawl_id: Mapped[int] = mapped_column(
        ForeignKey("website_crawls.id"),
        nullable=False,
        index=True,
    )

    url: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    website_crawl: Mapped["WebsiteCrawl"] = relationship(
        back_populates="links",
    )