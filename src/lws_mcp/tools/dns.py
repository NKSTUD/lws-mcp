"""DNS zone records: list, add, update, delete, and check that a change is live."""

from __future__ import annotations

from typing import Annotated, Literal

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from .. import propagation
from ..client import LwsApiError, LwsClient
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


def relative_name(name: str, domain: str) -> str:
    """Turn 'www.example.fr.' into 'www' and 'example.fr' into '@', as the LWS zone expects."""
    name = name.strip().rstrip(".").lower()
    if name in ("", "@", domain):
        return "@"
    suffix = "." + domain
    return name.removesuffix(suffix)


def _same_value(a: object, b: object) -> bool:
    return str(a).strip().strip('"').rstrip(".").lower() == str(b).strip().strip('"').rstrip(".").lower()


def register(server: MCPServer, client: LwsClient, settings: Settings) -> None:
    async def saved_record(result: Result, domain: str, body: dict) -> Result:
        """Return the record as stored, with its real id.

        LWS answers an add without the id, and an update with the old id although it replaces the record
        under a new one; reading the zone back gives the model an id it can use for the next call.
        """
        zone = (await client.request("GET", f"/domain/{domain}/zdns"))["data"] or []
        matches = [
            record
            for record in zone
            if str(record.get("type", "")).upper() == body["type"]
            and relative_name(str(record.get("name", "")), domain) == body["name"]
            and _same_value(record.get("value", ""), body["value"])
        ]
        if matches:
            result["data"] = max(matches, key=lambda record: int(record.get("id") or 0))
        return result

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
        expected: Annotated[
            str | None, Field(description="Value you expect to see; by default, what is saved in the LWS zone")
        ] = None,
    ) -> Result:
        """Check whether a DNS change is live: what is saved in the LWS zone, what the domain's nameservers answer,
        and what three public resolvers (Cloudflare, Google, Quad9) answer.

        Public resolvers can keep an old answer until its TTL expires, so they may disagree for a while after a
        change; the answer says how long a stale one can last.
        """
        query_type = "TXT" if type == "SPF" else type
        try:
            saved = await saved_values(name, query_type)
            note = None
        except LwsApiError as exc:  # still worth checking the DNS side
            saved, note = None, f"LWS zone not read ({exc})"
        timeout = min(settings.timeout, 5)
        result = await propagation.check(name, query_type, saved=saved, expected=expected, timeout=timeout)
        if note:
            result["message"] += f"; {note}"
        return result

    async def saved_values(name: str, type: str) -> list[str] | None:
        """Values saved in the LWS zone for this name, or None when the domain is not on the account."""
        fqdn = name.strip().rstrip(".").lower()
        hostings = (await client.request("GET", "/hosting/0/list"))["data"] or []
        domains = [str(h.get("domain", "")).lower() for h in hostings]
        domain = max((d for d in domains if d and (fqdn == d or fqdn.endswith("." + d))), key=len, default=None)
        if domain is None:
            return None
        zone = (await client.request("GET", f"/domain/{domain}/zdns"))["data"] or []
        wanted = relative_name(fqdn, domain)
        return sorted(
            str(record.get("value", ""))
            for record in zone
            if str(record.get("type", "")).upper() == type
            and relative_name(str(record.get("name", "")), domain) == wanted
        )

    if not settings.allows_writes:
        return

    @server.tool(annotations=WRITE)
    async def add_dns_record(
        domain: Domain, type: RecordType, name: RecordName, value: RecordValue, ttl: RecordTtl = 3600
    ) -> Result:
        """Add a record to a domain's DNS zone. Propagation can take up to a few hours."""
        body = {"type": type, "name": relative_name(name, domain), "value": value, "ttl": ttl}
        result = await client.request("POST", f"/domain/{domain}/zdns", json=body)
        return await saved_record(result, domain, body)

    @server.tool(annotations=WRITE)
    async def update_dns_record(
        domain: Domain,
        id: RecordId,
        type: RecordType,
        name: RecordName,
        value: RecordValue,
        ttl: RecordTtl = 3600,
    ) -> Result:
        """Replace an existing DNS record. Every field is required; LWS adds the record if the id does not exist.

        The record gets a new id: use the one returned here for any later change.
        """
        body = {"id": id, "type": type, "name": relative_name(name, domain), "value": value, "ttl": ttl}
        result = await client.request("PUT", f"/domain/{domain}/zdns", json=body)
        return await saved_record(result, domain, body)

    @server.tool(annotations=DESTRUCTIVE)
    async def delete_dns_record(domain: Domain, id: RecordId) -> Result:
        """Delete a DNS record. Check the id with get_dns_zone first: a wrong record can take a site or mail down."""
        return await client.request("DELETE", f"/domain/{domain}/zdns", json={"id": id})
