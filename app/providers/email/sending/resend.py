# app/providers/email/sending/resend.py

from __future__ import annotations

from typing import Any

import httpx

from app.models.schemas.email_send import (
    EmailSendRequest,
    EmailSendResult,
)


class ResendEmailSendingProvider:
    """
    Email sending provider backed by the Resend API.

    This provider is responsible only for communicating with Resend
    and converting its response into Autlead's email sending schema.

    Persistence, outreach decisions, and delivery-event processing
    belong outside the provider.
    """

    provider_name = "resend"

    def __init__(
        self,
        *,
        api_key: str,
        api_url: str = "https://api.resend.com",
        timeout: float = 30.0,
    ) -> None:
        if not api_key:
            raise ValueError(
                "Resend API key is required."
            )

        self._api_key = api_key
        self._api_url = api_url.rstrip("/")
        self._timeout = timeout

    async def send(
        self,
        request: EmailSendRequest,
    ) -> EmailSendResult:
        """
        Send an email through Resend.

        A successful result means Resend accepted the send request.
        It does not necessarily mean the recipient mail server
        delivered the message.
        """

        payload: dict[str, Any] = {
            "from": str(request.from_email),
            "to": [str(request.to_email)],
            "subject": request.subject,
        }

        if request.html is not None:
            payload["html"] = request.html

        if request.text is not None:
            payload["text"] = request.text

        if request.reply_to is not None:
            payload["reply_to"] = str(
                request.reply_to
            )

        headers = {
            "Authorization": (
                f"Bearer {self._api_key}"
            ),
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(
                base_url=self._api_url,
                timeout=self._timeout,
                headers=headers,
            ) as client:
                response = await client.post(
                    "/emails",
                    json=payload,
                )

                response.raise_for_status()

        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                self._format_http_error(exc)
            ) from exc

        except httpx.TimeoutException as exc:
            raise RuntimeError(
                "Resend request timed out."
            ) from exc

        except httpx.RequestError as exc:
            raise RuntimeError(
                f"Could not communicate with Resend: {exc}"
            ) from exc

        data = response.json()

        message_id = data.get("id")

        if not message_id:
            raise RuntimeError(
                "Resend returned a successful response "
                "without a message ID."
            )

        return EmailSendResult(
            provider_name=self.provider_name,
            provider_message_id=message_id,
        )

    @staticmethod
    def _format_http_error(
        exc: httpx.HTTPStatusError,
    ) -> str:
        response = exc.response

        try:
            data = response.json()
        except ValueError:
            return (
                "Resend request failed with HTTP "
                f"{response.status_code}: "
                f"{response.text}"
            )

        message = (
            data.get("message")
            or data.get("error")
            or response.text
        )

        return (
            "Resend request failed with HTTP "
            f"{response.status_code}: {message}"
        )