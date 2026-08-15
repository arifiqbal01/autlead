from pydantic import BaseModel, Field


class CompanyCandidate(BaseModel):
    name: str = Field(min_length=1)
    normalized_name: str = Field(min_length=1)

    website: str | None = None
    domain: str | None = None
    phone: str | None = None
    country: str | None = None
    city: str | None = None
    address: str | None = None
    category: str | None = None
