from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.persistence import Company
from app.models.persistence.website_crawl_state import WebsiteCrawlState
from app.state.transitions import (
    get_or_create_website_crawl_state,
    mark_website_crawl_completed,
    mark_website_crawl_failed,
    mark_website_crawl_started,
)
from app.state.transitions.website_crawl_status import WebsiteCrawlStatus


@pytest.mark.asyncio
async def test_get_or_create_website_crawl_state(
    session: AsyncSession,
    company: Company,
) -> None:
    state = await get_or_create_website_crawl_state(
        session=session,
        company_id=company.id,
    )

    assert state.id is not None
    assert state.company_id == company.id
    assert state.status == WebsiteCrawlStatus.PENDING.value
    assert state.attempt_count == 0


@pytest.mark.asyncio
async def test_get_or_create_returns_existing_state(
    session: AsyncSession,
    company: Company,
) -> None:
    first = await get_or_create_website_crawl_state(
        session=session,
        company_id=company.id,
    )

    second = await get_or_create_website_crawl_state(
        session=session,
        company_id=company.id,
    )

    assert second.id == first.id


@pytest.mark.asyncio
async def test_mark_website_crawl_started(
    session: AsyncSession,
    company: Company,
) -> None:
    state = await get_or_create_website_crawl_state(
        session=session,
        company_id=company.id,
    )

    await mark_website_crawl_started(
        session=session,
        state=state,
    )

    assert state.status == WebsiteCrawlStatus.RUNNING.value
    assert state.attempt_count == 1
    assert state.started_at is not None
    assert state.failed_at is None
    assert state.error_type is None
    assert state.error_message is None
    assert state.next_retry_at is None


@pytest.mark.asyncio
async def test_mark_website_crawl_completed(
    session: AsyncSession,
    company: Company,
) -> None:
    state = await get_or_create_website_crawl_state(
        session=session,
        company_id=company.id,
    )

    await mark_website_crawl_started(
        session=session,
        state=state,
    )

    await mark_website_crawl_completed(
        session=session,
        state=state,
        crawl_id=123,
    )

    assert state.status == WebsiteCrawlStatus.COMPLETED.value
    assert state.last_crawl_id == 123
    assert state.completed_at is not None
    assert state.failed_at is None
    assert state.error_type is None
    assert state.error_message is None
    assert state.next_retry_at is None


@pytest.mark.asyncio
async def test_mark_website_crawl_failed(
    session: AsyncSession,
    company: Company,
) -> None:
    state = await get_or_create_website_crawl_state(
        session=session,
        company_id=company.id,
    )

    await mark_website_crawl_started(
        session=session,
        state=state,
    )

    await mark_website_crawl_failed(
        session=session,
        state=state,
        error_type="ProviderTimeout",
        error_message="Crawl timed out.",
    )

    assert state.status == WebsiteCrawlStatus.FAILED.value
    assert state.failed_at is not None
    assert state.error_type == "ProviderTimeout"
    assert state.error_message == "Crawl timed out."
    assert state.next_retry_at is None


@pytest.mark.asyncio
async def test_mark_website_crawl_failed_with_retry(
    session: AsyncSession,
    company: Company,
) -> None:
    state = await get_or_create_website_crawl_state(
        session=session,
        company_id=company.id,
    )

    await mark_website_crawl_started(
        session=session,
        state=state,
    )

    retry_at = datetime.now(UTC)

    await mark_website_crawl_failed(
        session=session,
        state=state,
        error_type="ProviderTimeout",
        error_message="Crawl timed out.",
        next_retry_at=retry_at,
    )

    assert state.status == WebsiteCrawlStatus.RETRYING.value
    assert state.failed_at is not None
    assert state.error_type == "ProviderTimeout"
    assert state.error_message == "Crawl timed out."
    assert state.next_retry_at == retry_at