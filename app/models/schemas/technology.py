from __future__ import annotations

from pydantic import BaseModel, Field


class DetectedTechnology(BaseModel):
    name: str
    version: str | None = None
    confidence: int
    categories: list[str] = []
    groups: list[str] = []