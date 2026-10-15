"""Deferred requests: nameserver changes, purchases, renewals... are processed in the background."""

from __future__ import annotations

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from ..client import LwsClient
from ..config import Settings
from ._common import READ, Result


def register(server: MCPServer, client: LwsClient, settings: Settings) -> None:
    @server.tool(annotations=READ)
    async def list_requests(
        endpoint: Annotated[str | None, Field(description="Endpoint family, e.g. 'domain' or 'hosting'")] = None,
        value: Annotated[str | None, Field(description="Domain or hosting the request was about")] = None,
        subtype: Annotated[str | None, Field(description="Endpoint subtype, e.g. 'dns'")] = None,
    ) -> Result:
        """Search the requests made through the API. 'retour' stays empty until a deferred request is processed."""
        params = {"objet": endpoint, "valeur": value, "type": subtype}
        return await client.request("GET", "/requests", params=params)

    @server.tool(annotations=READ)
    async def list_pending_requests() -> Result:
        """List the deferred requests that have not been processed yet."""
        return await client.request("GET", "/requests/pending")
