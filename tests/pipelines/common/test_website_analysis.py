from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.models.schemas.crawling import WebsiteContent
from app.pipelines.common import website_crawl


def make_content(
    *,
    url: str = "https://example.com",
) -> WebsiteContent:
    return WebsiteContent(
        url=url,
        status_code=200,
        html="<html></html>",
        text="Example",
        title="Example",
        meta_description="Example website",
        links=["https://example.com/about"],
        collected_at=datetime.now(UTC),
    )


def make_state(
    *,
    last_crawl_id: int | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        company_id=1,
        last_crawl_id=last_crawl_id,
    )


def make_crawl(
    *,
    crawl_id: int = 1,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=crawl_id,
        url="https://example.com",
        status_code=200,
        html="<html></html>",
        text="Example",
        title="Example",
        meta_description="Example website",
        collected_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_no_previous_crawl_crawls_and_persists(
    monkeypatch,
):
    session = SimpleNamespace(
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )

    provider = SimpleNamespace(
        provider_name="crawl4ai",
        crawl=AsyncMock(return_value=make_content()),
    )

    state = make_state()
    crawl = make_crawl()

    get_state = AsyncMock(return_value=state)
    get_last_crawl = AsyncMock(return_value=None)
    load_crawl = AsyncMock(return_value=crawl)
    mark_started = AsyncMock()
    mark_completed = AsyncMock()

    monkeypatch.setattr(
        website_analysis,
        "get_or_create_website_crawl_state",
        get_state,
    )
    monkeypatch.setattr(
        website_analysis,
        "get_last_website_crawl",
        get_last_crawl,
    )
    monkeypatch.setattr(
        website_analysis,
        "load_website_crawl",
        load_crawl,
    )
    monkeypatch.setattr(
        website_analysis,
        "mark_website_crawl_started",
        mark_started,
    )
    monkeypatch.setattr(
        website_analysis,
        "mark_website_crawl_completed",
        mark_completed,
    )

    result = await website_analysis.analyze_website(
        session,
        company_id=1,
        website="https://example.com",
        provider=provider,
        retention_days=30,
    )

    assert result.crawled is True
    assert str(result.content.url) == "https://example.com/"

    get_state.assert_awaited_once_with(
        session=session,
        company_id=1,
    )

    get_last_crawl.assert_awaited_once_with(
        session=session,
        last_crawl_id=None,
    )

    mark_started.assert_awaited_once_with(
        session=session,
        state=state,
    )

    provider.crawl.assert_awaited_once()

    load_crawl.assert_awaited_once_with(
        session=session,
        content=result.content,
        company_id=1,
        provider_name="crawl4ai",
    )

    mark_completed.assert_awaited_once_with(
        session=session,
        state=state,
        crawl_id=crawl.id,
    )

    assert session.commit.await_count == 2
    session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_fresh_crawl_is_reused_without_crawling(
    monkeypatch,
):
    session = SimpleNamespace(
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )

    provider = SimpleNamespace(
        provider_name="crawl4ai",
        crawl=AsyncMock(),
    )

    state = make_state(last_crawl_id=10)
    crawl = make_crawl(crawl_id=10)
    content = make_content()

    get_state = AsyncMock(return_value=state)
    get_last_crawl = AsyncMock(return_value=crawl)
    get_content = AsyncMock(return_value=content)

    monkeypatch.setattr(
        website_analysis,
        "get_or_create_website_crawl_state",
        get_state,
    )
    monkeypatch.setattr(
        website_analysis,
        "get_last_website_crawl",
        get_last_crawl,
    )
    monkeypatch.setattr(
        website_analysis,
        "get_website_crawl_content",
        get_content,
    )
    monkeypatch.setattr(
        website_analysis,
        "should_recrawl_website",
        lambda *args, **kwargs: False,
    )

    result = await website_analysis.analyze_website(
        session,
        company_id=1,
        website="https://example.com",
        provider=provider,
        retention_days=30,
    )

    assert result.crawled is False
    assert result.content is content

    provider.crawl.assert_not_awaited()
    get_content.assert_awaited_once_with(
        session=session,
        crawl=crawl,
    )

    session.commit.assert_not_awaited()
    session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_stale_crawl_triggers_new_crawl(
    monkeypatch,
):
    session = SimpleNamespace(
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )

    provider = SimpleNamespace(
        provider_name="crawl4ai",
        crawl=AsyncMock(return_value=make_content()),
    )

    state = make_state(last_crawl_id=10)
    existing_crawl = make_crawl(crawl_id=10)
    new_crawl = make_crawl(crawl_id=11)

    get_state = AsyncMock(return_value=state)
    get_last_crawl = AsyncMock(return_value=existing_crawl)
    load_crawl = AsyncMock(return_value=new_crawl)
    mark_started = AsyncMock()
    mark_completed = AsyncMock()

    monkeypatch.setattr(
        website_analysis,
        "get_or_create_website_crawl_state",
        get_state,
    )
    monkeypatch.setattr(
        website_analysis,
        "get_last_website_crawl",
        get_last_crawl,
    )
    monkeypatch.setattr(
        website_analysis,
        "should_recrawl_website",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(
        website_analysis,
        "load_website_crawl",
        load_crawl,
    )
    monkeypatch.setattr(
        website_analysis,
        "mark_website_crawl_started",
        mark_started,
    )
    monkeypatch.setattr(
        website_analysis,
        "mark_website_crawl_completed",
        mark_completed,
    )

    result = await website_analysis.analyze_website(
        session,
        company_id=1,
        website="https://example.com",
        provider=provider,
        retention_days=30,
    )

    assert result.crawled is True

    provider.crawl.assert_awaited_once()
    load_crawl.assert_awaited_once()
    mark_started.assert_awaited_once()
    mark_completed.assert_awaited_once_with(
        session=session,
        state=state,
        crawl_id=new_crawl.id,
    )

    assert session.commit.await_count == 2


@pytest.mark.asyncio
async def test_provider_failure_marks_crawl_failed(
    monkeypatch,
):
    session = SimpleNamespace(
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )

    provider_error = RuntimeError("crawler unavailable")

    provider = SimpleNamespace(
        provider_name="crawl4ai",
        crawl=AsyncMock(side_effect=provider_error),
    )

    state = make_state()

    get_state = AsyncMock(return_value=state)
    get_last_crawl = AsyncMock(return_value=None)
    mark_started = AsyncMock()
    mark_failed = AsyncMock()

    monkeypatch.setattr(
        website_analysis,
        "get_or_create_website_crawl_state",
        get_state,
    )
    monkeypatch.setattr(
        website_analysis,
        "get_last_website_crawl",
        get_last_crawl,
    )
    monkeypatch.setattr(
        website_analysis,
        "mark_website_crawl_started",
        mark_started,
    )
    monkeypatch.setattr(
        website_analysis,
        "mark_website_crawl_failed",
        mark_failed,
    )

    with pytest.raises(RuntimeError, match="crawler unavailable"):
        await website_analysis.analyze_website(
            session,
            company_id=1,
            website="https://example.com",
            provider=provider,
            retention_days=30,
        )

    provider.crawl.assert_awaited_once()

    session.rollback.assert_awaited_once()

    mark_failed.assert_awaited_once_with(
        session=session,
        state=state,
        error_type="RuntimeError",
        error_message="crawler unavailable",
    )

    assert session.commit.await_count == 2


@pytest.mark.asyncio
async def test_persistence_failure_marks_crawl_failed(
    monkeypatch,
):
    session = SimpleNamespace(
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )

    provider = SimpleNamespace(
        provider_name="crawl4ai",
        crawl=AsyncMock(return_value=make_content()),
    )

    state = make_state()

    persistence_error = RuntimeError("database unavailable")

    get_state = AsyncMock(return_value=state)
    get_last_crawl = AsyncMock(return_value=None)
    load_crawl = AsyncMock(side_effect=persistence_error)
    mark_started = AsyncMock()
    mark_failed = AsyncMock()

    monkeypatch.setattr(
        website_analysis,
        "get_or_create_website_crawl_state",
        get_state,
    )
    monkeypatch.setattr(
        website_analysis,
        "get_last_website_crawl",
        get_last_crawl,
    )
    monkeypatch.setattr(
        website_analysis,
        "load_website_crawl",
        load_crawl,
    )
    monkeypatch.setattr(
        website_analysis,
        "mark_website_crawl_started",
        mark_started,
    )
    monkeypatch.setattr(
        website_analysis,
        "mark_website_crawl_failed",
        mark_failed,
    )

    with pytest.raises(RuntimeError, match="database unavailable"):
        await website_analysis.analyze_website(
            session,
            company_id=1,
            website="https://example.com",
            provider=provider,
            retention_days=30,
        )

    provider.crawl.assert_awaited_once()
    load_crawl.assert_awaited_once()

    session.rollback.assert_awaited_once()

    mark_failed.assert_awaited_once_with(
        session=session,
        state=state,
        error_type="RuntimeError",
        error_message="database unavailable",
    )

    assert session.commit.await_count == 2