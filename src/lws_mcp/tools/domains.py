"""Domains: information, availability, TLDs, nameservers, transfer protection, redirections."""

from __future__ import annotations

from typing import Annotated, Literal

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from ..client import LwsClient
from ..config import Settings
from ._common import DESTRUCTIVE, READ, WRITE, Domain, Result

Nameserver = Annotated[str, Field(min_length=3, description="Nameserver host name, e.g. ns1.lwsdns.com")]


def register(server: MCPServer, client: LwsClient, settings: Settings) -> None:
    @server.tool(annotations=READ)
    async def get_domain(domain: Domain) -> Result:
        """Get a domain's owner, nameservers and status flags (redemption, hold, transfer lock)."""
        return await client.request("GET", f"/domain/{domain}")

    @server.tool(annotations=READ)
    async def check_domain_availability(domain: Domain) -> Result:
        """Check whether a domain name is free to register (data is true when available)."""
        return await client.request("GET", f"/domain/{domain}/availability")

    @server.tool(annotations=READ)
    async def list_tlds(
        tld: Annotated[str | None, Field(description="Only return this extension, e.g. '.fr' or 'fr'")] = None,
    ) -> Result:
        """List the extensions LWS sells with their purchase, renewal, transfer and restore prices (EUR)."""
        result = await client.request("GET", "/domain/0/tlds")
        if tld:
            wanted = "." + tld.strip().lstrip(".").lower()
            result["data"] = [row for row in result["data"] or [] if str(row.get("tld", "")).lower() == wanted]
        return result

    if not settings.allows_writes:
        return

    @server.tool(annotations=DESTRUCTIVE)
    async def update_nameservers(
        domain: Domain, ns1: Nameserver, ns2: Nameserver, ns3: Nameserver, ns4: Nameserver
    ) -> Result:
        """Replace the four nameservers of a domain (deferred: see list_pending_requests).

        Pointing a domain to other nameservers makes its LWS DNS zone stop answering. All four are required;
        repeat a value when there are fewer than four.
        """
        body = {"ns1": ns1, "ns2": ns2, "ns3": ns3, "ns4": ns4}
        return await client.request("PUT", f"/domain/{domain}/dns", json=body)

    @server.tool(annotations=DESTRUCTIVE)
    async def set_transfer_protection(
        domain: Domain,
        enabled: Annotated[bool, Field(description="true to lock transfers, false to allow them")],
    ) -> Result:
        """Lock or unlock the transfer of a domain to another registrar (deferred)."""
        return await client.request("PUT", f"/domain/{domain}/clientTransferProhibited", json={"status": enabled})

    @server.tool(annotations=DESTRUCTIVE)
    async def request_transfer_authcode(domain: Domain) -> Result:
        """Have the transfer authorization code e-mailed to the domain owner (deferred)."""
        return await client.request("GET", f"/domain/{domain}/authcode")

    @server.tool(annotations=WRITE)
    async def create_domain_redirect(
        domain: Domain,
        url: Annotated[str, Field(pattern=r"^https?://", description="Destination URL")],
        type: Annotated[Literal[301, 302], Field(description="301 permanent, 302 temporary")] = 301,
    ) -> Result:
        """Redirect a whole domain to a URL."""
        return await client.request("POST", f"/domain/{domain}/redirect", json={"type": type, "redirection": url})

    @server.tool(annotations=DESTRUCTIVE)
    async def delete_domain_redirect(domain: Domain) -> Result:
        """Remove a domain's redirection (succeeds even if there was none)."""
        return await client.request("DELETE", f"/domain/{domain}/redirect")
