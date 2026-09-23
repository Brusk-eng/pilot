from __future__ import annotations

from typing import NotRequired, TypedDict


class SiteDomains(TypedDict):
    domains: list[str]
    primary: str | None


class SiteDomain(TypedDict):
    domain: str
    is_primary: bool


class DnsRecord(TypedDict):
    type: str
    host: str
    value: str


class DnsRecords(TypedDict):
    """Alternative record sets, each a complete recipe. Empty when no manual records are needed."""

    cname: NotRequired[list[DnsRecord]]
    a: NotRequired[list[DnsRecord]]
