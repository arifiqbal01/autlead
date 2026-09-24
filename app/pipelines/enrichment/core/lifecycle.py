from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.state.pipeline.enrichment import (
    EnrichmentStage,
    get_stage_state,
    mark_stage_completed,
    mark_stage_failed,
    mark_stage_running,
)


logger = get_logger(__name__)


T = TypeVar("T")


async def stage_should_run(
    session: AsyncSession,
    *,
    company_id: int,
    company_name: str,
    stage: EnrichmentStage,
) -> bool:
    """
    Determine whether an enrichment stage should execute.

    A completed stage is skipped. Missing, failed, or otherwise
    incomplete stage state is eligible to run again.

    Rehydrating stages such as homepage and business pages may still
    load persisted data even when this function returns False.
    """

    state = await get_stage_state(
        session=session,
        company_id=company_id,
        stage=stage,
    )

    if state is None:
        return True

    if state.status == "completed":
        logger.info(
            "enrichment_stage_skipped",
            company_id=company_id,
            company_name=company_name,
            stage=stage.value,
            reason="already_completed",
        )

        return False

    return True


async def run_checkpointed_stage(
    session: AsyncSession,
    *,
    company_id: int,
    company_name: str,
    stage: EnrichmentStage,
    operation: Callable[[], Awaitable[T]],
) -> T | None:
    """
    Run one enrichment stage with persisted checkpoint state.

    Flow:

        inspect stage state
            ↓
        already completed → skip
            ↓
        mark running + commit
            ↓
        execute operation
            ↓
        success → mark completed + commit
        failure → rollback → mark failed + commit → re-raise

    Transaction behavior intentionally preserves the existing
    enrichment checkpoint semantics.
    """

    should_run = await stage_should_run(
        session,
        company_id=company_id,
        company_name=company_name,
        stage=stage,
    )

    if not should_run:
        return None

    await mark_stage_running(
        session,
        company_id=company_id,
        stage=stage,
    )

    await session.commit()

    logger.info(
        "enrichment_stage_started",
        company_id=company_id,
        company_name=company_name,
        stage=stage.value,
    )

    try:
        result = await operation()

        await mark_stage_completed(
            session,
            company_id=company_id,
            stage=stage,
        )

        await session.commit()

        logger.info(
            "enrichment_stage_completed",
            company_id=company_id,
            company_name=company_name,
            stage=stage.value,
        )

        return result

    except Exception as exc:
        await session.rollback()

        await mark_stage_failed(
            session,
            company_id=company_id,
            stage=stage,
            exc=exc,
        )

        await session.commit()

        logger.exception(
            "enrichment_stage_failed",
            company_id=company_id,
            company_name=company_name,
            stage=stage.value,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )

        raise