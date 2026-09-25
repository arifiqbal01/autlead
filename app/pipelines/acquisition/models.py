from __future__ import annotations

from pydantic import BaseModel


class AcquisitionResult(BaseModel):
    found: int = 0
    new: int = 0
    duplicates: int = 0
    stored: int = 0