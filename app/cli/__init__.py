from __future__ import annotations

from app.cli.acquisition import (
    build_parser as build_acquisition_parser,
    run as run_acquisition,
)
from app.cli.outreach import (
    build_parser as build_email_send_parser,
    run as run_email_send,
)
from app.cli.enrichment import (
    build_parser as build_enrichment_parser,
    run as run_enrichment,
)
from app.cli.webartsy_saved import (
    build_parser as build_webartsy_saved_parser,
    run as run_webartsy_saved,
)


__all__ = [
    "build_acquisition_parser",
    "build_email_send_parser",
    "build_enrichment_parser",
    "build_webartsy_saved_parser",
    "run_acquisition",
    "run_email_send",
    "run_enrichment",
    "run_webartsy_saved",
]