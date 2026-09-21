# app/providers/discovery/gosom.py

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.logging import get_logger
from app.models.schemas import BusinessRecord, DiscoveryQuery
from app.providers.discovery.exceptions import (
    BusinessDiscoveryProviderError,
)
from app.providers.discovery.gosom_csv import (
    CSV_READ_ERRORS,
    count_results,
    read_results,
)
from app.providers.discovery.gosom_utils import (
    deduplicate,
    extract_domain,
    extract_external_id,
    optional_text,
    parse_location,
    required_text,
)


logger = get_logger(__name__)


class GosomGoogleMapsDiscoveryProvider:
    """
    Google Maps business discovery using Gosom's scraper.

    Raw discovery runs are persisted on disk.

    Example:

        data/discovery/gosom/
            20260822_092200_accountantskantoor_amsterdam-nederland/
                queries.txt
                results.csv

    This preserves partial Gosom results when a run:

        - completes
        - times out
        - is cancelled
        - is interrupted

    Gosom owns scraping concurrency internally.

    `query.limit` is an optional Autlead-side cap applied after
    Gosom discovery and provider-level deduplication.
    """

    source_name = "Google Maps"
    source_type = "business_discovery"
    provider_name = "gosom_google_maps"

    def __init__(
        self,
        *,
        results_root: str | Path = "data/discovery/gosom",
        image: str = "gosom/google-maps-scraper",
        concurrency: int = 4,
        depth: int = 5,
        zoom: int = 16,
        grid_bbox: str | None = None,
        grid_cell_km: float = 1.0,
        proxy: str | None = None,
        docker_command: str = "docker",
        timeout_seconds: int = 1800,
        pages_per_browser: int = 4,
        browser_pool_size: int = 1,
        exit_on_inactivity: str = "3m",
        playwright_cache_volume: str = (
            "autlead-gmaps-playwright-cache"
        ),
        progress_interval_seconds: float = 2.0,
        final_read_attempts: int = 3,
        final_read_delay_seconds: float = 0.5,
    ) -> None:
        if concurrency < 1:
            raise ValueError(
                "concurrency must be >= 1"
            )

        if depth < 1:
            raise ValueError(
                "depth must be >= 1"
            )

        if not 1 <= zoom <= 21:
            raise ValueError(
                "zoom must be between 1 and 21"
            )

        if grid_cell_km <= 0:
            raise ValueError(
                "grid_cell_km must be > 0"
            )

        if timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds must be > 0"
            )

        if pages_per_browser < 1:
            raise ValueError(
                "pages_per_browser must be >= 1"
            )

        if browser_pool_size < 0:
            raise ValueError(
                "browser_pool_size must be >= 0"
            )

        if progress_interval_seconds <= 0:
            raise ValueError(
                "progress_interval_seconds must be > 0"
            )

        if final_read_attempts < 1:
            raise ValueError(
                "final_read_attempts must be >= 1"
            )

        if final_read_delay_seconds < 0:
            raise ValueError(
                "final_read_delay_seconds must be >= 0"
            )

        self.results_root = (
            Path(results_root)
            .expanduser()
            .resolve()
        )

        self.image = image
        self.concurrency = concurrency
        self.depth = depth
        self.zoom = zoom
        self.grid_bbox = grid_bbox
        self.grid_cell_km = grid_cell_km
        self.proxy = proxy
        self.docker_command = docker_command
        self.timeout_seconds = timeout_seconds
        self.pages_per_browser = pages_per_browser
        self.browser_pool_size = browser_pool_size
        self.exit_on_inactivity = exit_on_inactivity
        self.playwright_cache_volume = (
            playwright_cache_volume
        )
        self.progress_interval_seconds = (
            progress_interval_seconds
        )
        self.final_read_attempts = (
            final_read_attempts
        )
        self.final_read_delay_seconds = (
            final_read_delay_seconds
        )

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    async def discover(
        self,
        query: DiscoveryQuery,
    ) -> list[BusinessRecord]:
        """
        Run one persistent Gosom discovery job.

        A timeout or non-zero process exit may still become partial success
        when the persistent results.csv contains usable rows.
        """

        area = required_text(
            query.location,
            "location",
        )

        work_dir = (
            self._create_run_directory(
                query=query,
            )
            .resolve()
        )

        queries_file = (
            work_dir
            / "queries.txt"
        ).resolve()

        results_file = (
            work_dir
            / "results.csv"
        ).resolve()

        queries_file.write_text(
            f"{query.query} in {area}\n",
            encoding="utf-8",
        )

        logger.info(
            "gosom_discovery_run_created",
            run_dir=str(
                work_dir
            ),
            run_dir_absolute=(
                work_dir.is_absolute()
            ),
            queries_file=str(
                queries_file
            ),
            queries_file_absolute=(
                queries_file.is_absolute()
            ),
            results_file=str(
                results_file
            ),
            results_file_absolute=(
                results_file.is_absolute()
            ),
            query=query.query,
            location=query.location,
        )

        command = self._build_command(
            queries_file=queries_file,
            results_file=results_file,
        )

        process_failure: Exception | None = None
        timed_out = False

        try:
            await self._run(
                command,
                cwd=work_dir,
                results_file=results_file,
            )

        except asyncio.CancelledError:
            discovered = count_results(
                results_file
            )

            logger.warning(
                "gosom_discovery_cancelled",
                run_dir=str(
                    work_dir
                ),
                results_file=str(
                    results_file
                ),
                results_exists=(
                    results_file.exists()
                ),
                results_size=(
                    self._file_size(
                        results_file
                    )
                ),
                discovered=discovered,
            )

            raise

        except asyncio.TimeoutError as exc:
            process_failure = exc
            timed_out = True

        except OSError as exc:
            logger.exception(
                "gosom_discovery_start_failed",
                run_dir=str(
                    work_dir
                ),
                results_file=str(
                    results_file
                ),
                results_exists=(
                    results_file.exists()
                ),
                results_size=(
                    self._file_size(
                        results_file
                    )
                ),
            )

            raise BusinessDiscoveryProviderError(
                "Could not start Gosom Google Maps scraper"
            ) from exc

        except RuntimeError as exc:
            process_failure = exc

        # =========================================================
        # Authoritative final / recovery CSV read
        # =========================================================

        try:
            businesses = await self._read_final_results(
                results_file
            )

        except FileNotFoundError as exc:
            if process_failure is not None:
                raise BusinessDiscoveryProviderError(
                    "Gosom failed without producing a results file"
                ) from process_failure

            raise BusinessDiscoveryProviderError(
                "Gosom did not produce a results file"
            ) from exc

        except CSV_READ_ERRORS as exc:
            logger.exception(
                "gosom_results_final_read_failed",
                run_dir=str(
                    work_dir
                ),
                results_file=str(
                    results_file
                ),
                results_exists=(
                    results_file.exists()
                ),
                results_size=(
                    self._file_size(
                        results_file
                    )
                ),
                process_error_type=(
                    type(
                        process_failure
                    ).__name__
                    if process_failure
                    else None
                ),
                process_error_message=(
                    str(
                        process_failure
                    )
                    if process_failure
                    else None
                ),
            )

            raise BusinessDiscoveryProviderError(
                "Could not read Gosom results file"
            ) from exc

        raw_count = len(
            businesses
        )

        # =========================================================
        # Decide success versus failed empty run
        # =========================================================

        if raw_count == 0:
            if process_failure is not None:
                if timed_out:
                    raise BusinessDiscoveryProviderError(
                        "Google Maps discovery timed out "
                        "before producing usable results"
                    ) from process_failure

                raise BusinessDiscoveryProviderError(
                    "Gosom Google Maps discovery failed "
                    "without producing usable results"
                ) from process_failure

            raise BusinessDiscoveryProviderError(
                "Gosom results file contains no usable records"
            )

        if process_failure is not None:
            event = (
                "gosom_discovery_partial_timeout"
                if timed_out
                else "gosom_discovery_partial_failure"
            )

            logger.warning(
                event,
                run_dir=str(
                    work_dir
                ),
                results_file=str(
                    results_file
                ),
                results_exists=(
                    results_file.exists()
                ),
                results_size=(
                    self._file_size(
                        results_file
                    )
                ),
                discovered=raw_count,
                error_type=type(
                    process_failure
                ).__name__,
                error_message=str(
                    process_failure
                ),
            )

        logger.info(
            "gosom_discovery_results_available",
            raw=raw_count,
            run_dir=str(
                work_dir
            ),
            results_file=str(
                results_file
            ),
            results_size=(
                self._file_size(
                    results_file
                )
            ),
        )

        # =========================================================
        # Provider-level identity diagnostics
        # =========================================================

        unique_external_ids = {
            external_id
            for business in businesses
            if (
                external_id := extract_external_id(
                    business
                )
            )
        }

        logger.info(
            "gosom_identity_diagnostics",
            raw=raw_count,
            place_ids=sum(
                1
                for business in businesses
                if optional_text(
                    business.get(
                        "place_id"
                    )
                )
            ),
            cids=sum(
                1
                for business in businesses
                if optional_text(
                    business.get(
                        "cid"
                    )
                )
            ),
            data_ids=sum(
                1
                for business in businesses
                if optional_text(
                    business.get(
                        "data_id"
                    )
                )
            ),
            unique_external_ids=len(
                unique_external_ids
            ),
            records_without_external_id=sum(
                1
                for business in businesses
                if extract_external_id(
                    business
                )
                is None
            ),
            results_file=str(
                results_file
            ),
        )

        # =========================================================
        # Provider-level deduplication
        # =========================================================

        businesses = deduplicate(
            businesses
        )

        deduplicated_count = len(
            businesses
        )

        logger.info(
            "gosom_results_loaded",
            raw=raw_count,
            deduplicated=deduplicated_count,
            duplicates_removed=(
                raw_count
                - deduplicated_count
            ),
            results_file=str(
                results_file
            ),
        )

        # =========================================================
        # Optional Autlead-side result cap
        # =========================================================

        limit = getattr(
            query,
            "limit",
            None,
        )

        if limit is not None:
            businesses = businesses[
                :limit
            ]

        # =========================================================
        # Convert Gosom records
        # =========================================================

        records: list[
            BusinessRecord
        ] = []

        malformed_count = 0

        for business in businesses:
            try:
                record = (
                    self._to_business_record(
                        business,
                        query,
                    )
                )

            except BusinessDiscoveryProviderError as exc:
                malformed_count += 1

                logger.warning(
                    "gosom_record_discarded",
                    error_type=type(
                        exc
                    ).__name__,
                    error_message=str(
                        exc
                    ),
                    title=optional_text(
                        business.get(
                            "title"
                        )
                    ),
                )

                continue

            records.append(
                record
            )

        logger.info(
            "gosom_discovery_records_prepared",
            raw=raw_count,
            deduplicated=deduplicated_count,
            selected=len(
                businesses
            ),
            valid=len(
                records
            ),
            malformed=malformed_count,
            limit=limit,
            partial=(
                process_failure
                is not None
            ),
            run_dir=str(
                work_dir
            ),
            results_file=str(
                results_file
            ),
        )

        return records

    # ------------------------------------------------------------------
    # Final CSV recovery
    # ------------------------------------------------------------------

    async def _read_final_results(
        self,
        results_file: Path,
    ) -> list[Mapping[str, Any]]:
        """
        Authoritatively read Gosom results after the process settles.

        Progress reads are intentionally best-effort via count_results().

        Final reads are different:
        transient filesystem/decoding/CSV errors receive a small bounded
        number of retries before the provider fails.
        """

        last_error: Exception | None = None

        for attempt in range(
            1,
            self.final_read_attempts + 1,
        ):
            if not results_file.exists():
                if (
                    attempt
                    < self.final_read_attempts
                ):
                    logger.warning(
                        "gosom_results_file_waiting",
                        results_file=str(
                            results_file
                        ),
                        attempt=attempt,
                        attempts=(
                            self.final_read_attempts
                        ),
                    )

                    await asyncio.sleep(
                        self.final_read_delay_seconds
                    )

                    continue

                raise FileNotFoundError(
                    results_file
                )

            try:
                businesses = read_results(
                    results_file
                )

                logger.debug(
                    "gosom_results_final_read",
                    results_file=str(
                        results_file
                    ),
                    attempt=attempt,
                    rows=len(
                        businesses
                    ),
                    results_size=(
                        self._file_size(
                            results_file
                        )
                    ),
                )

                return businesses

            except CSV_READ_ERRORS as exc:
                last_error = exc

                logger.warning(
                    "gosom_results_read_retry",
                    results_file=str(
                        results_file
                    ),
                    results_exists=(
                        results_file.exists()
                    ),
                    results_size=(
                        self._file_size(
                            results_file
                        )
                    ),
                    attempt=attempt,
                    attempts=(
                        self.final_read_attempts
                    ),
                    error_type=type(
                        exc
                    ).__name__,
                    error_message=str(
                        exc
                    ),
                )

                if (
                    attempt
                    < self.final_read_attempts
                ):
                    await asyncio.sleep(
                        self.final_read_delay_seconds
                    )

        assert last_error is not None

        raise last_error

    # ------------------------------------------------------------------
    # Run directory
    # ------------------------------------------------------------------

    def _create_run_directory(
        self,
        *,
        query: DiscoveryQuery,
    ) -> Path:
        """
        Create a persistent directory for one Gosom run.

        Run directories are never automatically removed.
        """

        timestamp = datetime.now(
            UTC
        ).strftime(
            "%Y%m%d_%H%M%S"
        )

        query_slug = self._slugify(
            str(
                query.query
            )
        )

        location_slug = self._slugify(
            str(
                query.location
                or "unknown"
            )
        )

        self.results_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        base_name = (
            f"{timestamp}_"
            f"{query_slug}_"
            f"{location_slug}"
        )

        run_dir = (
            self.results_root
            / base_name
        )

        counter = 1

        while run_dir.exists():
            run_dir = (
                self.results_root
                / f"{base_name}_{counter}"
            )

            counter += 1

        run_dir.mkdir(
            parents=True,
            exist_ok=False,
        )

        return run_dir.resolve()

    @staticmethod
    def _slugify(
        value: str,
    ) -> str:
        """
        Convert query/location text into a filesystem-safe slug.
        """

        value = (
            value
            .strip()
            .casefold()
        )

        result: list[str] = []
        previous_dash = False

        for character in value:
            if character.isalnum():
                result.append(
                    character
                )
                previous_dash = False
                continue

            if previous_dash:
                continue

            result.append(
                "-"
            )
            previous_dash = True

        slug = (
            "".join(
                result
            )
            .strip("-")
        )

        return (
            slug
            or "unknown"
        )

    # ------------------------------------------------------------------
    # Docker command
    # ------------------------------------------------------------------

    def _build_command(
        self,
        *,
        queries_file: Path,
        results_file: Path,
    ) -> list[str]:
        """
        Build the Gosom Docker command.

        Docker bind mount host paths are always absolute.
        """

        queries_file = (
            queries_file
            .expanduser()
            .resolve()
        )

        results_file = (
            results_file
            .expanduser()
            .resolve()
        )

        command = [
            self.docker_command,
            "run",
            "--rm",

            "-v",
            (
                f"{queries_file}"
                ":/queries.txt:ro"
            ),

            "-v",
            (
                f"{results_file.parent}"
                ":/out"
            ),

            "-v",
            (
                f"{self.playwright_cache_volume}"
                ":/opt"
            ),

            self.image,

            "-input",
            "/queries.txt",

            "-results",
            "/out/results.csv",

            "-depth",
            str(
                self.depth
            ),

            "-c",
            str(
                self.concurrency
            ),

            "-browser-pool-size",
            str(
                self.browser_pool_size
            ),

            "-pages-per-browser",
            str(
                self.pages_per_browser
            ),

            "-exit-on-inactivity",
            self.exit_on_inactivity,
        ]

        if self.grid_bbox:
            command.extend(
                [
                    "-grid-bbox",
                    self.grid_bbox,

                    "-grid-cell",
                    str(
                        self.grid_cell_km
                    ),

                    "-zoom",
                    str(
                        self.zoom
                    ),
                ]
            )

        if self.proxy:
            command.extend(
                [
                    "-proxies",
                    self.proxy,
                ]
            )

        return command

    # ------------------------------------------------------------------
    # Process execution
    # ------------------------------------------------------------------

    async def _run(
        self,
        command: list[str],
        *,
        cwd: Path,
        results_file: Path,
    ) -> None:
        """
        Execute Gosom asynchronously.

        This method owns process lifecycle only.

        It does not make the authoritative final decision about whether
        partial CSV output is usable. discover() performs the final CSV
        recovery read after this method returns or raises.
        """

        cwd = (
            cwd
            .expanduser()
            .resolve()
        )

        results_file = (
            results_file
            .expanduser()
            .resolve()
        )

        logger.info(
            "gosom_process_started",
            concurrency=self.concurrency,
            depth=self.depth,
            grid_bbox=self.grid_bbox,
            grid_cell_km=self.grid_cell_km,
            zoom=self.zoom,
            browser_pool_size=(
                self.browser_pool_size
            ),
            pages_per_browser=(
                self.pages_per_browser
            ),
            timeout_seconds=(
                self.timeout_seconds
            ),
            cwd=str(
                cwd
            ),
            cwd_absolute=(
                cwd.is_absolute()
            ),
            results_file=str(
                results_file
            ),
            results_file_absolute=(
                results_file.is_absolute()
            ),
        )

        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout_task = asyncio.create_task(
            self._consume_stream(
                process.stdout,
                stream_name="stdout",
            )
        )

        stderr_task = asyncio.create_task(
            self._consume_stream(
                process.stderr,
                stream_name="stderr",
            )
        )

        progress_task = asyncio.create_task(
            self._monitor_results(
                process=process,
                results_file=results_file,
            )
        )

        try:
            await asyncio.wait_for(
                process.wait(),
                timeout=self.timeout_seconds,
            )

        except asyncio.CancelledError:
            logger.warning(
                "gosom_process_cancelled",
                discovered=count_results(
                    results_file
                ),
                results_file=str(
                    results_file
                ),
                results_exists=(
                    results_file.exists()
                ),
                results_size=(
                    self._file_size(
                        results_file
                    )
                ),
            )

            await self._terminate_process(
                process
            )

            raise

        except asyncio.TimeoutError:
            logger.error(
                "gosom_process_timeout",
                timeout_seconds=(
                    self.timeout_seconds
                ),
                discovered=count_results(
                    results_file
                ),
                results_file=str(
                    results_file
                ),
                results_exists=(
                    results_file.exists()
                ),
                results_size=(
                    self._file_size(
                        results_file
                    )
                ),
            )

            await self._terminate_process(
                process
            )

            raise

        finally:
            if process.returncode is not None:
                await progress_task

            else:
                progress_task.cancel()

                await asyncio.gather(
                    progress_task,
                    return_exceptions=True,
                )

            await asyncio.gather(
                stdout_task,
                stderr_task,
                return_exceptions=True,
            )

        if process.returncode != 0:
            raise RuntimeError(
                "Gosom exited with code "
                f"{process.returncode}"
            )

        logger.info(
            "gosom_process_completed",
            returncode=(
                process.returncode
            ),
            discovered=count_results(
                results_file
            ),
            results_file=str(
                results_file
            ),
            results_exists=(
                results_file.exists()
            ),
            results_size=(
                self._file_size(
                    results_file
                )
            ),
        )

    # ------------------------------------------------------------------
    # Progress monitoring
    # ------------------------------------------------------------------

    async def _monitor_results(
        self,
        *,
        process: asyncio.subprocess.Process,
        results_file: Path,
    ) -> None:
        """
        Monitor results.csv while Gosom is running.

        Progress reads are deliberately non-critical.

        `discovered`:
            current total raw CSV row count.

        `added`:
            rows added since the previous successful progress poll.
        """

        previous_count = 0

        while process.returncode is None:
            await asyncio.sleep(
                self.progress_interval_seconds
            )

            count = count_results(
                results_file
            )

            if count <= previous_count:
                continue

            logger.info(
                "gosom_discovery_progress",
                discovered=count,
                added=(
                    count
                    - previous_count
                ),
                results_file=str(
                    results_file
                ),
            )

            previous_count = count

        count = count_results(
            results_file
        )

        if count > previous_count:
            logger.info(
                "gosom_discovery_progress",
                discovered=count,
                added=(
                    count
                    - previous_count
                ),
                results_file=str(
                    results_file
                ),
            )

    # ------------------------------------------------------------------
    # Process output
    # ------------------------------------------------------------------

    @staticmethod
    async def _consume_stream(
        stream: asyncio.StreamReader | None,
        *,
        stream_name: str,
    ) -> None:
        """
        Continuously drain Docker stdout/stderr.

        This prevents full subprocess pipes from blocking Gosom.
        """

        if stream is None:
            return

        while True:
            line = await stream.readline()

            if not line:
                break

            message = line.decode(
                errors="replace",
            ).strip()

            if not message:
                continue

            logger.debug(
                "gosom_output",
                stream=stream_name,
                message=message,
            )

    # ------------------------------------------------------------------
    # Process termination
    # ------------------------------------------------------------------

    @staticmethod
    async def _terminate_process(
        process: asyncio.subprocess.Process,
    ) -> None:
        """
        Gracefully terminate Gosom before forcing a kill.
        """

        if process.returncode is not None:
            return

        try:
            process.terminate()

            await asyncio.wait_for(
                process.wait(),
                timeout=5,
            )

            return

        except (
            asyncio.TimeoutError,
            ProcessLookupError,
        ):
            pass

        if process.returncode is not None:
            return

        try:
            process.kill()

        except ProcessLookupError:
            return

        await process.wait()

    # ------------------------------------------------------------------
    # Filesystem helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _file_size(
        path: Path,
    ) -> int:
        """
        Return file size without allowing diagnostic logging to fail.
        """

        try:
            return path.stat().st_size
        except OSError:
            return 0

    # ------------------------------------------------------------------
    # Record conversion
    # ------------------------------------------------------------------

    def _to_business_record(
        self,
        business: Mapping[str, Any],
        query: DiscoveryQuery,
    ) -> BusinessRecord:
        """
        Convert one Gosom result into Autlead's canonical schema.
        """

        name = required_text(
            business.get(
                "title"
            ),
            "title",
        )

        website = optional_text(
            business.get(
                "website"
            )
        )

        address = optional_text(
            business.get(
                "address"
            )
            or business.get(
                "complete_address"
            )
        )

        city, country = parse_location(
            optional_text(
                query.location
            )
        )

        external_id = extract_external_id(
            business
        )

        return BusinessRecord(
            name=name,
            website=website,
            domain=extract_domain(
                website
            ),
            phone=optional_text(
                business.get(
                    "phone"
                )
            ),
            country=country,
            city=city,
            address=address,
            category=optional_text(
                business.get(
                    "category"
                )
            ),
            source_name=self.source_name,
            source_type=self.source_type,
            provider_name=self.provider_name,
            external_id=external_id,
            raw_data=dict(
                business
            ),
        )

    async def load_results(
            self,
            *,
            results_file: str | Path,
            query: DiscoveryQuery,
    ) -> list[BusinessRecord]:
        """
        Load and process an existing Gosom results.csv without running Gosom.
        """

        results_path = (
            Path(results_file)
            .expanduser()
            .resolve()
        )

        try:
            businesses = await self._read_final_results(
                results_path
            )
        except FileNotFoundError as exc:
            raise BusinessDiscoveryProviderError(
                "Gosom results file does not exist"
            ) from exc
        except CSV_READ_ERRORS as exc:
            raise BusinessDiscoveryProviderError(
                "Could not read Gosom results file"
            ) from exc

        raw_count = len(
            businesses
        )

        if raw_count == 0:
            raise BusinessDiscoveryProviderError(
                "Gosom results file contains no usable records"
            )

        unique_external_ids = {
            external_id
            for business in businesses
            if (
                external_id := extract_external_id(
                    business
                )
            )
        }

        logger.info(
            "gosom_existing_results_loaded",
            raw=raw_count,
            unique_external_ids=len(
                unique_external_ids
            ),
            records_without_external_id=sum(
                1
                for business in businesses
                if extract_external_id(
                    business
                )
                is None
            ),
            results_file=str(
                results_path
            ),
        )

        businesses = deduplicate(
            businesses
        )

        deduplicated_count = len(
            businesses
        )

        limit = getattr(
            query,
            "limit",
            None,
        )

        if limit is not None:
            businesses = businesses[
                :limit
            ]

        records: list[
            BusinessRecord
        ] = []

        malformed_count = 0

        for business in businesses:
            try:
                records.append(
                    self._to_business_record(
                        business,
                        query,
                    )
                )
            except BusinessDiscoveryProviderError as exc:
                malformed_count += 1

                logger.warning(
                    "gosom_record_discarded",
                    error_type=type(
                        exc
                    ).__name__,
                    error_message=str(
                        exc
                    ),
                    title=optional_text(
                        business.get(
                            "title"
                        )
                    ),
                )

        logger.info(
            "gosom_existing_records_prepared",
            raw=raw_count,
            deduplicated=deduplicated_count,
            selected=len(
                businesses
            ),
            valid=len(
                records
            ),
            malformed=malformed_count,
            limit=limit,
            results_file=str(
                results_path
            ),
        )

        return records