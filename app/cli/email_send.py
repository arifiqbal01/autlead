from __future__ import annotations

import argparse

from app.bootstrap.providers import (
    create_email_sending_provider,
)
from app.core.config.settings import settings
from app.core.database.session import SessionFactory
from app.core.logging import get_logger
from app.models.schemas.email_send import (
    EmailSendRequest,
)
from app.pipelines.email import (
    get_email_candidates,
    send_email,
)

logger = get_logger(__name__)


def build_parser(
    parser: argparse.ArgumentParser | None = None,
) -> argparse.ArgumentParser:
    if parser is None:
        parser = argparse.ArgumentParser(
            description=(
                "Send emails to eligible persisted contacts."
            ),
        )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Maximum number of emails to send. "
            "Defaults to EMAIL_SEND_LIMIT."
        ),
    )

    parser.add_argument(
        "--min-confidence",
        type=float,
        default=None,
        help=(
            "Minimum email verification confidence. "
            "Defaults to EMAIL_MIN_VERIFICATION_CONFIDENCE."
        ),
    )

    parser.add_argument(
        "--verification-status",
        action="append",
        dest="verification_statuses",
        default=None,
        help=(
            "Allowed verification status. "
            "May be supplied multiple times."
        ),
    )

    parser.add_argument(
        "--include-previously-sent",
        action="store_true",
        help=(
            "Include addresses already present in "
            "email_messages. Use with caution."
        ),
    )

    parser.add_argument(
        "--subject",
        required=True,
        help="Email subject.",
    )

    parser.add_argument(
        "--text",
        required=True,
        help="Plain-text email body.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Show selected recipients without sending "
            "or persisting email messages."
        ),
    )

    return parser


async def run(
    args: argparse.Namespace,
) -> None:
    if (
        not settings.email_send_enabled
        and not args.dry_run
    ):
        raise RuntimeError(
            "Email sending is disabled. "
            "Set EMAIL_SEND_ENABLED=true before sending."
        )

    limit = (
        args.limit
        if args.limit is not None
        else settings.email_send_limit
    )

    minimum_confidence = (
        args.min_confidence
        if args.min_confidence is not None
        else settings.email_min_verification_confidence
    )

    if args.verification_statuses:
        allowed_statuses = set(
            args.verification_statuses
        )
    else:
        allowed_statuses = {
            value.strip()
            for value in (
                settings.email_allowed_verification_statuses.split(
                    ","
                )
            )
            if value.strip()
        }

    skip_previously_sent = (
        not args.include_previously_sent
        and settings.email_skip_previously_sent
    )

    if limit < 1:
        raise ValueError(
            "Email send limit must be at least 1."
        )

    if not allowed_statuses:
        raise ValueError(
            "At least one verification status is required."
        )

    logger.info(
        "email_pipeline_started",
        limit=limit,
        minimum_confidence=minimum_confidence,
        allowed_statuses=sorted(
            allowed_statuses
        ),
        skip_previously_sent=skip_previously_sent,
        dry_run=args.dry_run,
    )

    async with SessionFactory() as session:
        candidates = await get_email_candidates(
            session,
            limit=limit,
            minimum_confidence=minimum_confidence,
            allowed_verification_results=allowed_statuses,
            skip_previously_sent=skip_previously_sent,
        )

        if args.dry_run:
            print_candidates(
                candidates,
                limit=limit,
                minimum_confidence=minimum_confidence,
            )
            return

        if not settings.resend_from_email:
            raise RuntimeError(
                "RESEND_FROM_EMAIL is not configured."
            )

        provider = create_email_sending_provider()

        sent = 0
        failed = 0

        for candidate in candidates:
            request = EmailSendRequest(
                from_email=settings.resend_from_email,
                to_email=candidate.email,
                reply_to=settings.resend_reply_to,
                subject=args.subject,
                text=args.text,
            )

            try:
                await send_email(
                    session,
                    provider=provider,
                    person_id=candidate.person_id,
                    company_id=candidate.company_id,
                    request=request,
                )

                # Commit each successful external side effect.
                #
                # Resend may already have accepted the message,
                # so successful sends should be persisted
                # independently from the rest of the batch.
                await session.commit()

                sent += 1

                logger.info(
                    "email_sent",
                    person_id=candidate.person_id,
                    company_id=candidate.company_id,
                    email=candidate.email,
                )

            except Exception:
                await session.rollback()

                failed += 1

                logger.exception(
                    "email_send_failed",
                    person_id=candidate.person_id,
                    company_id=candidate.company_id,
                    email=candidate.email,
                )

    print()
    print("=" * 80)
    print("Email Pipeline")
    print("=" * 80)

    print(
        f"  Candidates:        {len(candidates)}"
    )
    print(
        f"  Sent:              {sent}"
    )
    print(
        f"  Failed:            {failed}"
    )
    print(
        f"  Limit:             {limit}"
    )
    print(
        f"  Min confidence:    {minimum_confidence:.2f}"
    )

    print("=" * 80)


def print_candidates(
    candidates,
    *,
    limit: int,
    minimum_confidence: float,
) -> None:
    print()
    print("=" * 80)
    print("Email Pipeline — Dry Run")
    print("=" * 80)

    print(
        f"  Limit:             {limit}"
    )
    print(
        f"  Min confidence:    {minimum_confidence:.2f}"
    )
    print(
        f"  Candidates:        {len(candidates)}"
    )

    print()
    print("Recipients")

    if not candidates:
        print("  None")
    else:
        for candidate in candidates:
            print(
                f"  - {candidate.email} | "
                f"person={candidate.person_id} | "
                f"company={candidate.company_id} | "
                f"status={candidate.verification_result} | "
                f"confidence={candidate.confidence:.2f}"
            )

    print()
    print("=" * 80)