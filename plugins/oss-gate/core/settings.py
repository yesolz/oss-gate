"""Explicit, optional policy settings and checks before outbound requests."""

from contextlib import contextmanager
from contextvars import ContextVar
from fnmatch import fnmatchcase
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

SERVICES = {
    "api.deps.dev": "depsdev",
    "api.osv.dev": "osv",
    "registry.npmjs.org": "npm",
    "pypi.org": "pypi",
    "mcp.deepwiki.com": "deepwiki",
}
ECOSYSTEMS = {"npm", "pypi", "go", "maven", "cargo", "nuget", "rubygems"}
OSV_SYSTEMS = {
    "PyPI": "pypi",
    "Go": "go",
    "Maven": "maven",
    "crates.io": "cargo",
    "NuGet": "nuget",
    "RubyGems": "rubygems",
    "npm": "npm",
}
CURRENT = ContextVar("oss_gate_policy", default=None)
EVENTS = ContextVar("oss_gate_requests", default=None)


class PolicyBlocked(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _keys(value, allowed):
    if not isinstance(value, dict) or set(value) - set(allowed):
        raise ValueError("unknown policy field or invalid object")


def _strings(value):
    if not isinstance(value, list) or len(value) > 2000:
        raise ValueError("policy lists must contain at most 2000 strings")
    if any(not isinstance(v, str) or not v or len(v) > 2048 or re.search(r"[\x00-\x20\x7f]", v) for v in value):
        raise ValueError("invalid policy list entry")


def validate(config):
    _keys(config, {"schema", "name", "version", "network", "review"})
    if config.get("schema") != "oss-gate.settings/1":
        raise ValueError("unsupported policy schema")
    for key in ("name", "version"):
        if not isinstance(config.get(key), str) or not config[key].strip() or len(config[key]) > 120:
            raise ValueError("policy name and version are required")
    network = config.get("network", {})
    _keys(network, {"services", "allow_identifiers", "deny_identifiers"})
    for key, values in network.items():
        _strings(values)
        if key == "services":
            if set(values) - set(SERVICES.values()):
                raise ValueError("unknown external service")
        elif any(
            v.split(":", 1)[0] not in ECOSYSTEMS | {"repo"} or ":" not in v or not v.split(":", 1)[1] for v in values
        ):
            raise ValueError("identifier patterns require an ecosystem: or repo: prefix")
    review = config.get("review", {})
    _keys(review, {"minimum_release_age_days", "require_communication_review", "blocked_destinations"})
    if "minimum_release_age_days" in review:
        days = review["minimum_release_age_days"]
        if type(days) is not int or not 0 <= days <= 3650:
            raise ValueError("minimum_release_age_days must be 0..3650")
    if "require_communication_review" in review and type(review["require_communication_review"]) is not bool:
        raise ValueError("require_communication_review must be boolean")
    if "blocked_destinations" in review:
        _strings(review["blocked_destinations"])
        if any(
            not re.fullmatch(r"(?:\*\.)?[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", v) for v in review["blocked_destinations"]
        ):
            raise ValueError("blocked destinations must be lowercase host names or *.host patterns")
    return config


def fingerprint(config):
    validate(config)
    return hashlib.sha256(
        json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def load_policy(path=None):
    """Never discover a policy in the target repository or relax a launch policy."""
    configured = os.environ.get("OSS_GATE_POLICY")
    if configured and path and Path(configured).expanduser().resolve() != Path(path).expanduser().resolve():
        raise ValueError("cannot replace the policy selected by OSS_GATE_POLICY")
    selected = configured or path
    if not selected:
        return None
    source = Path(selected).expanduser()
    if not source.is_absolute():
        raise ValueError("policy path must be absolute")
    if source.stat().st_size > 512_000:
        raise ValueError("policy file is too large")
    return validate(json.loads(source.read_text(encoding="utf-8")))


@contextmanager
def policy_scope(config):
    if config is not None:
        validate(config)
    token, log = CURRENT.set(config), EVENTS.set([])
    try:
        yield EVENTS.get()
    finally:
        EVENTS.reset(log)
        CURRENT.reset(token)


def identifier(system, name):
    system = OSV_SYSTEMS.get(system, system).lower()
    if system not in ECOSYSTEMS | {"repo"} or not isinstance(name, str) or not name:
        raise PolicyBlocked("invalid_identifier")
    if system == "pypi":
        name = re.sub(r"[-_.]+", "-", name).lower()
    elif system in ("npm", "nuget"):
        name = name.lower()
    elif system == "repo":
        name = name.removeprefix("github.com/").lower()
    return f"{system}:{name}"


def check(service, identifiers=()):
    config = CURRENT.get()
    reason = None
    if config is not None:
        network = config.get("network", {})
        if service not in network.get("services", SERVICES.values()):
            reason = "service_not_allowed"

        def matches(value, pattern):
            system, name = pattern.split(":", 1)
            return fnmatchcase(value, identifier(system, name))

        for value in identifiers:
            if any(matches(value, p) for p in network.get("deny_identifiers", [])):
                reason = "identifier_denied"
            if "allow_identifiers" in network and not any(matches(value, p) for p in network["allow_identifiers"]):
                reason = reason or "identifier_not_allowed"
    events = EVENTS.get()
    if events is not None:
        # Do not copy denied names, query bodies or credentials into diagnostics.
        events.append({"service": service, "decision": "blocked" if reason else "allowed", "reason": reason})
    if reason:
        raise PolicyBlocked(reason)


def guard_request(url, body=None):
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in SERVICES
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
    ):
        raise PolicyBlocked("unrecognized_destination")
    service = SERVICES[parsed.hostname]
    parts = parsed.path.split("/")
    names = []
    if service == "depsdev":
        if "packages" in parts:
            i = parts.index("packages")
            names = [identifier(parts[i - 1], unquote(parts[i + 1]))]
        elif "projects" in parts:
            names = [identifier("repo", unquote(parts[parts.index("projects") + 1]))]
    elif service == "osv" and body:
        names = [identifier(q["package"]["ecosystem"], q["package"]["name"]) for q in body.get("queries", [])]
    elif service == "npm":
        names = [identifier("npm", unquote(parts[1]))]
    elif service == "pypi":
        names = [identifier("pypi", unquote(parts[2]))]
    check(service, names)
