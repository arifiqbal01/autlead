# app/pipelines/common/person_email.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.extract.email import (
    generate_person_email_candidates,
)
from app.load.postgres.person_emails import (
    load_person_email_observation,
)
from app.policies.qualification import (
    EmailVerificationAssessment,
    evaluate_email_qualification,
)
from app.providers.email.verification import (
    EmailVerificationProvider,
    EmailVerificationRequest,
    EmailVerificationResult,
)
from app.transform.normalization.email import (
    normalize_email,
)


logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PersonEmailTarget:
    """
    One persisted person eligible for email verification/enrichment.

    If an email already exists:
        - skip when it has already been verified successfully
        - otherwise verify it first

    If no qualified email exists:
        - generate deterministic candidates from person name
          and company domain
        - verify candidates sequentially
        - persist verification evidence
        - store the first qualified candidate on Person.email
    """

    person_id: int
    company_id: int

    person_name: str
    company_domain: str

    email: str | None = None

    source_urls: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PersonEmailResult:
    """
    Final successful verification result for one persisted person.

    A person only appears here when at least one verification
    request completed successfully.
    """

    person_id: int
    person_name: str

    email: str
    status: str
    confidence: float

    is_qualified: bool
    qualification_reason: str

    candidate_source: str
    persisted: bool

    verification: EmailVerificationResult


