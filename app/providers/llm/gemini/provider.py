from __future__ import annotations

import asyncio
import random
import re
from collections.abc import Callable
from typing import Any

from google import genai

from app.core.logging import get_logger
from app.models.schemas.people import PersonCandidate
from app.providers.llm.models import (
    LLMRequest,
    LLMResponse,
)

from .errors import (
    GeminiParseError,
    GeminiProviderError,
    GeminiRateLimitedError,
)
from .models import GeminiPeopleExtraction
from app.providers.llm.prompt import build_people_prompt
from .rate_limiter import GeminiRateLimiter


logger = get_logger(__name__)


class GeminiLLMProvider:
    name = "gemini"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        requests_per_minute: int = 4,
        requests_per_day: int = 1450,
        max_rate_limit_attempts: int = 3,
    ) -> None:
        if not api_key.strip():
            raise ValueError(
                "Gemini API key is required"
            )

        if max_rate_limit_attempts < 1:
            raise ValueError(
                "max_rate_limit_attempts must be >= 1"
            )

        self._model = model

        self._client = genai.Client(
            api_key=api_key,
        )

        self._rate_limiter = GeminiRateLimiter(
            requests_per_minute=requests_per_minute,
            requests_per_day=requests_per_day,
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
        interaction = (
            await self._execute_with_rate_limit(
                lambda: (
                    self._client.interactions.create(
                        model=self._model,
                        input=request.prompt,
                    )
                )
            )
        )

        return LLMResponse(
            text=(
                interaction.output_text
                or ""
            ),
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
    ) -> GeminiPeopleExtraction:
        prompt = build_people_prompt(
            company_name=company_name,
            website_url=website_url,
            website_text=website_text,
            candidates=(
                candidates
                or []
            ),
        )

        interaction = (
            await self._execute_with_rate_limit(
                lambda: (
                    self._client.interactions.create(
                        model=self._model,
                        input=prompt,
                        response_format={
                            "type": "text",
                            "mime_type": (
                                "application/json"
                            ),
                            "schema": (
                                GeminiPeopleExtraction
                                .model_json_schema()
                            ),
                        },
                    )
                )
            )
        )

        output_text = (
            interaction.output_text
            or ""
        )

        if not output_text.strip():
            raise GeminiParseError(
                "Gemini returned empty people extraction output"
            )

        try:
            return (
                GeminiPeopleExtraction
                .model_validate_json(
                    output_text
                )
            )

        except Exception as exc:
            logger.warning(
                "gemini_people_parse_failed",
                model=self._model,
                output_length=len(
                    output_text
                ),
                error_type=(
                    type(exc).__name__
                ),
                error=str(exc),
            )

            raise GeminiParseError(
                "Gemini returned invalid people extraction output"
            ) from exc

    # =========================================================
    # Rate-limited execution
    # =========================================================

    async def _execute_with_rate_limit(
        self,
        operation: Callable[
            [],
            Any,
        ],
    ) -> Any:
        """
        Execute one Gemini request.

        Behavior:

        - waits for the local rate limiter
        - executes the synchronous SDK call in a thread
        - retries HTTP 429 / quota errors
        - respects Google's "Please retry in Xs" value
        - applies a small jitter/safety margin
        - shares cooldown through the provider's rate limiter
        - converts final SDK errors into provider errors
        """

        for attempt in range(
            1,
            self._max_rate_limit_attempts
            + 1,
        ):
            await self._rate_limiter.acquire()

            try:
                return await asyncio.to_thread(
                    operation
                )

            except Exception as exc:
                if not self._is_rate_limited(
                    exc
                ):
                    self._raise_provider_error(
                        exc
                    )

                # ---------------------------------------------
                # No retries remaining
                # ---------------------------------------------

                if (
                    attempt
                    >= self._max_rate_limit_attempts
                ):
                    logger.warning(
                        "gemini_rate_limit_exhausted",
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

                # ---------------------------------------------
                # Determine Google's requested cooldown
                # ---------------------------------------------

                retry_seconds = (
                    self._extract_retry_seconds(
                        exc
                    )
                )

                # Add a little margin so we do not retry
                # exactly on the quota boundary.
                jitter = random.uniform(
                    1.0,
                    3.0,
                )

                wait_seconds = (
                    retry_seconds
                    + jitter
                )

                logger.warning(
                    "gemini_rate_limited_retry",
                    model=self._model,
                    attempt=attempt,
                    max_attempts=(
                        self._max_rate_limit_attempts
                    ),
                    retry_after_seconds=(
                        retry_seconds
                    ),
                    wait_seconds=(
                        round(
                            wait_seconds,
                            2,
                        )
                    ),
                    error_type=(
                        type(exc).__name__
                    ),
                )

                # This blocks other requests using the same
                # shared GeminiRateLimiter as well.
                await self._rate_limiter.cooldown(
                    wait_seconds
                )

        # Defensive only. The loop always returns or raises.
        raise GeminiProviderError(
            "Gemini request failed unexpectedly"
        )

    # =========================================================
    # Error classification
    # =========================================================

    @staticmethod
    def _is_rate_limited(
        exc: Exception,
    ) -> bool:
        message = str(
            exc
        ).casefold()

        return (
            "429" in message
            or "resource_exhausted"
            in message
            or "rate limit" in message
            or "quota" in message
            or "too_many_requests" in message
            or "too many requests" in message
        )

    @staticmethod
    def _extract_retry_seconds(
        exc: Exception,
    ) -> float:
        """
        Extract Google's retry delay from messages such as:

            Please retry in 49.596123792s.

        Falls back to 60 seconds when Google does not provide
        a usable delay.
        """

        message = str(
            exc
        )

        match = re.search(
            (
                r"retry\s+in\s+"
                r"([0-9]+(?:\.[0-9]+)?)"
                r"\s*s"
            ),
            message,
            flags=re.IGNORECASE,
        )

        if match is None:
            return 60.0

        try:
            seconds = float(
                match.group(1)
            )

        except (
            TypeError,
            ValueError,
        ):
            return 60.0

        return max(
            1.0,
            seconds,
        )

    @staticmethod
    def _raise_provider_error(
        exc: Exception,
    ) -> None:
        message = str(
            exc
        )

        normalized = (
            message.casefold()
        )

        if (
            "429" in normalized
            or "resource_exhausted"
            in normalized
            or "rate limit" in normalized
            or "quota" in normalized
            or "too_many_requests"
            in normalized
            or "too many requests"
            in normalized
        ):
            raise GeminiRateLimitedError(
                message
            ) from exc

        raise GeminiProviderError(
            message
        ) from exc