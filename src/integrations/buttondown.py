"""Lightweight helper around the Buttondown API."""

from __future__ import annotations

from typing import Any, Dict

import requests

DEFAULT_BASE_URL = "https://api.buttondown.email"


class ButtondownError(RuntimeError):
    """Raised when the Buttondown API returns an error."""


class ButtondownClient:
    """Small wrapper for the Buttondown API endpoints we need."""

    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        if not api_key:
            raise ButtondownError("Buttondown API key is required.")

        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Token {api_key.strip()}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        response = self.session.request(method=method, url=url, timeout=30, **kwargs)

        if response.status_code >= 400:
            raise ButtondownError(
                f"{method} {path} failed with {response.status_code}: {response.text}"
            )

        if not response.content:
            return {}

        try:
            return response.json()
        except ValueError as exc:  # pragma: no cover - defensive
            raise ButtondownError(f"Could not decode response from {path}") from exc

    def create_email(
        self,
        subject: str,
        body: str,
        *,
        preheader: str | None = None,
        newsletter: str | None = None,
        slug: str | None = None,
        publish_at: str | None = None,
        tags: list[str] | None = None,
        extra_payload: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Create a newsletter draft in Buttondown."""
        payload: Dict[str, Any] = {
            "subject": subject,
            "body": body,
            "content_type": "markdown",
            "status": "draft",
        }

        if preheader:
            payload["preheader"] = preheader
        if newsletter:
            payload["newsletter"] = newsletter
        if slug:
            payload["slug"] = slug
        if publish_at:
            payload["publish_at"] = publish_at
        if tags:
            payload["tags"] = tags
        if extra_payload:
            payload.update(extra_payload)

        return self._request("POST", "/v1/emails", json=payload)

    def schedule_email(
        self,
        email_id: str | int,
        publish_at: str,
    ) -> Dict[str, Any]:
        """Schedule a draft email for delivery."""
        return self._request(
            "PATCH",
            f"/v1/emails/{email_id}",
            json={
                "status": "scheduled",
                "publish_at": publish_at,
            },
        )

    def delete_email(self, email_id: str | int) -> None:
        """Delete a draft if needed."""
        self._request("DELETE", f"/v1/emails/{email_id}")