@dataclass(frozen=True, slots=True)
class PersonEmailAnalysisResult:
    """
    Result of email candidate generation and verification.

    attempted_count:
        Number of people considered.

    verified_count:
        Number of candidate email addresses successfully checked
        by the verification provider.

    qualified_count:
        Number of people for whom a qualified email was found.

    already_verified_count:
        Number of people skipped because their existing Person.email
        already has successful verification evidence.

    generated_count:
        Number of deterministic pattern candidates generated.

    failed_count:
        Number of normalization/provider failures.

    persisted_count:
        Number of verification observations persisted.
    """

    people: list[PersonEmailResult]

    attempted_count: int
    verified_count: int
    qualified_count: int
    already_verified_count: int
    generated_count: int
    failed_count: int
    persisted_count: int


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def analyze_person_emails(
    *,
    session: AsyncSession,
    provider: EmailVerificationProvider,
    targets: list[PersonEmailTarget],
    source_id: int | None = None,
    observed_at: datetime | None = None,
    candidate_limit: int = 8,
) -> PersonEmailAnalysisResult:
    """
    Find and verify a usable email for persisted people.

    Pipeline:

        persisted person
            ↓
        existing Person.email?
            ↓
        already verified?
            ├── yes → skip
            └── no  → verify existing address
                          ↓
                    qualified?
                        ├── yes → done
                        └── no
                            ↓
                    generate name/domain candidates
                            ↓
                    verify sequentially
                            ↓
                    first qualified candidate
                            ↓
                    update Person.email

    Verification observations are persisted for every candidate
    that receives a valid response from the verification provider.

    Pattern-generated catch-all addresses are never accepted as
    qualified because SMTP acceptance on a catch-all domain does
    not prove that the guessed mailbox belongs to the person.

    Transaction ownership belongs to the caller.
    """

    if observed_at is None:
        observed_at = datetime.now(
            UTC
        )

    if not targets:
        logger.info(
            "person_email_analysis_skipped",
            reason="no_targets",
            targets=0,
        )

        return PersonEmailAnalysisResult(
            people=[],
            attempted_count=0,
            verified_count=0,
            qualified_count=0,
            already_verified_count=0,
            generated_count=0,
            failed_count=0,
            persisted_count=0,
        )

    logger.info(
        "person_email_analysis_started",
        targets=len(targets),
        provider=provider.__class__.__name__,
        candidate_limit=candidate_limit,
    )

    results: list[
        PersonEmailResult
    ] = []

    attempted_count = 0
    verified_count = 0
    qualified_count = 0
    already_verified_count = 0
    generated_count = 0
    failed_count = 0
    persisted_count = 0

    for target in targets:
        attempted_count += 1

        logger.info(
            "person_email_processing_started",
            person_id=target.person_id,
            company_id=target.company_id,
            person_name=target.person_name,
            existing_email=target.email,
            company_domain=target.company_domain,
        )

        # =====================================================
        # 1. Existing email
        # =====================================================

        existing_email: str | None = None

        if target.email:
            existing_email = normalize_email(
                target.email
            )

            if existing_email is None:
                failed_count += 1

                logger.warning(
                    "person_existing_email_normalization_failed",
                    person_id=target.person_id,
                    company_id=target.company_id,
                    person_name=target.person_name,
                    email=target.email,
                )

            else:
                already_verified = (
                    await _has_verified_email(
                        session=session,
                        person_id=target.person_id,
                        normalized_email=existing_email,
                    )
                )

                if already_verified:
                    already_verified_count += 1

                    logger.info(
                        "person_email_skipped",
                        person_id=target.person_id,
                        company_id=target.company_id,
                        person_name=target.person_name,
                        email=existing_email,
                        reason="already_verified",
                    )

                    continue

        # =====================================================
        # 2. Build ordered candidates
        # =====================================================

        candidates: list[
            tuple[str, str]
        ] = []

        if existing_email is not None:
            candidates.append(
                (
                    existing_email,
                    "existing",
                )
            )

        generated_candidates = (
            generate_person_email_candidates(
                name=target.person_name,
                domain=target.company_domain,
                limit=candidate_limit,
            )
        )

        generated_count += len(
            generated_candidates
        )

        seen_candidates: set[str] = {
            existing_email
        } if existing_email else set()

        for generated_email in (
            generated_candidates
        ):
            normalized_candidate = normalize_email(
                generated_email
            )

            if normalized_candidate is None:
                continue

            if (
                normalized_candidate
                in seen_candidates
            ):
                continue

            seen_candidates.add(
                normalized_candidate
            )

            candidates.append(
                (
                    normalized_candidate,
                    "pattern",
                )
            )

        if not candidates:
            logger.info(
                "person_email_no_candidates",
                person_id=target.person_id,
                company_id=target.company_id,
                person_name=target.person_name,
                company_domain=target.company_domain,
            )

            continue

        logger.info(
            "person_email_candidates_prepared",
            person_id=target.person_id,
            company_id=target.company_id,
            person_name=target.person_name,
            candidates=len(candidates),
            existing_email=(
                existing_email is not None
            ),
            generated=(
                len(candidates)
                - (
                    1
                    if existing_email is not None
                    else 0
                )
            ),
        )

        # =====================================================
        # 3. Verify candidates sequentially
        # =====================================================

        final_result: (
            PersonEmailResult | None
        ) = None

        for (
            candidate_email,
            candidate_source,
        ) in candidates:
            logger.info(
                "person_email_verification_started",
                person_id=target.person_id,
                company_id=target.company_id,
                person_name=target.person_name,
                email=candidate_email,
                candidate_source=candidate_source,
            )

            try:
                verification = (
                    await provider.verify(
                        EmailVerificationRequest(
                            email=candidate_email,
                        )
                    )
                )

            except Exception as exc:
                failed_count += 1

                logger.warning(
                    "person_email_verification_failed",
                    person_id=target.person_id,
                    company_id=target.company_id,
                    person_name=target.person_name,
                    email=candidate_email,
                    candidate_source=candidate_source,
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )

                continue

            verified_count += 1

            # =================================================
            # 4. Qualification
            # =================================================

            decision = (
                evaluate_email_qualification(
                    EmailVerificationAssessment(
                        status=(
                            verification.status
                        ),
                        valid=(
                            verification.valid
                        ),
                        score=(
                            verification.score
                        ),
                        risk=(
                            verification.risk
                        ),
                        smtp_verdict=(
                            verification.smtp.verdict
                        ),
                    )
                )
            )

            is_qualified = (
                decision.is_qualified
            )

            qualification_reason = (
                decision.reason
            )

            # -------------------------------------------------
            # Pattern guesses must not be accepted on catch-all
            # domains.
            #
            # A catch-all server accepting:
            #
            #     john@example.com
            #
            # does not prove that John's mailbox exists.
            # -------------------------------------------------

            if (
                candidate_source == "pattern"
                and (
                    verification.smtp.catch_all
                    or verification.smtp.verdict
                    == "catch_all"
                )
            ):
                is_qualified = False

                qualification_reason = (
                    "pattern_generated_email_on_"
                    "catch_all_domain"
                )

            confidence = (
                verification.score / 100
            )

            # =================================================
            # 5. Persist verification evidence
            # =================================================

            await load_person_email_observation(
                session=session,
                person_id=target.person_id,
                company_id=target.company_id,
                source_id=source_id,
                provider_name=(
                    verification.provider
                ),
                email=candidate_email,
                normalized_email=(
                    candidate_email
                ),
                confidence=confidence,
                verification_method=(
                    _verification_method(
                        verification
                    )
                ),
                verification_result=(
                    verification.status
                ),
                pattern_inferred=(
                    candidate_source
                    == "pattern"
                ),
                source_urls=(
                    " ; ".join(
                        target.source_urls
                    )
                    if target.source_urls
                    else None
                ),
                found_public_emails=None,
                observed_at=observed_at,
            )

            persisted_count += 1

            candidate_result = (
                PersonEmailResult(
                    person_id=(
                        target.person_id
                    ),
                    person_name=(
                        target.person_name
                    ),
                    email=candidate_email,
                    status=(
                        verification.status
                    ),
                    confidence=confidence,
                    is_qualified=(
                        is_qualified
                    ),
                    qualification_reason=(
                        qualification_reason
                    ),
                    candidate_source=(
                        candidate_source
                    ),
                    persisted=True,
                    verification=(
                        verification
                    ),
                )
            )

            # Keep the most recent verification as the
            # person's result when none qualify.
            final_result = (
                candidate_result
            )

            logger.info(
                "person_email_verified",
                person_id=target.person_id,
                company_id=target.company_id,
                person_name=target.person_name,
                email=candidate_email,
                candidate_source=candidate_source,
                provider=verification.provider,
                status=verification.status,
                valid=verification.valid,
                score=verification.score,
                risk=verification.risk,
                smtp_verdict=(
                    verification.smtp.verdict
                ),
                catch_all=(
                    verification.smtp.catch_all
                ),
                is_qualified=(
                    is_qualified
                ),
                qualification_reason=(
                    qualification_reason
                ),
            )

            # =================================================
            # 6. First qualified candidate wins
            # =================================================

            if not is_qualified:
                continue

            qualified_count += 1

            if (
                candidate_email
                != existing_email
            ):
                await _update_person_email(
                    session=session,
                    person_id=target.person_id,
                    company_id=target.company_id,
                    email=candidate_email,
                )

                logger.info(
                    "person_email_assigned",
                    person_id=target.person_id,
                    company_id=target.company_id,
                    person_name=target.person_name,
                    email=candidate_email,
                    candidate_source=candidate_source,
                )

            break

        if final_result is not None:
            results.append(
                final_result
            )

    # =========================================================
    # 7. Completed
    # =========================================================

    result = PersonEmailAnalysisResult(
        people=results,
        attempted_count=attempted_count,
        verified_count=verified_count,
        qualified_count=qualified_count,
        already_verified_count=(
            already_verified_count
        ),
        generated_count=(
            generated_count
        ),
        failed_count=failed_count,
        persisted_count=persisted_count,
    )

    logger.info(
        "person_email_analysis_completed",
        targets=len(targets),
        attempted=result.attempted_count,
        verified=result.verified_count,
        qualified=result.qualified_count,
        already_verified=(
            result.already_verified_count
        ),
        generated=(
            result.generated_count
        ),
        failed=result.failed_count,
        persisted=result.persisted_count,
    )

    return result


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


