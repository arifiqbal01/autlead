from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.persistence.acquisition_run import AcquisitionRun


async def find_completed_acquisition_run(
    session: AsyncSession,
    *,
    plan_name: str,
    segment: str,
    keyword: str,
    country_code: str,
    city: str,
) -> AcquisitionRun | None:
    return await session.scalar(
        select(AcquisitionRun).where(
            AcquisitionRun.plan_name == plan_name,
            AcquisitionRun.segment == segment,
            AcquisitionRun.keyword == keyword,
            AcquisitionRun.country_code == country_code,
            AcquisitionRun.city == city,
            AcquisitionRun.status == "completed",
        )
    )


async def start_acquisition_run(
    session: AsyncSession,
    *,
    plan_name: str,
    segment: str,
    keyword: str,
    country_code: str,
    city: str,
) -> AcquisitionRun:
    run = AcquisitionRun(
        plan_name=plan_name,
        segment=segment,
        keyword=keyword,
        country_code=country_code,
        city=city,
        status="running",
        started_at=datetime.now(UTC),
        completed_at=None,
    )

    session.add(run)
    await session.flush()

    return run


async def complete_acquisition_run(
    session: AsyncSession,
    run: AcquisitionRun,
) -> None:
    run.status = "completed"
    run.completed_at = datetime.now(UTC)

    await session.flush()


async def fail_acquisition_run(
    session: AsyncSession,
    run: AcquisitionRun,
) -> None:
    run.status = "failed"
    run.completed_at = datetime.now(UTC)

    await session.flush()