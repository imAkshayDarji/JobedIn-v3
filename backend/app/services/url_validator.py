import ipaddress
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

BLOCKED_HOSTNAMES = frozenset({
    "localhost",
    "localhost.localdomain",
    "ip6-localhost",
    "ip6-loopback",
})


def validate_apply_url(url: str) -> tuple[bool, str | None]:
    """Validate URL is safe for browser automation (SSRF protection).

    Checks:
    - Scheme must be http or https
    - Hostname must not resolve to private IP ranges
    - Hostname must not be a known internal hostname

    Returns (is_valid, error_message).
    """
    if not url or not url.strip():
        return False, "URL is empty"

    parsed = urlparse(url.strip())

    if parsed.scheme not in ("http", "https"):
        return False, f"Invalid URL scheme: {parsed.scheme!r}. Only http and https are allowed."

    hostname = parsed.hostname
    if not hostname:
        return False, "URL has no hostname"

    if hostname.lower() in BLOCKED_HOSTNAMES:
        return False, f"Hostname {hostname!r} is blocked (internal hostname)."

    try:
        resolved = ipaddress.ip_address(hostname)
    except ValueError:
        return True, None

    if resolved.is_private:
        return False, f"Hostname {hostname!r} resolves to a private IP address."
    if resolved.is_loopback:
        return False, f"Hostname {hostname!r} resolves to a loopback address."
    if resolved.is_link_local:
        return False, f"Hostname {hostname!r} resolves to a link-local address."
    if resolved.is_reserved:
        return False, f"Hostname {hostname!r} resolves to a reserved address."
    if resolved.is_multicast:
        return False, f"Hostname {hostname!r} resolves to a multicast address."

    return True, None
