import httpx
import pytest

from lws_mcp import propagation
from lws_mcp.propagation import Answer, normalize, summarize

pytestmark = pytest.mark.anyio


def ns(values, source="ns1"):
    return Answer(source, values, 3600)


def resolver(values, ttl=300, source="Google"):
    return Answer(source, values, ttl)


def test_normalize_ignores_case_dot_and_quotes():
    assert normalize('"V=spf1 -all"') == normalize("v=spf1 -all")
    assert normalize("Target.Example.") == "target.example"


def test_everything_up_to_date():
    result = summarize("a.example.fr", "CNAME", ["t.example."], [ns(["t.example."])], [resolver(["T.example"])])
    assert result["message"] == (
        "CNAME a.example.fr: saved in the LWS zone: t.example.; "
        "nameservers up to date 1/1; public resolvers up to date 1/1"
    )


def test_lagging_resolver_reports_how_long_it_can_last():
    result = summarize("a.example.fr", "A", ["192.0.2.2"], [ns(["192.0.2.2"])], [resolver(["192.0.2.1"], ttl=840)])
    assert "public resolvers up to date 0/1" in result["message"]
    assert "up to 840 s" in result["message"]
    assert result["data"]["public_resolvers"][0]["up_to_date"] is False


def test_no_cache_talk_while_nameservers_are_not_updated():
    result = summarize("a.example.fr", "A", ["192.0.2.2"], [ns(["192.0.2.1"])], [resolver(["192.0.2.1"])])
    assert "nameservers up to date 0/1" in result["message"]
    assert "s more" not in result["message"]


def test_expected_value_is_looked_for_among_several():
    token = "stripe-verification=abc"
    result = summarize("example.fr", "TXT", None, [ns(["v=spf1 -all", token])], [resolver([token])], token)
    assert "nameservers up to date 1/1" in result["message"]
    assert "public resolvers up to date 1/1" in result["message"]


def test_without_reference_answers_are_unknown_not_stale():
    result = summarize("example.fr", "MX", None, [Answer("ns1", error="no answer (Timeout)")], [resolver(["10 mail."])])
    assert result["data"]["public_resolvers"][0]["up_to_date"] is None
    assert "nameservers not reachable from here" in result["message"]
    assert "public resolvers answer 10 mail." in result["message"]


def test_nameservers_agreeing_become_the_reference():
    agreeing = [ns(["192.0.2.1"]), ns(["192.0.2.1"], "ns2")]
    result = summarize("example.fr", "A", None, agreeing, [resolver(["192.0.2.9"])])
    assert "nameservers up to date 2/2" in result["message"]
    assert "public resolvers up to date 0/1" in result["message"]


def test_record_absent_everywhere_is_up_to_date():
    result = summarize("gone.example.fr", "A", [], [ns([])], [resolver([])])
    assert "not in the LWS zone" in result["message"]
    assert "public resolvers up to date 1/1" in result["message"]


async def test_tool_reports_an_unreadable_zone(make_server, fake, monkeypatch):
    async def offline_check(name, rdtype, *, saved, expected, timeout):
        return summarize(name, rdtype, saved, [], [], expected)

    monkeypatch.setattr(propagation, "check", offline_check)
    refusal = {"code": 400, "info": {"error": "bad source 1.2.3.4"}}
    fake.handler = lambda request: httpx.Response(400, json=refusal)
    result = await make_server().call_tool("check_dns_propagation", {"name": "a.example.fr", "type": "A"})
    assert "LWS zone not read" in result.structured_content["message"]
