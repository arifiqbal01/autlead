# app/models/schemas/website_pages.py

from __future__ import annotations

from pydantic import BaseModel, HttpUrl


class WebsitePageCandidate(BaseModel):
    url: HttpUrl
    path: str
    anchor_text: str | None = None