"""Isolated source adapters for Thalos Prime.

Adapters fetch or accept raw material but cannot evaluate truth, commit beliefs,
or execute instructions found in content. Network policy is explicit and
private/local address ranges are rejected by default.
"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse

import httpx

from thalos_prime.epistemic_core import SourceArtifact, TrustClass
from thalos_prime.security import TaintLabel, TaintedValue


class SourceAdapter(Protocol):
    def ingest(self) -> SourceArtifact:
        """Return one immutable source artifact."""


@dataclass(frozen=True)
class TextSourceAdapter:
    text: str
    source_uri: str | None = None
    title: str | None = None
    issuer: str | None = None
    trust_class: TrustClass = TrustClass.USER_ASSERTION

    def ingest(self) -> SourceArtifact:
        return SourceArtifact.create(
            self.text,
            source_uri=self.source_uri,
            source_title=self.title,
            issuer=self.issuer,
            trust_class=self.trust_class,
        )


@dataclass(frozen=True)
class HttpSourcePolicy:
    allowed_schemes: tuple[str, ...] = ("https",)
    max_bytes: int = 2_000_000
    timeout_seconds: float = 15.0
    allow_private_networks: bool = False
    user_agent: str = "ThalosPrimeSourceAdapter/1.0"


class UnsafeSourceUrl(ValueError):
    """Raised when a source URL violates network policy."""


def validate_source_url(url: str, policy: HttpSourcePolicy) -> None:
    parsed = urlparse(url)
    if parsed.scheme.lower() not in policy.allowed_schemes:
        raise UnsafeSourceUrl(f"scheme {parsed.scheme!r} is not allowed")
    if not parsed.hostname:
        raise UnsafeSourceUrl("source URL has no hostname")
    try:
        addresses = {
            item[4][0]
            for item in socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
        }
    except socket.gaierror as exc:
        raise UnsafeSourceUrl("source hostname could not be resolved") from exc
    if not policy.allow_private_networks:
        for raw in addresses:
            address = ipaddress.ip_address(raw)
            if (
                address.is_private
                or address.is_loopback
                or address.is_link_local
                or address.is_multicast
                or address.is_reserved
                or address.is_unspecified
            ):
                raise UnsafeSourceUrl("source resolves to a non-public network address")


@dataclass(frozen=True)
class HttpTextSourceAdapter:
    url: str
    policy: HttpSourcePolicy = HttpSourcePolicy()
    trust_class: TrustClass = TrustClass.UNKNOWN

    def ingest(self) -> SourceArtifact:
        validate_source_url(self.url, self.policy)
        with httpx.Client(
            timeout=self.policy.timeout_seconds,
            follow_redirects=False,
            headers={"User-Agent": self.policy.user_agent},
        ) as client:
            response = client.get(self.url)
            response.raise_for_status()
            length = response.headers.get("content-length")
            if length is not None and int(length) > self.policy.max_bytes:
                raise ValueError("source exceeds configured byte limit")
            raw = response.content
            if len(raw) > self.policy.max_bytes:
                raise ValueError("source exceeds configured byte limit")
            content_type = response.headers.get("content-type", "text/plain").split(";", 1)[0]
            text = raw.decode(response.encoding or "utf-8", errors="replace")
        return SourceArtifact.create(
            text,
            media_type=content_type,
            source_uri=self.url,
            trust_class=self.trust_class,
        )

    def tainted_preview(self) -> TaintedValue:
        artifact = self.ingest()
        return TaintedValue(
            value=artifact.canonical_text,
            labels=frozenset({TaintLabel.EXTERNAL_CONTENT}),
            origin_id=artifact.artifact_id,
        )


__all__ = [
    "HttpSourcePolicy",
    "HttpTextSourceAdapter",
    "SourceAdapter",
    "TextSourceAdapter",
    "UnsafeSourceUrl",
    "validate_source_url",
]
