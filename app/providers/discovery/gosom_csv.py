# app/providers/discovery/gosom_csv.py

from __future__ import annotations

import csv
from collections.abc import Mapping
from pathlib import Path
from typing import Any


CSV_READ_ERRORS = (
    OSError,
    UnicodeDecodeError,
    csv.Error,
)


def read_results(
    results_file: Path,
) -> list[Mapping[str, Any]]:
    """
    Read Gosom CSV results.

    The caller is responsible for deciding whether read failures should:

        - be ignored temporarily for progress monitoring
        - be retried during terminal recovery
        - fail the provider

    Returns an empty list when the CSV contains no usable data rows.
    """

    with results_file.open(
        mode="r",
        newline="",
        encoding="utf-8",
    ) as file:
        return list(
            csv.DictReader(file)
        )


def count_results(
    results_file: Path,
) -> int:
    """
    Best-effort count of currently available Gosom CSV rows.

    This function is intended for non-critical progress monitoring.

    Gosom may be writing results.csv concurrently. Temporary filesystem,
    decoding, or CSV parsing failures therefore return zero rather than
    interrupting an active discovery run.

    IMPORTANT:

    Do not use this function as the authoritative terminal recovery check.
    Final recovery should call read_results() with a small bounded retry
    loop from the provider.
    """

    if not results_file.exists():
        return 0

    try:
        return len(
            read_results(
                results_file
            )
        )

    except CSV_READ_ERRORS:
        return 0