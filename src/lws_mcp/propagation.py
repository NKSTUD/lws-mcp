"""DNS propagation check: what is saved versus what the domain's nameservers and public resolvers answer.

The domain's own (authoritative) nameservers answer from the zone, with no cache. Public resolvers answer with
what most users see, and each may keep an older answer until its TTL runs out: one resolver alone can lag well
behind a change, so several are asked.
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, field

import dns.asyncquery
import dns.asyncresolver
import dns.exception
import dns.flags
import dns.message
import dns.name
import dns.rcode
import dns.rdatatype
import httpx

# Asked over HTTPS (RFC 8484), so this part works even where outgoing port 53 is blocked.
# Quad9 only speaks HTTP/2 there; Cloudflare is reached by IP, which also skips one lookup.
PUBLIC_RESOLVERS = {
    "Cloudflare": "https://1.1.1.1/dns-query",
    "Google": "https://dns.google/dns-query",
    "Quad9": "https://dns.quad9.net/dns-query",
}


@dataclass
class Answer:
    source: str
    values: list[str] = field(default_factory=list)
    ttl: int | None = None
    error: str | None = None
    up_to_date: bool | None = None


def normalize(value: str) -> str:
    """Compare values the way DNS does: case-insensitive, trailing dot and TXT quotes ignored."""
    return value.strip().strip('"').rstrip(".").lower()


def _read(response: dns.message.Message, rdtype: dns.rdatatype.RdataType) -> tuple[list[str], int | None]:
    qname = response.question[0].name
    for rrset in response.answer:
        if rrset.name == qname and rrset.rdtype == rdtype:
            if rdtype == dns.rdatatype.TXT:
                values = [b"".join(rdata.strings).decode(errors="replace") for rdata in rrset]
            else:
                values = [rdata.to_text() for rdata in rrset]
            return sorted(values), rrset.ttl
    return [], None


async def _ask_nameserver(host: str, address: str, query: dns.message.Message, timeout: float) -> Answer:
    rdtype = query.question[0].rdtype
    try:
        response, _ = await dns.asyncquery.udp_with_fallback(query, address, timeout=timeout)
    except (dns.exception.DNSException, OSError) as exc:
        return Answer(host, error=f"no answer ({exc.__class__.__name__})")
    return Answer(host, *_read(response, rdtype))


async def _ask_resolver(http: httpx.AsyncClient, label: str, url: str, query: dns.message.Message) -> Answer:
    rdtype = query.question[0].rdtype
    try:
        reply = await http.post(
            url,
            content=query.to_wire(),
            headers={"Content-Type": "application/dns-message", "Accept": "application/dns-message"},
        )
        reply.raise_for_status()
        response = dns.message.from_wire(reply.content)
    except (httpx.HTTPError, dns.exception.DNSException) as exc:
        return Answer(label, error=f"no answer ({exc.__class__.__name__})")
    if response.rcode() not in (dns.rcode.NOERROR, dns.rcode.NXDOMAIN):
        return Answer(label, error=dns.rcode.to_text(response.rcode()))
    return Answer(label, *_read(response, rdtype))


async def _nameservers(name: str, timeout: float) -> list[tuple[str, str]]:
    """(host, IPv4 address) of each nameserver of the zone holding `name`; empty if they cannot be found."""
    resolver = dns.asyncresolver.Resolver()
    resolver.lifetime = timeout
    try:
        zone = await dns.asyncresolver.zone_for_name(name, resolver=resolver)
        hosts = sorted(rdata.to_text() for rdata in await resolver.resolve(zone, "NS"))
    except dns.exception.DNSException:
        return []

    async def address(host: str) -> tuple[str, str] | None:
        try:
            answer = await resolver.resolve(host, "A")
        except dns.exception.DNSException:
            return None
        return host.rstrip("."), next(iter(answer)).to_text()

    return [server for server in await asyncio.gather(*(address(host) for host in hosts)) if server]


def summarize(
    name: str,
    rdtype: str,
    saved: list[str] | None,
    nameservers: list[Answer],
    resolvers: list[Answer],
    expected: str | None = None,
) -> dict:
    """Mark every answer up to date or not against the reference, and say in one line where the change stands.

    The reference is, in order: the value the caller expects, the records saved in the LWS zone, or what the
    nameservers agree on.
    """
    if expected is not None:
        wanted = normalize(expected)

        def matches(values: list[str]) -> bool | None:
            return wanted in {normalize(value) for value in values}

    else:
        reference: set[str] | None = None
        if saved is not None:
            reference = {normalize(value) for value in saved}
        else:
            sets = {frozenset(normalize(v) for v in a.values) for a in nameservers if a.error is None}
            reference = set(sets.pop()) if len(sets) == 1 else None

        def matches(values: list[str]) -> bool | None:
            # Nothing to compare with (domain not on the account, nameservers unreachable): unknown, not stale.
            return None if reference is None else {normalize(value) for value in values} == reference

    for answer in (*nameservers, *resolvers):
        answer.up_to_date = None if answer.error else matches(answer.values)

    parts = []
    if saved is not None:
        if expected is None:
            parts.append(f"saved in the LWS zone: {', '.join(saved)}" if saved else "not in the LWS zone")
        else:
            parts.append("saved in the LWS zone" if matches(saved) else "NOT saved in the LWS zone")
    reachable = [a for a in nameservers if a.error is None]
    if reachable:
        parts.append(f"nameservers up to date {sum(bool(a.up_to_date) for a in reachable)}/{len(reachable)}")
    elif nameservers:
        parts.append("nameservers not reachable from here")
    asked = [a for a in resolvers if a.error is None]
    if any(a.up_to_date is not None for a in asked):
        parts.append(f"public resolvers up to date {sum(bool(a.up_to_date) for a in asked)}/{len(asked)}")
    else:
        answers = sorted({", ".join(a.values) or "nothing" for a in asked})
        parts.append(f"public resolvers answer {' | '.join(answers) or 'nothing (unreachable)'}")
    lagging = [a.ttl for a in asked if a.up_to_date is False and a.ttl]
    # Cached answers only matter once the change has reached the nameservers.
    if lagging and not (reachable and not any(a.up_to_date for a in reachable)):
        parts.append(f"stale answers can last up to {max(lagging)} s more")

    return {
        "message": f"{rdtype} {name}: " + "; ".join(parts),
        "data": {
            "saved_in_zone": saved,
            "nameservers": [asdict(a) for a in nameservers],
            "public_resolvers": [asdict(a) for a in resolvers],
        },
    }


async def check(
    name: str, rdtype: str, *, saved: list[str] | None = None, expected: str | None = None, timeout: float = 5.0
) -> dict:
    fqdn = name.strip().rstrip(".") + "."
    query = dns.message.make_query(fqdn, dns.rdatatype.from_text(rdtype))
    direct = dns.message.make_query(fqdn, dns.rdatatype.from_text(rdtype))
    direct.flags &= ~dns.flags.RD  # nameservers answer from their own zone

    async with httpx.AsyncClient(timeout=timeout, http2=True) as http:
        servers = await _nameservers(fqdn, timeout)
        nameservers, resolvers = await asyncio.gather(
            asyncio.gather(*(_ask_nameserver(host, ip, direct, timeout) for host, ip in servers)),
            asyncio.gather(*(_ask_resolver(http, label, url, query) for label, url in PUBLIC_RESOLVERS.items())),
        )
    return summarize(fqdn.rstrip("."), rdtype, saved, list(nameservers), list(resolvers), expected)
