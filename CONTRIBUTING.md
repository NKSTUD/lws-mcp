# Contributing

Thanks for helping! Issues and pull requests are welcome, in English or French.

## Setup

```bash
git clone https://github.com/NKSTUD/lws-mcp && cd lws-mcp
uv sync
uv run pytest
```

Before opening a pull request:

```bash
uv run ruff check . && uv run ruff format --check . && uv run pytest
```

## Layout

```
src/lws_mcp/
  config.py        settings read from environment variables
  client.py        HTTP client: auth headers, LWS response envelope, errors
  server.py        builds the MCP server and registers the tool modules
  tools/
    _common.py     shared types (Domain) and tool hints (READ, WRITE, DESTRUCTIVE)
    dns.py         DNS zone records
    domains.py     domains, nameservers, redirections
    hosting.py     hosting, renewal, purchases
    account.py     balance, history, contacts
    requests.py    deferred requests
tests/             pytest, the API is mocked with httpx.MockTransport (no network, no key needed)
```

## Adding or changing a tool

1. Find the endpoint in the [LWS API reference](https://api.lws.fr/api-client/lws-client-api) (the OpenAPI file is at `https://api.lws.net/openapi.json`).
2. Add an `async` function in the matching `tools/*.py` module, inside `register()`:
   - a `snake_case` verb name (`get_`, `list_`, `add_`, `update_`, `delete_`...);
   - typed parameters with `Field(description=...)`: the model only sees the schema and the docstring;
   - a one-line docstring that says what it does and anything surprising (deferred, paid, irreversible);
   - the right hint: `READ`, `WRITE`, `DESTRUCTIVE`, or `PAID`.
3. Put it behind the right setting: writes after `if not settings.allows_writes: return`, paid actions behind `settings.allows_purchases`.
4. Add a test in `tests/test_tools.py` that checks the request sent (method, path, body), and add the name to the tool sets at the top of that file.
5. Update the tool table in both READMEs and the `Unreleased` section of [CHANGELOG.md](CHANGELOG.md).

## Testing against the real API

Copy `.env.example` to `.env` (ignored by git) and fill it. Prefer `LWS_TEST_MODE=true` with a test key while developing:

```bash
npx @modelcontextprotocol/inspector uv run --env-file .env lws-mcp
```

Never paste an API key in an issue, a commit or a test.

## Commits and pull requests

- One topic per pull request, with a short description of what changes for the user.
- Tests and lint must pass (CI runs them on Python 3.10 to 3.13).
