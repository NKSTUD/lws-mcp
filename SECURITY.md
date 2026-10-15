# Security

## Reporting a vulnerability

Please do not open a public issue. Use [GitHub private vulnerability reporting](https://github.com/NKSTUD/lws-mcp/security/advisories/new) and include the steps to reproduce. You will get an answer within a week.

## Your API key

- The key is read from the environment and only sent to the LWS API (`api.lws.net`) in the `X-Auth-Pass` header.
- It is never logged, written to disk or returned to the model.
- If a key leaks, generate a new one in the LWS Panel (**Api LWS**): the old one stops working.

## Limiting what an assistant can do

- `LWS_READ_ONLY=true` exposes only tools that read.
- Paid tools (`buy_hosting`, `renew_hosting`) are off unless `LWS_ENABLE_PURCHASES=true`.
- Keep your MCP client's confirmation prompts on for tools marked destructive.
