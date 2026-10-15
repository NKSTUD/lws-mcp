"""DNS zone records: list, add, update, delete, and check what the public internet sees."""

from __future__ import annotations

from typing import Annotated, Literal

import httpx
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from ..client import LwsClient
from ..config import Settings
from ._common import DESTRUCTIVE, READ, WRITE, Domain, Result

RecordType = Literal["A", "AAAA", "CNAME", "ANAME", "MX", "NS", "TXT", "SRV", "SPF", "CAA"]
Ttl = Literal[900, 1800, 3600, 7200, 21600, 43200, 86400]

RecordId = Annotated[int, Field(description="Record ID, as returned by get_dns_zone")]
RecordName = Annotated[
    str,
    Field(
        min_length=1,
        description=(
            "Record name relative to the domain: '@' for the domain itself, 'www', '_dmarc'... "
            "A full name such as 'www.example.fr' is accepted and shortened automatically."
        ),
    ),
]
RecordValue = Annotated[str, Field(min_length=1, description="Record value: IP address, target host name, text...")]
RecordTtl = Annotated[Ttl, Field(description="Time to live in seconds")]

# Public resolver queried by check_dns_propagation (DNS over HTTPS, JSON format).
DOH_URL = "https://cloudflare-dns.com/dns-query"


def relative_name(name: str, domain: str) -> str:
    """Turn 'www.example.fr.' into 'www' and 'example.fr' into '@', as the LWS zone expects."""
    name = name.strip().rstrip(".").lower()
    if name in ("", "@", domain):
        return "@"
    suffix = "." + domain
    return name.removesuffix(suffix)


def register(server: MCPServer, client: LwsClient, settings: Settings) -> None:
    @server.tool(annotations=READ)
    async def get_dns_zone(
        domain: Domain,
        type: Annotated[RecordType | None, Field(description="Only return records of this type")] = None,
        name: Annotated[str | None, Field(description="Only return records with this name ('@', 'www'...)")] = None,
    ) -> Result:
        """List the DNS records of a domain (id, type, name, value, ttl). Use the ids to update or delete records."""
        result = await client.request("GET", f"/domain/{domain}/zdns")
        records = result["data"] or []
        if type:
            records = [record for record in records if str(record.get("type", "")).upper() == type]
        if name:
            wanted = relative_name(name, domain)
            records = [record for record in records if relative_name(str(record.get("name", "")), domain) == wanted]
        return {"message": result["message"], "data": records}

    @server.tool(annotations=READ)
    async def check_dns_propagation(
        name: Annotated[str, Field(description="Fully qualified name to look up, e.g. _dmarc.example.fr")],
        type: Annotated[RecordType, Field(description="Record type to look up")] = "A",
    ) -> Result:
        """Ask a public resolver (Cloudflare 1.1.1.1) what the internet currently sees for a name.

        Useful after adding or changing a record: changes can take from minutes to a few hours to propagate.
        """
        query_type = "TXT" if type == "SPF" else type
        try:
            async with httpx.AsyncClient(timeout=settings.timeout) as resolver:
                response = await resolver.get(
                    DOH_URL,
                    params={"name": name.strip(), "type": query_type},
                    headers={"Accept": "application/dns-json"},
                )
                response.raise_for_status()
                body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ToolError(f"DNS lookup failed: {exc}") from exc
        answers = [
            {"name": answer.get("name"), "ttl": answer.get("TTL"), "value": answer.get("data")}
            for answer in body.get("Answer") or []
        ]
        found = "found" if answers else "no answer"
        return {"message": f"{query_type} {name}: {found}", "data": answers}

    if not settings.allows_writes:
        return

    @server.tool(annotations=WRITE)
    async def add_dns_record(
        domain: Domain, type: RecordType, name: RecordName, value: RecordValue, ttl: RecordTtl = 3600
    ) -> Result:
        """Add a record to a domain's DNS zone. Propagation can take up to a few hours."""
        body = {"type": type, "name": relative_name(name, domain), "value": value, "ttl": ttl}
        return await client.request("POST", f"/domain/{domain}/zdns", json=body)

    @server.tool(annotations=WRITE)
    async def update_dns_record(
        domain: Domain,
        id: RecordId,
        type: RecordType,
        name: RecordName,
        value: RecordValue,
        ttl: RecordTtl = 3600,
    ) -> Result:
        """Replace an existing DNS record. Every field is required; LWS adds the record if the id does not exist."""
        body = {"id": id, "type": type, "name": relative_name(name, domain), "value": value, "ttl": ttl}
        return await client.request("PUT", f"/domain/{domain}/zdns", json=body)

    @server.tool(annotations=DESTRUCTIVE)
    async def delete_dns_record(domain: Domain, id: RecordId) -> Result:
        """Delete a DNS record. Check the id with get_dns_zone first: a wrong record can take a site or mail down."""
        return await client.request("DELETE", f"/domain/{domain}/zdns", json={"id": id})
