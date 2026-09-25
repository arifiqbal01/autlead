from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AcquisitionPriority(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AcquisitionCountry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=2, max_length=2)
    name: str = Field(min_length=1)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip()

class AcquisitionCity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    grid_bbox: str | None = None
    grid_cell_km: float = Field(
        default=1.0,
        gt=0,
    )
    zoom: int = Field(
        default=16,
        ge=1,
        le=22,
    )

    @field_validator("name")
    @classmethod
    def normalize_name(
        cls,
        value: str,
    ) -> str:
        return value.strip()


class AcquisitionTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    segment: str = Field(min_length=1)
    priority: AcquisitionPriority = AcquisitionPriority.MEDIUM

    keywords: list[str] = Field(min_length=1)
    cities: list[str] = Field(min_length=1)

    @field_validator("segment")
    @classmethod
    def normalize_segment(cls, value: str) -> str:
        return value.strip()

    @field_validator("keywords", "cities")
    @classmethod
    def normalize_string_list(
        cls,
        values: list[str],
    ) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()

        for value in values:
            item = value.strip()

            if not item:
                raise ValueError(
                    "Values cannot be empty."
                )

            key = item.casefold()

            if key in seen:
                continue

            seen.add(key)
            normalized.append(item)

        return normalized


class AcquisitionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(default=1, ge=1)

    name: str = Field(min_length=1)
    country: AcquisitionCountry
    industry: str = Field(min_length=1)

    cities: dict[str, AcquisitionCity] = Field(
        min_length=1,
    )

    targets: list[AcquisitionTarget] = Field(
        min_length=1,
    )

    @field_validator("name", "industry")
    @classmethod
    def normalize_string(
        cls,
        value: str,
    ) -> str:
        return value.strip()