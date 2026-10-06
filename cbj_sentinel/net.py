"""Hardened HTTP helpers.

Every request: HTTPS only, host must be on an allowlist, redirects are
re-validated, response size is capped, and timeouts are enforced.
Every URL handed to the browser: HTTPS only and host on a separate allowlist,
which prevents a malicious feed link from launching local files via
``os.startfile`` (what ``webbrowser.open`` uses on Windows).
"""
from __future__ import annotations

import json
import logging
import urllib.request
import webbrowser
from typing import Any, Iterable
from urllib.parse import urlsplit

from . import config

log = logging.getLogger(__name__)


class UnsafeURLError(ValueError):
    """Raised when a URL fails scheme/host validation."""


class ResponseTooLargeError(IOError):
    """Raised when a response exceeds the configured byte cap."""


def validate_url(url: Any, allowed_hosts: Iterable[str]) -> str:
    if not isinstance(url, str) or len(url) > 2048:
        raise UnsafeURLError("URL must be a string under 2048 chars")
    if any(ord(c) < 0x20 for c in url) or "\\" in url:
        raise UnsafeURLError("URL contains control characters or backslashes")
    parts = urlsplit(url.strip())
    if parts.scheme.lower() != "https":
        raise UnsafeURLError(f"Only https URLs are allowed: {url!r}")
    if parts.username or parts.password:
        raise UnsafeURLError("Credentials in URLs are not allowed")
    try:
        port = parts.port
    except ValueError as exc:
        raise UnsafeURLError("Invalid port") from exc
    if port not in (None, 443):
        raise UnsafeURLError("Non-standard ports are not allowed")
    host = (parts.hostname or "").lower().rstrip(".")
    if host not in {h.lower() for h in allowed_hosts}:
        raise UnsafeURLError(f"Host not allowed: {host!r}")
    return url.strip()


def is_safe_browser_url(url: Any) -> bool:
    try:
        validate_url(url, config.BROWSER_HOSTS)
        return True
    except UnsafeURLError:
        return False


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    max_redirections = config.MAX_REDIRECTS

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl, config.FETCH_HOSTS)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_opener = urllib.request.build_opener(_SafeRedirectHandler())


def fetch_bytes(url: str, max_bytes: int, timeout: float = config.HTTP_TIMEOUT) -> bytes:
    validate_url(url, config.FETCH_HOSTS)
    req = urllib.request.Request(url, headers={
        "User-Agent": config.USER_AGENT,
        "Accept": "application/json, application/rss+xml, application/xml;q=0.9, */*;q=0.5",
    })
    with _opener.open(req, timeout=min(float(timeout), 30.0)) as resp:
        length = resp.headers.get("Content-Length")
        if length and length.isdigit() and int(length) > max_bytes:
            raise ResponseTooLargeError(f"{url} declares {length} bytes")
        data = resp.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ResponseTooLargeError(f"{url} exceeded {max_bytes} bytes")
    return data


def fetch_json(url: str) -> dict:
    data = json.loads(fetch_bytes(url, config.MAX_JSON_BYTES).decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Unexpected JSON shape from {url}")
    return data


def open_in_browser(url: str) -> bool:
    """Open a URL only if it passes the browser allowlist."""
    if not is_safe_browser_url(url):
        log.warning("Blocked attempt to open unsafe URL: %r", url)
        return False
    try:
        return bool(webbrowser.open(url, new=2))
    except Exception:  # pragma: no cover - platform specific
        log.exception("Failed to open browser")
        return False
