# app/pipelines/enrichment/stage_state.py

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.persistence.webartsy_stage_state import (
    WebArtsyStageState,
)
from .stages import (
    EnrichmentStage,
)
from .status import (
    EnrichmentStageStatus,
)


async def get_stage_state(
    session: AsyncSession,
    *,
    company_id: int,
    stage: EnrichmentStage,
) -> WebArtsyStageState | None:
    return await session.scalar(
        select(WebArtsyStageState).where(
            WebArtsyStageState.company_id == company_id,
            WebArtsyStageState.stage == stage.value,
        )
    )


async def should_run_stage(
    session: AsyncSession,
    *,
    company_id: int,
    stage: EnrichmentStage,
) -> bool:
    state = await get_stage_state(
        session,
        company_id=company_id,
        stage=stage,
    )

    if state is None:
        return True

    return state.status != EnrichmentStageStatus.COMPLETED.value


async def mark_stage_running(
    session: AsyncSession,
    *,
    company_id: int,
    stage: EnrichmentStage,
) -> WebArtsyStageState:
    state = await get_stage_state(
        session,
        company_id=company_id,
        stage=stage,
    )

    now = datetime.now(UTC)

    if state is None:
        state = WebArtsyStageState(
            company_id=company_id,
            stage=stage.value,
            status=EnrichmentStageStatus.RUNNING.value,
            attempts=1,
            started_at=now,
            updated_at=now,
        )

        session.add(state)

    else:
        state.status = EnrichmentStageStatus.RUNNING.value
        state.attempts += 1
        state.started_at = now
        state.error_type = None
        state.error_message = None
        state.updated_at = now

    await session.flush()

    return state


async def mark_stage_completed(
    session: AsyncSession,
    *,
    company_id: int,
    stage: EnrichmentStage,
) -> None:
    state = await get_stage_state(
        session,
        company_id=company_id,
        stage=stage,
    )

    if state is None:
        raise RuntimeError(
            f"Missing stage state for {company_id}:{stage}"
        )

    now = datetime.now(UTC)

    state.status = EnrichmentStageStatus.COMPLETED.value
    state.completed_at = now
    state.updated_at = now

    await session.flush()


async def mark_stage_failed(
    session: AsyncSession,
    *,
    company_id: int,
    stage: EnrichmentStage,
    exc: Exception,
) -> None:
    state = await get_stage_state(
        session,
        company_id=company_id,
        stage=stage,
    )

    if state is None:
        raise RuntimeError(
            f"Missing stage state for {company_id}:{stage}"
        )

    state.status = EnrichmentStageStatus.FAILED.value
    state.error_type = type(exc).__name__
    state.error_message = str(exc)
    state.updated_at = datetime.now(UTC)

    await session.flush()