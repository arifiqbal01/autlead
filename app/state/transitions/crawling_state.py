from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.persistence.website_crawl_state import WebsiteCrawlState
from .website_crawl_status import WebsiteCrawlStatus, can_transition


def _transition(
    state: WebsiteCrawlState,
    new_status: WebsiteCrawlStatus,
) -> None:
    current_status = WebsiteCrawlStatus(state.status)

    if not can_transition(current_status, new_status):
        raise ValueError(
            f"Invalid website crawl state transition: "
            f"{current_status} -> {new_status}"
        )

    state.status = new_status.value


async def get_or_create_website_crawl_state(
    session: AsyncSession,
    company_id: int,
) -> WebsiteCrawlState:
    state = await session.scalar(
        select(WebsiteCrawlState).where(
            WebsiteCrawlState.company_id == company_id,
        )
    )

    if state is not None:
        return state

    state = WebsiteCrawlState(
        company_id=company_id,
        status=WebsiteCrawlStatus.PENDING.value,
    )

    session.add(state)
    await session.flush()

    return state


async def mark_website_crawl_started(
    session: AsyncSession,
    state: WebsiteCrawlState,
) -> None:
    now = datetime.now(UTC)

    _transition(
        state,
        WebsiteCrawlStatus.RUNNING,
    )

    state.attempt_count += 1
    state.started_at = now
    state.failed_at = None
    state.error_type = None
    state.error_message = None
    state.next_retry_at = None


async def mark_website_crawl_completed(
    session: AsyncSession,
    state: WebsiteCrawlState,
    crawl_id: int,
) -> None:
    _transition(
        state,
        WebsiteCrawlStatus.COMPLETED,
    )

    state.last_crawl_id = crawl_id
    state.completed_at = datetime.now(UTC)
    state.failed_at = None
    state.error_type = None
    state.error_message = None
    state.next_retry_at = None


async def mark_website_crawl_failed(
    session: AsyncSession,
    state: WebsiteCrawlState,
    *,
    error_type: str,
    error_message: str,
    next_retry_at: datetime | None = None,
) -> None:
    new_status = (
        WebsiteCrawlStatus.RETRYING
        if next_retry_at is not None
        else WebsiteCrawlStatus.FAILED
    )

    _transition(state, new_status)

    state.failed_at = datetime.now(UTC)
    state.error_type = error_type
    state.error_message = error_message
    state.next_retry_at = next_retry_at