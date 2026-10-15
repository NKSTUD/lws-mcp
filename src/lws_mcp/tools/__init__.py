"""Tool modules. Each one exposes register(server, client, settings) and skips the tools the settings forbid."""

from . import account, dns, domains, hosting, requests

MODULES = (dns, domains, hosting, account, requests)
