"""SSRF guard unit tests (SPEC §5, ADR-003) — the security-critical piece."""

import socket

import pytest

from app.core.errors import ForbiddenError
from app.core.ssrf import assert_safe_url


def _fake_resolver(ip: str):
    def _getaddrinfo(*_args, **_kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 80))]

    return _getaddrinfo


@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",  # loopback
        "10.0.0.5",  # private A
        "172.16.0.1",  # private B
        "192.168.1.1",  # private C
        "169.254.169.254",  # link-local / cloud metadata
        "0.0.0.0",  # unspecified
        "::1",  # IPv6 loopback
    ],
)
def test_blocks_internal_addresses(monkeypatch, ip):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_resolver(ip))
    with pytest.raises(ForbiddenError):
        assert_safe_url("http://evil.example/path")


def test_allows_public_address(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_resolver("8.8.8.8"))
    assert_safe_url("https://example.com/hook")  # must not raise


@pytest.mark.parametrize("url", ["ftp://host/x", "file:///etc/passwd", "http://", "not-a-url"])
def test_rejects_bad_scheme_or_host(url):
    with pytest.raises(ForbiddenError):
        assert_safe_url(url)
