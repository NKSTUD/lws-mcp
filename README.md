# lws-mcp

[![CI](https://github.com/NKSTUD/lws-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/NKSTUD/lws-mcp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)

**English** · [Français](README.fr.md)

An [MCP](https://modelcontextprotocol.io) server for the [LWS](https://www.lws.fr) Client API. Manage your domains, DNS zones, hosting and account from Claude, Cursor or any MCP client:

> *"Add the CNAME records Stripe gave me to example.fr, then tell me when they are live."*

It covers the whole [LWS Client API](https://api.lws.fr/api-client/lws-client-api) (29 endpoints), plus a propagation check through a public resolver.

> Community project, not affiliated with or endorsed by LWS.

## Tools

| Area | Tools |
| --- | --- |
| **DNS** | `get_dns_zone` · `add_dns_record` · `update_dns_record` · `delete_dns_record` · `check_dns_propagation` |
| **Domains** | `get_domain` · `check_domain_availability` · `list_tlds` · `update_nameservers` · `set_transfer_protection` · `request_transfer_authcode` · `create_domain_redirect` · `delete_domain_redirect` |
| **Hosting** | `list_hostings` · `get_hosting` · `list_hosting_prices` · `get_renewal_prices` · `set_auto_renew` · `buy_hosting`¹ · `renew_hosting`¹ |
| **Account** | `get_account_balance` · `get_purchase_history` · `list_contacts` · `get_contact` · `create_contact` · `update_contact` · `add_test_credit_to_contact`² · `add_test_credit_to_account`² |
| **Requests** | `list_requests` · `list_pending_requests` |

¹ Paid: off unless `LWS_ENABLE_PURCHASES=true`. ² Only in test mode.

DNS record names can be written in full (`_dmarc.example.fr`): they are shortened to what the LWS zone expects (`_dmarc`, `@`).

## Safety

An assistant with access to your DNS can take a site or a mailbox down, and one with access to purchases can spend money. So:

- **Purchases are off by default.** `buy_hosting` and `renew_hosting` only exist when `LWS_ENABLE_PURCHASES=true`.
- **Read-only mode.** `LWS_READ_ONLY=true` removes every tool that changes something.
- **Hints for your client.** Every tool declares whether it reads, writes or destroys ([tool annotations](https://modelcontextprotocol.io/specification/2025-06-18/server/tools#tool-annotations)), so clients can ask before running it.
- **Test environment.** `LWS_TEST_MODE=true` sends every request to the LWS sandbox.
- **Your key stays local.** It goes only to `api.lws.net`, and is never logged or returned to the model.

## Requirements

- An LWS account and its API key: [LWS Panel](https://www.lws.fr/panel) → your account number (LWS-XXXXXX, top right) → **Api LWS** → **Clé API en mode PRODUCTION** → *voir*. [LWS guide](https://aide.lws.fr/a/1943).
- The public IP address of the machine running the server, allowed on the same **Api LWS** page. Otherwise every call fails with `bad source <your IP>`.
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (it fetches Python and the server for you).

## Installation

### Claude Code

```bash
claude mcp add lws \
  -e LWS_LOGIN=123456 \
  -e LWS_API_KEY=your-api-key \
  -- uvx --from git+https://github.com/NKSTUD/lws-mcp lws-mcp
```

### Claude Desktop, Cursor, Windsurf and other clients

Add to the client's MCP configuration (`claude_desktop_config.json`, `.cursor/mcp.json`...):

```json
{
  "mcpServers": {
    "lws": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/NKSTUD/lws-mcp", "lws-mcp"],
      "env": {
        "LWS_LOGIN": "123456",
        "LWS_API_KEY": "your-api-key"
      }
    }
  }
}
```

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `LWS_LOGIN` | *required* | Your LWS account ID (the digits of LWS-XXXXXX). |
| `LWS_API_KEY` | *required* | Production API key. |
| `LWS_TEST_API_KEY` | | Test key, used instead of `LWS_API_KEY` in test mode. |
| `LWS_TEST_MODE` | `false` | Send requests to the LWS test environment. |
| `LWS_READ_ONLY` | `false` | Only expose tools that read. |
| `LWS_ENABLE_PURCHASES` | `false` | Expose `buy_hosting` and `renew_hosting`. |
| `LWS_TIMEOUT` | `30` | Request timeout, in seconds. |
| `LWS_BASE_URL` | `https://api.lws.net/v1` | API base URL. |

## Good to know

- **Deferred actions.** Nameserver changes, transfer protection, auth codes, purchases and renewals are processed in the background. Follow them with `list_pending_requests`.
- **Propagation.** A DNS change can take from minutes to a few hours to be seen everywhere. `check_dns_propagation` shows what Cloudflare's 1.1.1.1 sees now.
- **Allowed TTLs.** 900, 1800, 3600, 7200, 21600, 43200 or 86400 seconds.

## Development

```bash
git clone https://github.com/NKSTUD/lws-mcp && cd lws-mcp
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

Try it against your account with the [MCP Inspector](https://github.com/modelcontextprotocol/inspector), credentials in a local `.env` (see [.env.example](.env.example)):

```bash
npx @modelcontextprotocol/inspector uv run --env-file .env lws-mcp
```

See [CONTRIBUTING.md](CONTRIBUTING.md) to add a tool or fix a bug.

## License

[MIT](LICENSE)
