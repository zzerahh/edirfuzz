"""Authorization and target-scope enforcement (Person 4).

Every target and every redirect destination must pass through this module
before any request is sent. The default scope only contains loopback and
documentation/test ranges; anything else needs an explicit --allow-host.
"""
from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

SAFE_DEFAULT_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "example.com"})
# Loopback + RFC 5737 documentation ranges (TEST-NET-1/2/3).
SAFE_DEFAULT_NETWORKS = (
    "127.0.0.0/8",
    "::1/128",
    "192.0.2.0/24",
    "198.51.100.0/24",
    "203.0.113.0/24",
)
ALLOWED_SCHEMES = ("http", "https")
MIN_IPV4_PREFIX = 16  
MIN_IPV6_PREFIX = 48
_HOSTNAME_RE = re.compile(
    r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)*[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$"
)

LEGAL_BANNER = """ENHANCED DIRECTORY FUZZER

AUTHORIZED SECURITY TESTING ONLY

Unauthorized access to computer systems may violate
Malaysia's Computer Crimes Act 1997.

Only test systems for which you have explicit permission."""

CONFIRM_PROMPT = "Type YES to confirm authorization: "


class ScopeError(ValueError):
    """Raised when a target, scope entry, or authorization check fails."""


@dataclass(frozen=True)
class Scope:
    """Set of hostnames and IP networks the tool is allowed to touch."""

    hosts: frozenset
    networks: tuple

    @classmethod
    def default(cls) -> "Scope":
        return cls(SAFE_DEFAULT_HOSTS, tuple(ipaddress.ip_network(n) for n in SAFE_DEFAULT_NETWORKS))

    def extended(self, entries) -> "Scope":
        """Return a new Scope with user-approved hosts / IPs / CIDRs added."""
        hosts = set(self.hosts)
        networks = list(self.networks)
        for raw in entries or []:
            entry = raw.strip().lower().rstrip(".")
            if not entry or "*" in entry:
                raise ScopeError(f"Invalid scope entry {raw!r}: wildcards are not allowed.")
            if "/" in entry:
                try:
                    net = ipaddress.ip_network(entry, strict=False)
                except ValueError as exc:
                    raise ScopeError(f"Invalid CIDR {raw!r}: {exc}") from exc
                min_prefix = MIN_IPV4_PREFIX if net.version == 4 else MIN_IPV6_PREFIX
                if net.prefixlen < min_prefix:
                    raise ScopeError(f"Scope {raw!r} is too broad (minimum prefix /{min_prefix}).")
                networks.append(net)
                continue
            try:
                ip = ipaddress.ip_address(entry)
            except ValueError:
                if not _HOSTNAME_RE.match(entry):
                    raise ScopeError(f"Invalid hostname in scope: {raw!r}")
                hosts.add(entry)
            else:
                networks.append(ipaddress.ip_network(ip))
        return Scope(frozenset(hosts), tuple(networks))

    def contains_host(self, host) -> bool:
        if not host:
            return False
        host = host.lower().rstrip(".")
        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            return host in self.hosts
        return any(ip in net for net in self.networks if net.version == ip.version)


def is_default_safe_host(host) -> bool:
    return Scope.default().contains_host(host)


def validate_target(target: str, scope: Scope) -> str:
    """Validate the declared target and return a normalized base URL.

    Raises ScopeError for a missing/unsupported scheme, embedded credentials,
    query strings or fragments, invalid ports, or a host outside the scope.
    """
    target = (target or "").strip()
    try:
        parts = urlsplit(target)
        port = parts.port  
    except ValueError as exc:
        raise ScopeError(f"Invalid target URL: {exc}") from exc
    if parts.scheme not in ALLOWED_SCHEMES:
        raise ScopeError("Target must start with http:// or https://")
    if not parts.hostname:
        raise ScopeError("Target has no hostname.")
    if parts.username or parts.password:
        raise ScopeError("Credentials inside the target URL are not allowed.")
    if parts.query or parts.fragment:
        raise ScopeError("Target must not contain a query string or fragment.")
    if not scope.contains_host(parts.hostname):
        raise ScopeError(
            f"Target host '{parts.hostname}' is outside the authorized scope. "
            "If you have written permission, add it with --allow-host."
        )
    host = f"[{parts.hostname}]" if ":" in parts.hostname else parts.hostname
    netloc = f"{host}:{port}" if port else host
    return f"{parts.scheme}://{netloc}{parts.path.rstrip('/')}"


def is_url_in_scope(url: str, base_url: str, scope: Scope) -> bool:
    """True if `url` (absolute or relative to base_url) stays inside scope.

    Used to decide whether a redirect Location may ever be followed/probed.
    """
    try:
        parts = urlsplit(urljoin(base_url + "/", url))
        _ = parts.port
    except ValueError:
        return False
    return parts.scheme in ALLOWED_SCHEMES and scope.contains_host(parts.hostname)


def confirm_authorization(input_fn=input, assume_yes: bool = False, safe_target: bool = True) -> bool:
    """Ask the operator to confirm authorization. Only the exact word YES passes.

    --yes (assume_yes) is accepted only for default safe targets, so a real
    third-party target can never be scanned without a typed confirmation.
    """
    if assume_yes:
        if not safe_target:
            raise ScopeError(
                "--yes can only be used with the default safe targets; type YES interactively instead."
            )
        return True
    try:
        return input_fn(CONFIRM_PROMPT).strip() == "YES"
    except EOFError:
        return False
