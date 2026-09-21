from datetime import UTC, datetime, timedelta

from app.policies.retention.website_crawl import (
    WebsiteCrawlRetentionContext,
    should_recrawl_website,
)


def test_should_recrawl_when_no_previous_crawl() -> None:
    context = WebsiteCrawlRetentionContext(
        collected_at=None,
        max_age=timedelta(days=7),
    )

    assert should_recrawl_website(context) is True


def test_should_not_recrawl_fresh_crawl() -> None:
    now = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)

    context = WebsiteCrawlRetentionContext(
        collected_at=now - timedelta(days=2),
        max_age=timedelta(days=7),
    )

    assert should_recrawl_website(
        context,
        now=now,
    ) is False


def test_should_recrawl_stale_crawl() -> None:
    now = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)

    context = WebsiteCrawlRetentionContext(
        collected_at=now - timedelta(days=8),
        max_age=timedelta(days=7),
    )

    assert should_recrawl_website(
        context,
        now=now,
    ) is True


def test_should_recrawl_at_exact_age_boundary() -> None:
    now = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)

    context = WebsiteCrawlRetentionContext(
        collected_at=now - timedelta(days=7),
        max_age=timedelta(days=7),
    )

    assert should_recrawl_website(
        context,
        now=now,
    ) is True