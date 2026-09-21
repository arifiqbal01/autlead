from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class WebsiteCrawlRetentionContext:
    """Context used to determine whether existing crawl data can be reused."""

    collected_at: datetime | None
    max_age: timedelta


def should_recrawl_website(
    context: WebsiteCrawlRetentionContext,
    *,
    now: datetime | None = None,
) -> bool:
    """Return whether existing website crawl data should be refreshed."""

    if context.collected_at is None:
        return True

    current_time = now or datetime.now(UTC)

    collected_at = context.collected_at

    if collected_at.tzinfo is None:
        collected_at = collected_at.replace(tzinfo=UTC)

    return current_time - collected_at >= context.max_age