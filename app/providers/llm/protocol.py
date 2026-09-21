# app/providers/llm/protocol.py

from __future__ import annotations

from typing import Protocol

from .models import LLMRequest, LLMResponse


class LLMProvider(Protocol):
    async def generate(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        ...