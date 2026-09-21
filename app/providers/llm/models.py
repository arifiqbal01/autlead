# app/providers/llm/models.py

from __future__ import annotations

from pydantic import BaseModel


class LLMRequest(BaseModel):
    prompt: str


class LLMResponse(BaseModel):
    text: str
    provider: str
    model: str