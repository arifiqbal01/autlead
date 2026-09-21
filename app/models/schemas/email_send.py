from __future__ import annotations

from pydantic import BaseModel, EmailStr


class EmailSendRequest(BaseModel):
    from_email: EmailStr
    to_email: EmailStr
    subject: str
    html: str | None = None
    text: str | None = None
    reply_to: EmailStr | None = None


class EmailSendResult(BaseModel):
    provider_name: str
    provider_message_id: str