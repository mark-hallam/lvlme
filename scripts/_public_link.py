"""Check whether a source is an anonymously reachable public web link."""
import ipaddress
from urllib.parse import urlsplit


def is_public_link(value):
    """True only for an https URL on a public host, with no private address or local name."""
    try:
        parsed = urlsplit(value or "")
        if parsed.scheme.lower() != "https" or not parsed.hostname or parsed.username or parsed.password:
            return False
        host = parsed.hostname.rstrip(".").lower()
        if host == "localhost" or host.endswith((".local", ".internal", ".lan")):
            return False
        try:
            return ipaddress.ip_address(host).is_global
        except ValueError:
            labels = host.split(".")
            return ("." in host and not host.startswith(".") and
                    not all(label.isdigit() for label in labels))
    except (TypeError, ValueError):
        return False


def source_is_public(source):
    """A source is checkable only when its address is public and its note has no access restriction."""
    note = (source.get("note") or "").lower()
    restricted = any(mark in note for mark in ("login", "sign in", "sign-in", "on request"))
    return not restricted and is_public_link(source.get("ref", ""))


def is_link(ref):
    """True when a source reference is a link (a web or file address), not a document, export or email note."""
    ref = (ref or "").strip().lower()
    return "://" in ref or ref.startswith("file:")


def effective_level(item):
    """Downgrade a checked claim only when its sources are all links and none of them is public. Documents,
    emails, exports and references are not links, so this rule leaves them to the evidence levels as before."""
    level, sources = item.get("level"), item.get("sources") or []
    if level not in ("verified", "corroborated") or not sources:
        return level
    if all(is_link(s.get("ref")) for s in sources) and not any(source_is_public(s) for s in sources):
        return "self_reported"
    return level
