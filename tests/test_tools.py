import json

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from lws_mcp.tools.dns import relative_name

from .conftest import envelope

pytestmark = pytest.mark.anyio

READ_TOOLS = {
    "get_dns_zone",
    "check_dns_propagation",
    "get_domain",
    "check_domain_availability",
    "list_tlds",
    "list_hostings",
    "get_hosting",
    "list_hosting_prices",
    "get_renewal_prices",
    "get_account_balance",
    "get_purchase_history",
    "list_contacts",
    "get_contact",
    "list_requests",
    "list_pending_requests",
}
WRITE_TOOLS = {
    "add_dns_record",
    "update_dns_record",
    "delete_dns_record",
    "update_nameservers",
    "set_transfer_protection",
    "request_transfer_authcode",
    "create_domain_redirect",
    "delete_domain_redirect",
    "set_auto_renew",
    "create_contact",
    "update_contact",
}
PAID_TOOLS = {"buy_hosting", "renew_hosting"}
TEST_TOOLS = {"add_test_credit_to_contact", "add_test_credit_to_account"}


async def tool_names(server) -> set[str]:
    return {tool.name for tool in await server.list_tools()}


async def call(server, tool, /, **arguments):
    result = await server.call_tool(tool, arguments)
    assert not result.is_error, result.content
    return result.structured_content


async def test_default_exposes_reads_and_writes_but_no_purchase(make_server):
    assert await tool_names(make_server()) == READ_TOOLS | WRITE_TOOLS


async def test_read_only_hides_every_write(make_server):
    assert await tool_names(make_server(read_only=True, enable_purchases=True)) == READ_TOOLS


async def test_purchases_are_opt_in(make_server):
    assert await tool_names(make_server(enable_purchases=True)) == READ_TOOLS | WRITE_TOOLS | PAID_TOOLS


async def test_credit_tools_exist_only_in_test_mode(make_server):
    assert await tool_names(make_server(test_mode=True)) == READ_TOOLS | WRITE_TOOLS | TEST_TOOLS


async def test_every_tool_tells_clients_whether_it_writes(make_server):
    for tool in await make_server(enable_purchases=True, test_mode=True).list_tools():
        assert tool.annotations is not None, tool.name
        assert tool.annotations.read_only_hint == (tool.name in READ_TOOLS), tool.name
        assert tool.description, tool.name


@pytest.mark.parametrize(
    ("name", "expected"),
    [("www", "www"), ("@", "@"), ("example.fr", "@"), ("_DMARC.Example.fr.", "_dmarc"), ("a.b.example.fr", "a.b")],
)
def test_relative_name(name, expected):
    assert relative_name(name, "example.fr") == expected


async def test_add_record_shortens_full_names(make_server, fake):
    await call(make_server(), "add_dns_record", domain="Example.FR", type="CNAME", name="em.example.fr", value="x.io")
    post = fake.requests[0]
    assert (post.method, post.url.path) == ("POST", "/v1/domain/example.fr/zdns")
    assert json.loads(post.content) == {"type": "CNAME", "name": "em", "value": "x.io", "ttl": 3600}


async def test_update_returns_the_new_id(make_server, fake):
    # LWS replaces the record under a new id but answers with the old one.
    def handler(request):
        if request.method == "PUT":
            return envelope({"id": 5, "type": "TXT", "name": "t", "value": "v2", "ttl": 900}, info="Updated record")
        a_record = {"id": 9, "type": "A", "name": "t", "value": "v2"}
        txt_record = {"id": 6, "type": "TXT", "name": "t", "value": "v2"}
        return envelope([a_record, txt_record])

    fake.handler = handler
    result = await call(make_server(), "update_dns_record", domain="example.fr", id=5, type="TXT", name="t", value="v2")
    assert result["data"]["id"] == 6


async def test_add_returns_the_id_lws_omits(make_server, fake):
    def handler(request):
        if request.method == "POST":
            return envelope({"type": "CNAME", "name": "em", "value": "x.io", "ttl": 3600})
        return envelope([{"id": 3, "type": "CNAME", "name": "em", "value": "x.io.", "ttl": 3600}])

    fake.handler = handler
    result = await call(make_server(), "add_dns_record", domain="example.fr", type="CNAME", name="em", value="x.io")
    assert result["data"]["id"] == 3


async def test_zone_can_be_filtered(make_server, fake):
    records = [
        {"id": 1, "type": "A", "name": "@", "value": "192.0.2.1", "ttl": 3600},
        {"id": 2, "type": "CNAME", "name": "www", "value": "example.fr.", "ttl": 3600},
        {"id": 3, "type": "TXT", "name": "@", "value": "v=spf1 -all", "ttl": 3600},
    ]
    fake.handler = lambda request: envelope(records, info="Fetched DNS Zone")
    result = await call(make_server(), "get_dns_zone", domain="example.fr", name="example.fr", type="TXT")
    assert [record["id"] for record in result["data"]] == [3]


async def test_delete_record_sends_the_id(make_server, fake):
    await call(make_server(), "delete_dns_record", domain="example.fr", id=234851)
    assert (fake.last.method, fake.last_json) == ("DELETE", {"id": 234851})


async def test_invalid_ttl_is_rejected_before_any_call(make_server, fake):
    with pytest.raises(ToolError):
        await make_server().call_tool(
            "add_dns_record", {"domain": "example.fr", "type": "A", "name": "@", "value": "192.0.2.1", "ttl": 60}
        )
    assert fake.requests == []


async def test_invalid_domain_is_rejected(make_server, fake):
    with pytest.raises(ToolError):
        await make_server().call_tool("get_domain", {"domain": "not a domain"})
    assert fake.requests == []


async def test_api_errors_reach_the_model(make_server, fake):
    fake.handler = lambda request: envelope(code=314, info="Provided domain has not been found on your account.")
    with pytest.raises(ToolError, match="314"):
        await make_server().call_tool("get_domain", {"domain": "example.fr"})


async def test_update_contact_sends_only_given_fields(make_server, fake):
    await call(make_server(), "update_contact", contact=367228, city="Paris", country="fr")
    assert fake.last.method == "PUT"
    assert fake.last_json == {"city": "Paris", "country": "FR"}


async def test_list_requests_maps_parameter_names(make_server, fake):
    await call(make_server(), "list_requests", endpoint="domain", value="example.fr")
    assert dict(fake.last.url.params) == {"objet": "domain", "valeur": "example.fr"}


async def test_list_tlds_filter(make_server, fake):
    fake.handler = lambda request: envelope([{"tld": ".fr"}, {"tld": ".com"}])
    result = await call(make_server(), "list_tlds", tld="com")
    assert result["data"] == [{"tld": ".com"}]
