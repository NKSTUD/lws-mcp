# Changelog

All notable changes are listed here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.0] - 2026-10-15

### Changed

- `check_dns_propagation` no longer trusts a single resolver, which can lag behind a change. It compares what is
  saved in the LWS zone, what the domain's nameservers answer (no cache), and what Cloudflare, Google and Quad9
  answer, marks each one up to date or not, and says how long a stale answer can last. An optional `expected`
  value can be checked instead of the zone. Thanks @TheUpright_Man for the suggestion.
- Public resolvers are queried over DNS-over-HTTPS (HTTP/2), so the check works where port 53 is blocked.

## [0.1.0] - 2026-10-15

### Added

- Published on PyPI: `uvx lws-mcp`.
- Tools for the whole LWS Client API: DNS zone, domains, hosting, account and contacts, deferred requests.
- `check_dns_propagation`, to see what a public resolver answers after a change.
- Safety settings: `LWS_READ_ONLY`, `LWS_ENABLE_PURCHASES` (off by default), `LWS_TEST_MODE` with `LWS_TEST_API_KEY`.
- Full DNS names are shortened to the relative form the LWS zone expects.

[Unreleased]: https://github.com/NKSTUD/lws-mcp/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/NKSTUD/lws-mcp/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/NKSTUD/lws-mcp/releases/tag/v0.1.0
