"""Types and tool hints shared by every tool module."""

from __future__ import annotations

from typing import Annotated, Any

from mcp.types import ToolAnnotations
from pydantic import AfterValidator, Field

Result = dict[str, Any]

# Labels of 1-63 characters that neither start nor end with a hyphen (pydantic regexes have no look-arounds).
_DOMAIN_PATTERN = r"^([A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}\.?$"


def _normalize_domain(value: str) -> str:
    return value.strip().rstrip(".").lower()


Domain = Annotated[
    str,
    Field(pattern=_DOMAIN_PATTERN, description="Domain name managed by the LWS account, e.g. example.fr"),
    AfterValidator(_normalize_domain),
]

# Hints shown to MCP clients so they can decide when to ask the user before running a tool.
READ = ToolAnnotations(read_only_hint=True, open_world_hint=True)
WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=True)
DESTRUCTIVE = ToolAnnotations(read_only_hint=False, destructive_hint=True, open_world_hint=True)