async def _has_verified_email(
    *,
    session: AsyncSession,
    person_id: int,
    normalized_email: str,
) -> bool:
    """
    Return True when this exact email already has successful
    verification evidence for the person.

    Matching both person_id and normalized_email prevents an old
    verified address from suppressing verification of a newly
    assigned address.
    """

    result = await session.execute(
        text(
            """
            SELECT 1
            FROM public.person_email_observations
            WHERE person_id = :person_id
              AND normalized_email = :normalized_email
              AND verification_result = 'deliverable'
            LIMIT 1
            """
        ),
        {
            "person_id": person_id,
            "normalized_email": (
                normalized_email
            ),
        },
    )

    return (
        result.scalar_one_or_none()
        is not None
    )


async def _update_person_email(
    *,
    session: AsyncSession,
    person_id: int,
    company_id: int,
    email: str,
) -> None:
    """
    Store a qualified email on the persisted Person.

    The caller owns the transaction.
    """

    await session.execute(
        text(
            """
            UPDATE public.people
            SET
                email = :email,
                updated_at = NOW()
            WHERE id = :person_id
              AND company_id = :company_id
            """
        ),
        {
            "person_id": person_id,
            "company_id": company_id,
            "email": email,
        },
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _verification_method(
    verification: EmailVerificationResult,
) -> str:
    """
    Describe the strongest verification mechanism attempted.

    The provider owns the technical verification result.
    This helper only maps that evidence into the existing
    persistence field.
    """

    if (
        verification.smtp.verdict
        != "skipped"
    ):
        return "smtp+mx"

    return "mx"