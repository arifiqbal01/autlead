from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import asyncio
from app.core.database.session import SessionFactory
from app.core.logging import get_logger
from app.load.postgres.acquisition_runs import (
    complete_acquisition_run,
    fail_acquisition_run,
    find_completed_acquisition_run,
    start_acquisition_run,
)
from app.models.persistence import AcquisitionRun
from app.models.schemas import DiscoveryQuery
from app.models.schemas.acquisition_plan import (
    AcquisitionCity,
    AcquisitionPlan,
    AcquisitionPriority,
)
from app.pipelines.acquisition.pipeline import (
    run_acquisition_pipeline,
)
from app.providers.discovery.protocol import (
    BusinessDiscoveryProvider,
)


logger = get_logger(__name__)


DiscoveryProviderFactory = Callable[
    [AcquisitionCity],
    BusinessDiscoveryProvider,
]


@dataclass(frozen=True, slots=True)
class AcquisitionPlanResult:
    queries: int
    found: int
    new: int
    duplicates: int
    stored: int


_PRIORITY_ORDER = {
    AcquisitionPriority.HIGH: 0,
    AcquisitionPriority.MEDIUM: 1,
    AcquisitionPriority.LOW: 2,
}


async def run_acquisition_plan(
    *,
    plan: AcquisitionPlan,
    provider_factory: DiscoveryProviderFactory,
    limit: int | None = None,
) -> AcquisitionPlanResult:
    """
    Execute all discovery searches defined by an acquisition plan.

    Each keyword/city combination is an independent acquisition run.

    Completed queries are skipped using persisted acquisition-run state.

    Business acquisition and acquisition-run tracking use separate
    transactions. This ensures run state survives acquisition failures
    and allows interrupted plans to resume safely.
    """

    query_count = 0
    found = 0
    new = 0
    duplicates = 0
    stored = 0

    targets = sorted(
        plan.targets,
        key=lambda target: _PRIORITY_ORDER[target.priority],
    )

    logger.info(
        "acquisition_plan_started",
        plan=plan.name,
        country=plan.country.code,
        industry=plan.industry,
        targets=len(targets),
    )

    for target in targets:
        for city_key in target.cities:
            city = plan.cities[city_key]

            for keyword in target.keywords:
                completed = await _is_query_completed(
                    plan_name=plan.name,
                    segment=target.segment,
                    keyword=keyword,
                    country_code=plan.country.code,
                    city=city.name,
                )

                if completed:
                    logger.info(
                        "acquisition_plan_query_skipped",
                        plan=plan.name,
                        segment=target.segment,
                        priority=target.priority.value,
                        city=city.name,
                        query=keyword,
                        reason="already_completed",
                    )
                    continue

                provider = provider_factory(city)

                query = DiscoveryQuery(
                    query=keyword,
                    location=(
                        f"{city.name}, "
                        f"{plan.country.name}"
                    ),
                    limit=limit,
                )

                logger.info(
                    "acquisition_plan_query_started",
                    plan=plan.name,
                    segment=target.segment,
                    priority=target.priority.value,
                    city=city.name,
                    query=query.query,
                    location=query.location,
                    limit=query.limit,
                    grid_bbox=city.grid_bbox,
                    grid_cell_km=city.grid_cell_km,
                    zoom=city.zoom,
                )

                run_id = await _start_query_run(
                    plan_name=plan.name,
                    segment=target.segment,
                    keyword=keyword,
                    country_code=plan.country.code,
                    city=city.name,
                )

                try:
                    result = await run_acquisition_pipeline(
                        provider=provider,
                        query=query,
                    )

                except asyncio.CancelledError:
                    await _fail_query_run(
                        run_id=run_id,
                    )

                    logger.warning(
                        "acquisition_plan_query_cancelled",
                        plan=plan.name,
                        segment=target.segment,
                        priority=target.priority.value,
                        city=city.name,
                        query=query.query,
                        location=query.location,
                    )

                    raise

                except Exception:
                    await _fail_query_run(
                        run_id=run_id,
                    )

                    logger.exception(
                        "acquisition_plan_query_failed",
                        plan=plan.name,
                        segment=target.segment,
                        priority=target.priority.value,
                        city=city.name,
                        query=query.query,
                        location=query.location,
                    )

                    raise

                await _complete_query_run(
                    run_id=run_id,
                )

                query_count += 1
                found += result.found
                new += result.new
                duplicates += result.duplicates
                stored += result.stored

                logger.info(
                    "acquisition_plan_query_completed",
                    plan=plan.name,
                    segment=target.segment,
                    priority=target.priority.value,
                    city=city.name,
                    query=query.query,
                    location=query.location,
                    found=result.found,
                    new=result.new,
                    duplicates=result.duplicates,
                    stored=result.stored,
                )

    result = AcquisitionPlanResult(
        queries=query_count,
        found=found,
        new=new,
        duplicates=duplicates,
        stored=stored,
    )

    logger.info(
        "acquisition_plan_completed",
        plan=plan.name,
        queries=result.queries,
        found=result.found,
        new=result.new,
        duplicates=result.duplicates,
        stored=result.stored,
    )

    return result


async def _is_query_completed(
    *,
    plan_name: str,
    segment: str,
    keyword: str,
    country_code: str,
    city: str,
) -> bool:
    async with SessionFactory() as session:
        run = await find_completed_acquisition_run(
            session,
            plan_name=plan_name,
            segment=segment,
            keyword=keyword,
            country_code=country_code,
            city=city,
        )

        return run is not None


async def _start_query_run(
    *,
    plan_name: str,
    segment: str,
    keyword: str,
    country_code: str,
    city: str,
) -> int:
    async with SessionFactory() as session:
        try:
            run = await start_acquisition_run(
                session,
                plan_name=plan_name,
                segment=segment,
                keyword=keyword,
                country_code=country_code,
                city=city,
            )

            await session.commit()

            return run.id

        except Exception:
            await session.rollback()
            raise


async def _complete_query_run(
    *,
    run_id: int,
) -> None:
    async with SessionFactory() as session:
        run = await session.get(
            AcquisitionRun,
            run_id,
        )

        if run is None:
            raise RuntimeError(
                f"Acquisition run {run_id} does not exist."
            )

        try:
            await complete_acquisition_run(
                session,
                run,
            )

            await session.commit()

        except Exception:
            await session.rollback()
            raise


async def _fail_query_run(
    *,
    run_id: int,
) -> None:
    async with SessionFactory() as session:
        run = await session.get(
            AcquisitionRun,
            run_id,
        )

        if run is None:
            raise RuntimeError(
                f"Acquisition run {run_id} does not exist."
            )

        try:
            await fail_acquisition_run(
                session,
                run,
            )

            await session.commit()

        except Exception:
            await session.rollback()
            raise