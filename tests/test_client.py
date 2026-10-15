import httpx
import pytest

from lws_mcp.client import LwsApiError, LwsClient
from lws_mcp.config import Settings

from .conftest import envelope

pytestmark = pytest.mark.anyio


def client_for(fake, **overrides) -> LwsClient:
    return LwsClient(Settings(login="123456", api_key="secret-key", **overrides), transport=fake.transport())


async def test_sends_auth_headers_and_returns_payload(fake):
    fake.handler = lambda request: envelope(42.5, info="Remaining credits fetched")
    result = await client_for(fake).request("GET", "/contact/0/credit")

    assert result == {"message": "Remaining credits fetched", "data": 42.5}
    assert str(fake.last.url) == "https://api.lws.net/v1/contact/0/credit"
    assert fake.last.headers["X-Auth-Login"] == "123456"
    assert fake.last.headers["X-Auth-Pass"] == "secret-key"
    assert "X-Test-Mode" not in fake.last.headers


async def test_test_mode_header(fake):
    await client_for(fake, test_mode=True).request("GET", "/contact/0/credit")
    assert fake.last.headers["X-Test-Mode"] == "true"


async def test_delete_carries_a_json_body(fake):
    await client_for(fake).request("DELETE", "/domain/example.fr/zdns", json={"id": 7})
    assert fake.last.method == "DELETE"
    assert fake.last_json == {"id": 7}


async def test_drops_empty_query_parameters(fake):
    await client_for(fake).request("GET", "/requests", params={"objet": "domain", "valeur": None})
    assert dict(fake.last.url.params) == {"objet": "domain"}


async def test_application_error_code_raises_even_with_http_200(fake):
    fake.handler = lambda request: envelope(code=314, info="Provided domain has not been found on your account.")
    with pytest.raises(LwsApiError, match="314: Provided domain") as error:
        await client_for(fake).request("GET", "/domain/other.fr")
    assert error.value.code == 314


async def test_http_error_with_envelope(fake):
    fake.handler = lambda request: httpx.Response(401, json={"code": 401, "info": "Unauthorized access"})
    with pytest.raises(LwsApiError, match="401: Unauthorized access"):
        await client_for(fake).request("GET", "/contact/0/credit")


async def test_access_refusal_is_readable(fake):
    refusal = {"code": 400, "info": {"status": "KO", "error": "bad source 192.0.2.7"}}
    fake.handler = lambda request: httpx.Response(400, json=refusal)
    with pytest.raises(LwsApiError, match=r"400: bad source 192\.0\.2\.7 \(this IP address is not allowed"):
        await client_for(fake).request("GET", "/contact/0/credit")


async def test_validation_details_are_kept(fake):
    fake.handler = lambda request: envelope({"ttl": "Invalid field"}, code=400, info="Invalid input", status=400)
    with pytest.raises(LwsApiError, match="ttl"):
        await client_for(fake).request("POST", "/domain/example.fr/zdns", json={})


async def test_non_json_answer(fake):
    fake.handler = lambda request: httpx.Response(502, text="Bad gateway")
    with pytest.raises(LwsApiError, match="502: Bad gateway"):
        await client_for(fake).request("GET", "/hosting/0/list")


async def test_network_failure_never_leaks_the_key(fake):
    def fail(request):
        raise httpx.ConnectError("connection refused", request=request)

    fake.handler = fail
    with pytest.raises(LwsApiError, match="could not reach the API") as error:
        await client_for(fake).request("GET", "/hosting/0/list")
    assert "secret-key" not in str(error.value)
