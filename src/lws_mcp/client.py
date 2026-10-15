"""Thin async client for the LWS Client API (https://api.lws.fr/api-client/lws-client-api)."""

from __future__ import annotations

from typing import Any

import httpx
from mcp.server.mcpserver.exceptions import ToolError

from . import __version__
from .config import Settings

# The API wraps every answer in {"code", "info", "data"}; "code" is its own status, not always the HTTP one
# (314 means "domain not on your account"). 201 means "nothing to do" (already deleted, nothing to update).
_SUCCESS_CODES = {200, 201}


class LwsApiError(ToolError):
    """An error answered by the LWS API.

    Subclassing ToolError lets the MCP server hand the message to the model instead of hiding it as a crash.
    """

    def __init__(self, code: int | None, info: Any, data: Any = None) -> None:
        self.code = code
        self.info = info
        self.data = data
        message = f"LWS API error {code}: {info}" if code is not None else f"LWS API error: {info}"
        if data not in (None, "", [], {}):
            message += f" ({data})"
        super().__init__(message)


class LwsClient:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> None:
        headers = {
            "Accept": "application/json",
            "User-Agent": f"lws-mcp/{__version__}",
            "X-Auth-Login": settings.login,
            "X-Auth-Pass": settings.api_key,
        }
        if settings.test_mode:
            headers["X-Test-Mode"] = "true"
        self._http = httpx.AsyncClient(
            base_url=settings.base_url, headers=headers, timeout=settings.timeout, transport=transport
        )

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call the API and return {"message", "data"}, or raise LwsApiError."""
        if params:
            params = {key: value for key, value in params.items() if value is not None}
        try:
            response = await self._http.request(method, path, json=json, params=params or None)
        except httpx.HTTPError as exc:
            raise LwsApiError(None, f"could not reach the API ({exc.__class__.__name__}: {exc})") from exc

        try:
            body = response.json()
        except ValueError:
            raise LwsApiError(response.status_code, response.text[:300] or response.reason_phrase) from None

        if not isinstance(body, dict):
            raise LwsApiError(response.status_code, "unexpected response format", body)

        code = body.get("code", response.status_code)
        if code not in _SUCCESS_CODES or response.is_error:
            # Authentication failures skip the envelope: {"status": "KO", "error": "bad credentials"}.
            info = body.get("info") or body.get("error") or response.reason_phrase
            raise LwsApiError(code, info, body.get("data"))
        return {"message": body.get("info"), "data": body.get("data")}

    async def aclose(self) -> None:
        await self._http.aclose()
