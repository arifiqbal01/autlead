from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class DiscoveryQuery(BaseModel):
    query: str = Field(
        min_length=1,
    )

    location: str | None = None

    limit: int | None = Field(
        default=None,
        ge=1,
    )


class BusinessRecord(BaseModel):
    name: str = Field(
        min_length=1,
    )

    website: str | None = None
    domain: str | None = None
    phone: str | None = None
    country: str | None = None
    city: str | None = None
    address: str | None = None
    category: str | None = None

    source_name: str = Field(
        min_length=1,
    )
    source_type: str = Field(
        min_length=1,
    )
    provider_name: str = Field(
        min_length=1,
    )

    external_id: str | None = None

    raw_data: dict[str, Any] | None = None

    collected_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )


class AcquisitionResult(BaseModel):
    found: int = 0
    new: int = 0
    duplicates: int = 0
    stored: int = 0