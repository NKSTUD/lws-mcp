"""Builds the MCP server and runs it over stdio."""

from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from mcp.server.mcpserver import MCPServer

from . import __version__
from .client import LwsClient
from .config import ConfigError, Settings
from .tools import MODULES

INSTRUCTIONS = """\
Manage domains, DNS zones, hosting and the account of an LWS (lws.fr) customer.
- DNS: read the zone with get_dns_zone before changing it; record ids come from there.
  After a change, check_dns_propagation shows what the internet sees (propagation can take hours).
- Actions marked "deferred" run in the background: follow them with list_pending_requests.
- Tools marked PAID debit the prepaid account: always confirm the price with the user first.
"""


def build_server(settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> MCPServer:
    client = LwsClient(settings, transport=transport)

    @asynccontextmanager
    async def lifespan(_: MCPServer) -> AsyncIterator[None]:
        try:
            yield
        finally:
            await client.aclose()

    server = MCPServer(
        name="lws",
        title="LWS",
        instructions=INSTRUCTIONS,
        website_url="https://github.com/NKSTUD/lws-mcp",
        version=__version__,
        lifespan=lifespan,
    )
    for module in MODULES:
        module.register(server, client, settings)
    return server


def main() -> None:
    try:
        settings = Settings.from_env()
    except ConfigError as exc:
        sys.exit(f"lws-mcp: {exc} See https://github.com/NKSTUD/lws-mcp#configuration")
    build_server(settings).run("stdio")


if __name__ == "__main__":
    main()
