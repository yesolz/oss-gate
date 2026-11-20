"""Parse repository identities without dropping their host or path components."""

import re
from urllib.parse import urlsplit


def hostname(value):
    if not isinstance(value, str) or not value or re.search(r"[\s/:@%\\?#\[\]]", value):
        raise ValueError("expected a host name without URL, port or wildcard")
    host = value.rstrip(".").encode("idna").decode("ascii").lower()
    if len(host) > 253 or any(
        not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in host.split(".")
    ):
        raise ValueError("invalid host name")
    return host


def parse_repository(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("expected owner/repo or a repository URL")
    value = value.strip()
    if len(value) > 2048 or re.search(r"[\x00-\x20\x7f\\%@?#]", value):
        raise ValueError("invalid repository identifier")
    if "://" in value:
        url = urlsplit(value)
        if url.scheme not in ("https", "http") or url.port is not None or not url.hostname:
            raise ValueError("unsupported repository URL")
        host, path = hostname(url.hostname), url.path.strip("/")
    else:
        parts = value.strip("/").split("/")
        if len(parts) == 2:
            host, path = "github.com", "/".join(parts)
        elif len(parts) >= 3:
            host, path = hostname(parts[0]), "/".join(parts[1:])
        else:
            raise ValueError("expected owner/repo or host/owner/repo")
    if host == "www.github.com":
        host = "github.com"
    if path.lower().endswith(".git"):
        path = path[:-4]
    parts = path.split("/")
    if len(parts) < 2 or any(p in (".", "..") or not re.fullmatch(r"[A-Za-z0-9_.-]+", p) for p in parts):
        raise ValueError("invalid repository path")
    # Recognize GitHub page links returned in upstream metadata. Other hosts
    # retain the entire path, including enterprise groups and subgroups.
    if host == "github.com" and len(parts) > 2:
        if parts[2] not in {"issues", "pull", "tree", "blob", "releases", "security", "discussions", "actions"}:
            raise ValueError("use the GitHub repository root")
        path = "/".join(parts[:2])
    return host, path.lower()


def normalize_repository(value):
    host, path = parse_repository(value)
    return f"{host}/{path}"
