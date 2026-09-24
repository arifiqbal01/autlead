# app/pipelines/common/worker.py

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

from app.core.logging import get_logger


logger = get_logger(__name__)


T = TypeVar("T")
R = TypeVar("R")


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WorkerSuccess(Generic[T, R]):
    """
    Successful processing result for one queued item.
    """

    index: int
    item: T
    result: R
    attempts: int


@dataclass(frozen=True, slots=True)
class WorkerFailure(Generic[T]):
    """
    Failed processing result for one queued item.

    Failures are captured instead of terminating the complete worker pool.
    """

    index: int
    item: T
    attempts: int

    error_type: str
    error_message: str

    exception: Exception


@dataclass(frozen=True, slots=True)
class WorkerPoolResult(Generic[T, R]):
    """
    Result of processing a collection through the worker pool.
    """

    successes: tuple[WorkerSuccess[T, R], ...]
    failures: tuple[WorkerFailure[T], ...]

    @property
    def processed(self) -> int:
        return (
            len(self.successes)
            + len(self.failures)
        )

    @property
    def succeeded(self) -> int:
        return len(
            self.successes
        )

    @property
    def failed(self) -> int:
        return len(
            self.failures
        )

    @property
    def results(self) -> list[R]:
        """
        Return successful results in original input order.
        """

        return [
            success.result
            for success in sorted(
                self.successes,
                key=lambda item: item.index,
            )
        ]


# ---------------------------------------------------------------------------
# Internal queue item
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _QueueItem(Generic[T]):
    index: int
    item: T


# ---------------------------------------------------------------------------
# Retry policy
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WorkerRetryPolicy:
    """
    Retry policy for one worker item.

    retries:
        Number of retries AFTER the initial attempt.

        retries=0
            one attempt total

        retries=2
            up to three attempts total

    base_delay_seconds:
        Delay before the first retry.

    max_delay_seconds:
        Maximum retry delay.

    backoff_factor:
        Exponential backoff multiplier.
    """

    retries: int = 0

    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 10.0
    backoff_factor: float = 2.0

    def __post_init__(self) -> None:
        if self.retries < 0:
            raise ValueError(
                "retries must be >= 0"
            )

        if self.base_delay_seconds < 0:
            raise ValueError(
                "base_delay_seconds must be >= 0"
            )

        if self.max_delay_seconds < 0:
            raise ValueError(
                "max_delay_seconds must be >= 0"
            )

        if self.backoff_factor < 1:
            raise ValueError(
                "backoff_factor must be >= 1"
            )

    def retry_delay(
        self,
        retry_number: int,
    ) -> float:
        """
        Calculate delay before a retry.

        retry_number starts at 1.
        """

        delay = (
            self.base_delay_seconds
            * (
                self.backoff_factor
                ** (retry_number - 1)
            )
        )

        return min(
            delay,
            self.max_delay_seconds,
        )


# ---------------------------------------------------------------------------
# Public worker pool
# ---------------------------------------------------------------------------


