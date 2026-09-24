from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.providers.email.verification.errors import (
    MrEmailCheckerError,
    MrEmailCheckerParseError,
    MrEmailCheckerTimeoutError,
)
from app.providers.email.verification.models import (
    EmailSmtpResult,
    EmailVerificationRequest,
    EmailVerificationResult,
)


class MrEmailCheckerProvider:
    name = "mr_email_checker"

    def __init__(
        self,
        *,
        timeout_seconds: float = 30.0,
        smtp_enabled: bool = True,
        smtp_from: str = "verify@enrichment.nl",
        smtp_helo_host: str = "enrichment.nl",
        smtp_timeout_ms: int = 10_000,
        detect_catch_all: bool = True,
        node_binary: str = "node",
        runner_path: Path | None = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._smtp_enabled = smtp_enabled
        self._smtp_from = smtp_from
        self._smtp_helo_host = smtp_helo_host
        self._smtp_timeout_ms = smtp_timeout_ms
        self._detect_catch_all = detect_catch_all
        self._node_binary = node_binary

        if runner_path is None:
            runner_path = (
                Path(__file__)
                .resolve()
                .parents[4]
                / "tools"
                / "email_verification"
                / "runner.mjs"
            )

        self._runner_path = runner_path

    async def verify(
        self,
        request: EmailVerificationRequest,
    ) -> EmailVerificationResult:
        payload = {
            "email": request.email,
            "options": {
                "smtp": self._smtp_enabled,
                "smtpFrom": self._smtp_from,
                "smtpHeloHost": self._smtp_helo_host,
                "smtpTimeoutMs": self._smtp_timeout_ms,
                "detectCatchAll": self._detect_catch_all,
            },
        }

        payload_bytes = json.dumps(
            payload,
        ).encode("utf-8")

        try:
            process = await asyncio.create_subprocess_exec(
                self._node_binary,
                str(self._runner_path),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as error:
            raise MrEmailCheckerError(
                "Failed to start mr-email-checker runner."
            ) from error

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(
                    input=payload_bytes,
                ),
                timeout=self._timeout_seconds,
            )
        except TimeoutError as error:
            process.kill()
            await process.communicate()

            raise MrEmailCheckerTimeoutError(
                "mr-email-checker runner timed out."
            ) from error

        stderr_text = stderr.decode(
            "utf-8",
            errors="replace",
        ).strip()

        stdout_text = stdout.decode(
            "utf-8",
            errors="replace",
        ).strip()

        if process.returncode != 0:
            raise MrEmailCheckerError(
                "mr-email-checker runner failed"
                + (
                    f": {stderr_text}"
                    if stderr_text
                    else "."
                )
            )

        if not stdout_text:
            raise MrEmailCheckerParseError(
                "mr-email-checker returned an empty response."
            )

        try:
            raw = json.loads(
                stdout_text,
            )
        except json.JSONDecodeError as error:
            raise MrEmailCheckerParseError(
                "mr-email-checker returned invalid JSON."
            ) from error

        if not isinstance(
            raw,
            dict,
        ):
            raise MrEmailCheckerParseError(
                "mr-email-checker response must be an object."
            )

        return self._parse_result(
            raw,
        )

    def _parse_result(
        self,
        raw: dict[str, Any],
    ) -> EmailVerificationResult:
        try:
            smtp_raw = raw["smtp"]

            if not isinstance(
                smtp_raw,
                dict,
            ):
                raise MrEmailCheckerParseError(
                    "Invalid SMTP result."
                )

            catch_all_raw = smtp_raw.get(
                "catchAll"
            )

            if catch_all_raw is None:
                catch_all = False
            elif isinstance(
                catch_all_raw,
                bool,
            ):
                catch_all = catch_all_raw
            else:
                raise MrEmailCheckerParseError(
                    "Invalid SMTP catchAll value: "
                    f"{catch_all_raw!r} "
                    f"(type="
                    f"{type(catch_all_raw).__name__}"
                    f")."
                )

            smtp_verdict_raw = smtp_raw[
                "verdict"
            ]

            if not isinstance(
                smtp_verdict_raw,
                str,
            ):
                raise MrEmailCheckerParseError(
                    "Invalid SMTP verdict value: "
                    f"{smtp_verdict_raw!r}."
                )

            smtp_message_raw = smtp_raw.get(
                "message"
            )

            if (
                smtp_message_raw is not None
                and not isinstance(
                    smtp_message_raw,
                    str,
                )
            ):
                raise MrEmailCheckerParseError(
                    "Invalid SMTP message value: "
                    f"{smtp_message_raw!r}."
                )

            smtp_message = smtp_message_raw

            smtp_verdict = _normalize_smtp_verdict(
                verdict=smtp_verdict_raw,
                message=smtp_message,
            )

            smtp = EmailSmtpResult(
                verdict=smtp_verdict,
                code=smtp_raw.get(
                    "code"
                ),
                message=smtp_message,
                catch_all=catch_all,
                latency_ms=smtp_raw.get(
                    "latencyMs"
                ),
            )

            reasons_raw = raw.get(
                "reasons"
            )

            if reasons_raw is None:
                reasons: list[str] = []
            elif isinstance(
                reasons_raw,
                list,
            ):
                reasons = [
                    str(reason)
                    for reason in reasons_raw
                ]
            else:
                raise MrEmailCheckerParseError(
                    "Invalid reasons value."
                )

            status = raw["status"]
            valid = raw["valid"]

            if smtp.verdict == "blocked":
                status = "unknown"
                valid = False

                reasons = [
                    reason
                    for reason in reasons
                    if reason
                    != "mailbox_not_found"
                ]

                if (
                    "smtp_blocked"
                    not in reasons
                ):
                    reasons.append(
                        "smtp_blocked"
                    )

            return EmailVerificationResult(
                email=raw["email"],
                canonical=raw[
                    "canonical"
                ],
                status=status,
                valid=valid,
                score=raw["score"],
                risk=raw["risk"],
                reasons=reasons,
                smtp=smtp,
                provider=self.name,
            )

        except MrEmailCheckerParseError:
            raise

        except KeyError as error:
            raise MrEmailCheckerParseError(
                "mr-email-checker response "
                f"is missing required field: "
                f"{error.args[0]!r}."
            ) from error

        except ValidationError as error:
            raise MrEmailCheckerParseError(
                "Invalid response from "
                "mr-email-checker: "
                f"{error}"
            ) from error


def _normalize_smtp_verdict(
    *,
    verdict: str,
    message: str | None,
) -> str:
    normalized_message = (
        message.casefold().strip()
        if message
        else ""
    )

    blocked_markers = (
        "blocked using spamhaus",
        "spamhaus",
        "client blocked",
        "client host rejected",
        "client rejected",
        "client denied",
        "client blacklisted",
        "client is blacklisted",
        "ip blacklisted",
        "ip address blacklisted",
        "sender ip blocked",
        "connection blocked",
        "service unavailable; client",
    )

    if any(
        marker in normalized_message
        for marker in blocked_markers
    ):
        return "blocked"

    return verdict