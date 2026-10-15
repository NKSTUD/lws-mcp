"""Account and contacts: balance, purchase history, contacts, and test-environment credit."""

from __future__ import annotations

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from ..client import LwsClient
from ..config import Settings
from ._common import READ, WRITE, Result

ContactId = Annotated[int, Field(ge=1, description="LWS contact ID (see list_contacts)")]
Phone = Annotated[str, Field(pattern=r"^00\d{6,15}$", description="International format 00{country}{number}")]
Country = Annotated[str, Field(min_length=2, max_length=2, description="ISO country code, e.g. FR")]
Password = Annotated[str, Field(min_length=8, description="Password of the contact's LWS customer area")]
Amount = Annotated[int, Field(ge=1, description="Amount of credit to add, in EUR")]


def register(server: MCPServer, client: LwsClient, settings: Settings) -> None:
    @server.tool(annotations=READ)
    async def get_account_balance() -> Result:
        """Get the remaining balance of the prepaid account, in EUR."""
        return await client.request("GET", "/contact/0/credit")

    @server.tool(annotations=READ)
    async def get_purchase_history() -> Result:
        """List every purchase, renewal and other transaction made through the API."""
        return await client.request("GET", "/contact/purchase/history")

    @server.tool(annotations=READ)
    async def list_contacts() -> Result:
        """List the contacts managed by the account, keyed by contact ID."""
        return await client.request("GET", "/contact/0/list")

    @server.tool(annotations=READ)
    async def get_contact(contact: ContactId) -> Result:
        """Get a contact's details (name, address, e-mail, phone, credit)."""
        return await client.request("GET", f"/contact/{contact}")

    if settings.allows_writes:

        @server.tool(annotations=WRITE)
        async def create_contact(
            firstname: str,
            lastname: str,
            email: str,
            phone: Phone,
            address: str,
            postal: str,
            city: str,
            country: Country,
            password: Password,
            company: Annotated[str | None, Field(description="Leave empty for an individual")] = None,
        ) -> Result:
            """Create a contact managed by the account, usable as owner of domains and hostings."""
            body = {
                "firstname": firstname,
                "lastname": lastname,
                "email": email,
                "phone": phone,
                "address": address,
                "postal": postal,
                "city": city,
                "country": country.upper(),
                "password": password,
                "company": company,
            }
            return await client.request("POST", "/contact", json={k: v for k, v in body.items() if v is not None})

        @server.tool(annotations=WRITE)
        async def update_contact(
            contact: ContactId,
            address: str | None = None,
            postal: str | None = None,
            city: str | None = None,
            country: Country | None = None,
            phone: Phone | None = None,
            password: Password | None = None,
        ) -> Result:
            """Update a contact's address, phone or password. Only the fields given are changed."""
            body = {
                "address": address,
                "postal": postal,
                "city": city,
                "country": country.upper() if country else None,
                "phone": phone,
                "password": password,
            }
            body = {key: value for key, value in body.items() if value is not None}
            return await client.request("PUT", f"/contact/{contact}", json=body)

    # These two only work against the LWS test environment, where they fund fake purchases.
    if settings.test_mode:

        @server.tool(annotations=WRITE)
        async def add_test_credit_to_contact(contact: ContactId, amount: Amount) -> Result:
            """TEST ENVIRONMENT ONLY: add fake credit to a contact."""
            return await client.request("PUT", f"/contact/{contact}/credit", json={"amount": amount})

        @server.tool(annotations=WRITE)
        async def add_test_credit_to_account(amount: Amount) -> Result:
            """TEST ENVIRONMENT ONLY: add fake credit to your own (reseller) account."""
            return await client.request("PUT", "/contact/reseller/credit", json={"amount": amount})