async def run_worker_pool(
    *,
    items: Sequence[T],
    handler: Callable[[T], Awaitable[R]],
    worker_count: int,
    queue_size: int | None = None,
    retry_policy: WorkerRetryPolicy | None = None,
    should_retry: Callable[[Exception], bool] | None = None,
    item_name: Callable[[T], str] | None = None,
) -> WorkerPoolResult[T, R]:
    """
    Process items concurrently using a bounded asyncio worker pool.

    Important behavior:

        - bounded concurrency
        - item failures do not kill the pool
        - successful results preserve original input order
        - graceful cancellation
        - optional retries
        - progress logging
        - no external queue dependency

    The handler is responsible for its own resources.

    For database-backed work, the handler should create its own
    AsyncSession. Never share one AsyncSession across workers.

    Example:

        async def handler(company):
            async with SessionFactory() as session:
                return await process_company(
                    session=session,
                    company=company,
                )
    """

    if worker_count < 1:
        raise ValueError(
            "worker_count must be >= 1"
        )

    if not items:
        return WorkerPoolResult(
            successes=(),
            failures=(),
        )

    if queue_size is None:
        # Enough buffering to keep workers fed without creating
        # an unnecessarily large in-memory queue.
        queue_size = max(
            worker_count * 2,
            1,
        )

    if queue_size < 1:
        raise ValueError(
            "queue_size must be >= 1"
        )

    if retry_policy is None:
        retry_policy = WorkerRetryPolicy()

    if should_retry is None:
        should_retry = _never_retry

    if item_name is None:
        item_name = _default_item_name

    queue: asyncio.Queue[
        _QueueItem[T] | None
    ] = asyncio.Queue(
        maxsize=queue_size
    )

    successes: list[
        WorkerSuccess[T, R]
    ] = []

    failures: list[
        WorkerFailure[T]
    ] = []

    result_lock = asyncio.Lock()

    logger.info(
        "worker_pool_started",
        items=len(items),
        workers=worker_count,
        queue_size=queue_size,
        retries=retry_policy.retries,
    )

    # =========================================================
    # Producer
    # =========================================================

    async def producer() -> None:
        try:
            for index, item in enumerate(
                items
            ):
                await queue.put(
                    _QueueItem(
                        index=index,
                        item=item,
                    )
                )

        finally:
            # One sentinel per worker.
            for _ in range(
                worker_count
            ):
                await queue.put(
                    None
                )

    # =========================================================
    # Worker
    # =========================================================

    async def worker(
        worker_id: int,
    ) -> None:
        logger.debug(
            "worker_started",
            worker_id=worker_id,
        )

        while True:
            queue_item = await queue.get()

            try:
                # ---------------------------------------------
                # Sentinel
                # ---------------------------------------------

                if queue_item is None:
                    logger.debug(
                        "worker_stopping",
                        worker_id=worker_id,
                    )

                    return

                item = queue_item.item
                index = queue_item.index

                name = item_name(
                    item
                )

                logger.info(
                    "worker_item_started",
                    worker_id=worker_id,
                    item_index=index,
                    item=name,
                )

                outcome = await _run_item(
                    index=index,
                    item=item,
                    handler=handler,
                    retry_policy=retry_policy,
                    should_retry=should_retry,
                    worker_id=worker_id,
                    item_label=name,
                )

                async with result_lock:
                    if isinstance(
                        outcome,
                        WorkerSuccess,
                    ):
                        successes.append(
                            outcome
                        )

                        logger.info(
                            "worker_item_completed",
                            worker_id=worker_id,
                            item_index=index,
                            item=name,
                            attempts=outcome.attempts,
                        )

                    else:
                        failures.append(
                            outcome
                        )

                        logger.error(
                            "worker_item_failed",
                            worker_id=worker_id,
                            item_index=index,
                            item=name,
                            attempts=outcome.attempts,
                            error_type=outcome.error_type,
                            error_message=(
                                outcome.error_message
                            ),
                        )

            except asyncio.CancelledError:
                logger.warning(
                    "worker_cancelled",
                    worker_id=worker_id,
                )

                raise

            finally:
                queue.task_done()

    # =========================================================
    # Run
    # =========================================================

    try:
        async with asyncio.TaskGroup() as task_group:
            task_group.create_task(
                producer()
            )

            for worker_id in range(
                1,
                worker_count + 1,
            ):
                task_group.create_task(
                    worker(
                        worker_id
                    )
                )

    except asyncio.CancelledError:
        logger.warning(
            "worker_pool_cancelled",
            items=len(items),
            successes=len(successes),
            failures=len(failures),
        )

        raise

    # =========================================================
    # Result
    # =========================================================

    ordered_successes = tuple(
        sorted(
            successes,
            key=lambda item: item.index,
        )
    )

    ordered_failures = tuple(
        sorted(
            failures,
            key=lambda item: item.index,
        )
    )

    result = WorkerPoolResult(
        successes=ordered_successes,
        failures=ordered_failures,
    )

    logger.info(
        "worker_pool_completed",
        items=len(items),
        processed=result.processed,
        succeeded=result.succeeded,
        failed=result.failed,
        workers=worker_count,
    )

    return result


# ---------------------------------------------------------------------------
# Item execution
# ---------------------------------------------------------------------------


async def _run_item(
    *,
    index: int,
    item: T,
    handler: Callable[[T], Awaitable[R]],
    retry_policy: WorkerRetryPolicy,
    should_retry: Callable[[Exception], bool],
    worker_id: int,
    item_label: str,
) -> WorkerSuccess[T, R] | WorkerFailure[T]:
    """
    Execute one queue item with bounded retries.
    """

    max_attempts = (
        retry_policy.retries
        + 1
    )

    for attempt in range(
        1,
        max_attempts + 1,
    ):
        try:
            result = await handler(
                item
            )

            return WorkerSuccess(
                index=index,
                item=item,
                result=result,
                attempts=attempt,
            )

        except asyncio.CancelledError:
            raise

        except Exception as exc:
            retry_allowed = (
                attempt < max_attempts
                and should_retry(exc)
            )

            if not retry_allowed:
                return WorkerFailure(
                    index=index,
                    item=item,
                    attempts=attempt,
                    error_type=(
                        type(exc).__name__
                    ),
                    error_message=str(
                        exc
                    ),
                    exception=exc,
                )

            retry_number = attempt

            delay = (
                retry_policy.retry_delay(
                    retry_number
                )
            )

            logger.warning(
                "worker_item_retry",
                worker_id=worker_id,
                item_index=index,
                item=item_label,
                attempt=attempt,
                next_attempt=attempt + 1,
                delay_seconds=delay,
                error_type=(
                    type(exc).__name__
                ),
                error_message=str(
                    exc
                ),
            )

            await asyncio.sleep(
                delay
            )

    # Defensive fallback. The loop always returns above.
    raise RuntimeError(
        "Worker item execution ended unexpectedly"
    )


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------


def _never_retry(
    _exc: Exception,
) -> bool:
    return False


def _default_item_name(
    item: T,
) -> str:
    return str(
        item
    )