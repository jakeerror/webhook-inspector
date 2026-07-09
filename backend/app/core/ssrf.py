"""SSRF guard for replay (SPEC §5, ADR-003).

Replay makes the *server* issue an outbound request to a user-supplied URL —
a classic SSRF vector. We allow only http/https and refuse any target that
resolves to a private, loopback, link-local or otherwise non-global address
(including cloud metadata 169.254.169.254).
"""

import ipaddress
import socket
from urllib.parse import urlparse

from app.core.errors import ForbiddenError


def _is_blocked_ip(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    )


def assert_safe_url(url: str) -> None:
    """Raise DomainError if the URL is malformed or resolves to a blocked host."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ForbiddenError("Only http/https targets are allowed")
    host = parsed.hostname
    if not host:
        raise ForbiddenError("Target URL has no host")

    try:
        infos = socket.getaddrinfo(host, parsed.port or 80, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise ForbiddenError(f"Cannot resolve host: {host}") from exc

    resolved = {info[4][0] for info in infos}
    if not resolved:
        raise ForbiddenError(f"Cannot resolve host: {host}")

    for ip in resolved:
        if _is_blocked_ip(ip):
            raise ForbiddenError(
                f"Target resolves to a blocked address ({ip}); private/loopback/"
                "link-local hosts are not allowed"
            )
