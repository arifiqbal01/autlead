from __future__ import annotations

import json
import random
import re
from collections.abc import Awaitable, Callable
from typing import Any

from groq import AsyncGroq

from app.core.logging import get_logger
from app.models.schemas.people import PersonCandidate
from app.providers.llm.models import (
    LLMRequest,
    LLMResponse,
)
from app.providers.llm.prompt import (
    build_people_prompt,
)

from .errors import (
    GroqParseError,
    GroqProviderError,
    GroqRateLimitedError,
)
from .models import GroqPeopleExtraction
from .rate_limiter import GroqRateLimiter

logger = get_logger(__name__)


class GroqLLMProvider:
    name = "groq"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        requests_per_minute: int = 25,
        requests_per_day: int = 900,
        max_rate_limit_attempts: int = 3,
        timeout: float = 60.0,
    ) -> None:
        if not api_key.strip():
            raise ValueError(
                "Groq API key is required"
            )

        if max_rate_limit_attempts < 1:
            raise ValueError(
                "max_rate_limit_attempts must be >= 1"
            )

        self._model = model

        self._client = AsyncGroq(
            api_key=api_key,
            timeout=timeout,
        )

        self._rate_limiter = GroqRateLimiter(
            requests_per_minute=(
                requests_per_minute
            ),
            requests_per_day=(
                requests_per_day
            ),
        )

        self._max_rate_limit_attempts = (
            max_rate_limit_attempts
        )

    # =========================================================
    # Generic generation
    # =========================================================

    async def generate(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        completion = (
            await self._execute_with_rate_limit(
                lambda: (
                    self._client.chat.completions.create(
                        model=self._model,
                        messages=[
                            {
                                "role": "user",
                                "content": (
                                    request.prompt
                                ),
                            }
                        ],
                        temperature=0.2,
                    )
                )
            )
        )

        text = self._extract_content(
            completion
        )

        return LLMResponse(
            text=text,
            provider=self.name,
            model=self._model,
        )

    # =========================================================
    # People extraction / refinement
    # =========================================================

    async def extract_people(
        self,
        *,
        company_name: str,
        website_url: str,
        website_text: str,
        candidates: (
            list[PersonCandidate]
            | None
        ) = None,
    ) -> GroqPeopleExtraction:
        prompt = build_people_prompt(
            company_name=company_name,
            website_url=website_url,
            website_text=website_text,
            candidates=(
                candidates
                or []
            ),
        )

        schema = (
            GroqPeopleExtraction
            .model_json_schema()
        )

        schema_text = json.dumps(
            schema,
            separators=(
                ",",
                ":",
            ),
        )

        system_prompt = (
            "Return only valid JSON. "
            "Do not use markdown fences. "
            "The output must conform exactly to this "
            "JSON Schema:\n"
            f"{schema_text}"
        )

        completion = (
            await self._execute_with_rate_limit(
                lambda: (
                    self._client.chat.completions.create(
                        model=self._model,
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    system_prompt
                                ),
                            },
                            {
                                "role": "user",
                                "content": prompt,
                            },
                        ],
                        temperature=0.1,
                        response_format={
                            "type": "json_object",
                        },
                    )
                )
            )
        )

        output_text = self._extract_content(
            completion
        )

        if not output_text.strip():
            raise GroqParseError(
                "Groq returned empty people extraction output"
            )

        output_text = (
            self._strip_json_fences(
                output_text
            )
        )

        try:
            return (
                GroqPeopleExtraction
                .model_validate_json(
                    output_text
                )
            )

        except Exception as exc:
            logger.warning(
                "groq_people_parse_failed",
                model=self._model,
                output_length=len(
                    output_text
                ),
                error_type=(
                    type(exc).__name__
                ),
                error=str(exc),
            )

            raise GroqParseError(
                "Groq returned invalid people extraction output"
            ) from exc

    # =========================================================
    # Rate-limited execution
    # =========================================================

    async def _execute_with_rate_limit(
            self,
            operation: Callable[
                [],
                Awaitable[Any],
            ],
    ) -> Any:
        for attempt in range(
                1,
                self._max_rate_limit_attempts
                + 1,
        ):
            await self._rate_limiter.acquire()

            try:
                return await operation()

            except Exception as exc:
                if not self._is_rate_limited(
                        exc
                ):
                    self._raise_provider_error(
                        exc
                    )

                if (
                        attempt
                        >= self._max_rate_limit_attempts
                ):
                    logger.warning(
                        "groq_rate_limit_exhausted",
                        model=self._model,
                        attempts=attempt,
                        error_type=(
                            type(exc).__name__
                        ),
                        error=str(exc),
                    )

                    self._raise_provider_error(
                        exc
                    )

                retry_seconds = (
                    self._extract_retry_seconds(
                        exc
                    )
                )

                jitter = random.uniform(
                    0.5,
                    2.0,
                )

                wait_seconds = (
                        retry_seconds
                        + jitter
                )

                cooldown_accepted = (
                    await self._rate_limiter.cooldown(
                        wait_seconds
                    )
                )

                if not cooldown_accepted:
                    logger.warning(
                        "groq_rate_limit_wait_too_long",
                        model=self._model,
                        attempt=attempt,
                        max_attempts=(
                            self._max_rate_limit_attempts
                        ),
                        retry_after_seconds=(
                            retry_seconds
                        ),
                        wait_seconds=round(
                            wait_seconds,
                            2,
                        ),
                        error_type=(
                            type(exc).__name__
                        ),
                    )

                    raise GroqRateLimitedError(
                        "Groq requested a rate-limit "
                        "cooldown that exceeds the "
                        "configured maximum: "
                        f"{wait_seconds:.1f}s"
                    ) from exc

                logger.warning(
                    "groq_rate_limited_retry",
                    model=self._model,
                    attempt=attempt,
                    max_attempts=(
                        self._max_rate_limit_attempts
                    ),
                    retry_after_seconds=(
                        retry_seconds
                    ),
                    wait_seconds=round(
                        wait_seconds,
                        2,
                    ),
                    error_type=(
                        type(exc).__name__
                    ),
                )

        raise GroqProviderError(
            "Groq request failed unexpectedly"
        )

    # =========================================================
    # Response helpers
    # =========================================================

    @staticmethod
    def _extract_content(
        completion: Any,
    ) -> str:
        choices = getattr(
            completion,
            "choices",
            None,
        )

        if not choices:
            return ""

        message = getattr(
            choices[0],
            "message",
            None,
        )

        if message is None:
            return ""

        content = getattr(
            message,
            "content",
            None,
        )

        return content or ""

    @staticmethod
    def _strip_json_fences(
        text: str,
    ) -> str:
        stripped = text.strip()

        if stripped.startswith(
            "```json"
        ):
            stripped = stripped[
                len("```json"):
            ]

        elif stripped.startswith(
            "```"
        ):
            stripped = stripped[
                len("```"):
            ]

        stripped = stripped.removesuffix("```")

        return stripped.strip()

    # =========================================================
    # Error classification
    # =========================================================

    @staticmethod
    def _is_rate_limited(
        exc: Exception,
    ) -> bool:
        status_code = getattr(
            exc,
            "status_code",
            None,
        )

        if status_code == 429:
            return True

        message = str(
            exc
        ).casefold()

        return (
            "429" in message
            or "rate limit" in message
            or "rate_limit" in message
            or "too many requests" in message
            or "quota" in message
        )

    @classmethod
    def _extract_retry_seconds(
        cls,
        exc: Exception,
    ) -> float:
        header_value = (
            cls._extract_retry_after_header(
                exc
            )
        )

        if header_value is not None:
            return header_value

        message = str(
            exc
        )

        patterns = (
            (
                r"retry[\s_-]*after[^0-9]*"
                r"([0-9]+(?:\.[0-9]+)?)"
            ),
            (
                r"retry\s+in\s+"
                r"([0-9]+(?:\.[0-9]+)?)"
                r"\s*s"
            ),
        )

        for pattern in patterns:
            match = re.search(
                pattern,
                message,
                flags=re.IGNORECASE,
            )

            if match is None:
                continue

            try:
                return max(
                    1.0,
                    float(
                        match.group(1)
                    ),
                )

            except (
                TypeError,
                ValueError,
            ):
                continue

        return 60.0

    @staticmethod
    def _extract_retry_after_header(
        exc: Exception,
    ) -> float | None:
        response = getattr(
            exc,
            "response",
            None,
        )

        if response is None:
            return None

        headers = getattr(
            response,
            "headers",
            None,
        )

        if headers is None:
            return None

        value = headers.get(
            "retry-after"
        )

        if value is None:
            return None

        try:
            return max(
                1.0,
                float(value),
            )

        except (
            TypeError,
            ValueError,
        ):
            return None

    # =========================================================
    # Provider errors
    # =========================================================

    @staticmethod
    def _raise_provider_error(
        exc: Exception,
    ) -> None:
        message = str(
            exc
        )

        status_code = getattr(
            exc,
            "status_code",
            None,
        )

        normalized = (
            message.casefold()
        )

        if (
            status_code == 429
            or "429" in normalized
            or "rate limit" in normalized
            or "rate_limit" in normalized
            or "too many requests"
            in normalized
            or "quota" in normalized
        ):
            raise GroqRateLimitedError(
                message
            ) from exc

        raise GroqProviderError(
            message
        ) from exc