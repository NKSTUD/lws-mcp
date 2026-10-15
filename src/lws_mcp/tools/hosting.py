"""Hosting: list, details, prices, auto-renewal, and the two paid actions (buy, renew)."""

from __future__ import annotations

from typing import Annotated, Literal

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from ..client import LwsClient
from ..config import Settings
from ._common import READ, WRITE, Domain, Result

# Paid actions debit the prepaid account: never idempotent, always worth a confirmation.
PAID = ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=True)

Hosting = Annotated[str, Field(min_length=3, description="Domain name the hosting is attached to")]


def register(server: MCPServer, client: LwsClient, settings: Settings) -> None:
    @server.tool(annotations=READ)
    async def list_hostings() -> Result:
        """List every domain and hosting on the account, with expiry dates, nameservers and auto-renewal."""
        return await client.request("GET", "/hosting/0/list")

    @server.tool(annotations=READ)
    async def get_hosting(hosting: Hosting) -> Result:
        """Get a hosting's package, purchase and expiry dates, nameservers and auto-renewal settings."""
        return await client.request("GET", f"/hosting/{hosting}")

    @server.tool(annotations=READ)
    async def list_hosting_prices() -> Result:
        """List every hosting package with its monthly price in EUR."""
        return await client.request("GET", "/hosting/0/priceall")

    @server.tool(annotations=READ)
    async def get_renewal_prices(hosting: Hosting) -> Result:
        """Get the renewal price (hosting, domain, options) and the expiry status. Check it before renew_hosting."""
        return await client.request("GET", f"/hosting/{hosting}/pricerenew")

    if not settings.allows_writes:
        return

    @server.tool(annotations=WRITE)
    async def set_auto_renew(hosting: Hosting, enabled: bool) -> Result:
        """Turn automatic renewal of a hosting (and its domain, if bought at LWS) on or off."""
        return await client.request("PUT", f"/hosting/{hosting}/autorenew", json={"enable": enabled})

    if not settings.allows_purchases:
        return

    @server.tool(annotations=PAID)
    async def buy_hosting(
        domain: Domain,
        package: Annotated[
            str, Field(description="Package name from list_hosting_prices, or 'domaine' to buy only the domain")
        ],
        owner: Annotated[int, Field(description="LWS contact ID that will own it (see list_contacts)")],
        type: Annotated[
            Literal["buy", "host", "transfer"],
            Field(description="buy: hosting + new domain; host: hosting for a domain you own; transfer: move in"),
        ] = "buy",
        period: Annotated[int, Field(ge=1, description="Duration in months")] = 12,
    ) -> Result:
        """PAID: buy a domain and/or hosting, debited from the prepaid account (deferred).

        Confirm the package, period and price with the user before calling this.
        """
        body = {"package": package, "domain": domain, "owner": owner, "type": type, "period": period}
        return await client.request("POST", "/hosting", json=body)

    @server.tool(annotations=PAID)
    async def renew_hosting(hosting: Hosting) -> Result:
        """PAID: renew a hosting and its domain for another period, debited from the prepaid account (deferred).

        Show the price from get_renewal_prices to the user and get their confirmation first.
        """
        return await client.request("POST", f"/hosting/{hosting}/renew")
