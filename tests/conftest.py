from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import httpx
import pytest

from lws_mcp.config import Settings
from lws_mcp.server import build_server


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@dataclass
class FakeLws:
    """Records the requests sent to the LWS API and answers them from a handler."""

    handler: Callable[[httpx.Request], httpx.Response] = lambda request: httpx.Response(
        200, json={"code": 200, "info": "OK", "data": None}
    )
    requests: list[httpx.Request] = field(default_factory=list)

    def transport(self) -> httpx.MockTransport:
        def handle(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            return self.handler(request)

        return httpx.MockTransport(handle)

    @property
    def last(self) -> httpx.Request:
        return self.requests[-1]

    @property
    def last_json(self) -> Any:
        return json.loads(self.last.content) if self.last.content else None


@pytest.fixture
def fake() -> FakeLws:
    return FakeLws()


@pytest.fixture
def make_server(fake: FakeLws):
    def make(**overrides: Any):
        settings = Settings(login="123456", api_key="secret-key", **overrides)
        return build_server(settings, transport=fake.transport())

    return make


def envelope(data: Any = None, code: int = 200, info: str = "OK", status: int = 200) -> httpx.Response:
    return httpx.Response(status, json={"code": code, "info": info, "data": data})
