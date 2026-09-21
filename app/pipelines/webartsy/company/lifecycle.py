from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.state.pipeline.webartsy import (
    WebArtsyStage,
    mark_stage_completed,
    mark_stage_failed,
    mark_stage_running,
    should_run_stage,
)


logger = get_logger(__name__)

T = TypeVar("T")


async def stage_should_run(
    session: AsyncSession,
    *,
    company_id: int,
    company_name: str,
    stage: WebArtsyStage,
) -> bool:
    run_stage = await should_run_stage(
        session,
        company_id=company_id,
        stage=stage,
    )

    if not run_stage:
        logger.info(
            "webartsy_company_stage_skipped",
            company_id=company_id,
            company_name=company_name,
            stage=stage.value,
            reason="already_completed",
        )

    return run_stage


async def run_checkpointed_stage(
    session: AsyncSession,
    *,
    company_id: int,
    company_name: str,
    stage: WebArtsyStage,
    operation: Callable[[], Awaitable[T]],
) -> T | None:
    """
    Execute one resumable WebArtsy stage.

    Returns None when the stage was already completed.
    """

    if not await stage_should_run(
        session,
        company_id=company_id,
        company_name=company_name,
        stage=stage,
    ):
        return None

    await mark_stage_running(
        session,
        company_id=company_id,
        stage=stage,
    )

    await session.commit()

    logger.info(
        "webartsy_company_stage_started",
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
            "webartsy_company_stage_checkpointed",
            company_id=company_id,
            company_name=company_name,
            stage=stage.value,
            status="completed",
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

        logger.error(
            "webartsy_company_stage_failed",
            company_id=company_id,
            company_name=company_name,
            stage=stage.value,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )

        raise