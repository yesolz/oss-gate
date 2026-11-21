"""Shared entry points for local MCP adapters and the CLI."""

import json
from contextlib import nullcontext

from . import api
from .collect import collect
from .settings import check, fingerprint, identifier, load_policy, npm_registry_url, policy_scope, PolicyBlocked
from .repository import parse_repository
from .tls import TLSConfigurationError, EVIDENCE as TLS_EVIDENCE


def plan(system, name, version="", repo=""):
    system, name = api.norm_system(system), api._seg(name, "name")
    if version:
        api._seg(version, "version")
    requests = [
        ("depsdev", identifier(system, name), "package and dependency metadata"),
        ("osv", identifier(system, name), "vulnerability queries"),
    ]
    if system in ("npm", "pypi"):
        requests.append((system, identifier(system, name), "only after a deps.dev 404"))
    if repo:
        repository = identifier("repo", api.normalize_repo(repo))
        requests.extend(
            [
                ("depsdev", repository, "project metadata"),
                ("deepwiki", repository, "optional explanation, separate call"),
            ]
        )
    rows = []
    for service, value, purpose in requests:
        try:
            check(service, [value])
            if service == "deepwiki" and parse_repository(value[5:])[0] != "github.com":
                decision, reason = "unsupported", "unsupported_repository_host"
            else:
                decision, reason = "allowed", None
        except PolicyBlocked as exc:
            decision, reason = "blocked", exc.code
        rows.append(
            {"service": service, "identifier": value, "purpose": purpose, "decision": decision, "reason": reason}
        )
    return {
        "target": {"system": system, "name": name, "version": version or "registry default at collection"},
        "requests": rows,
        "network_performed": False,
        "npm_registry_url": npm_registry_url() if system == "npm" else None,
        "scope": "Initial destinations only. Returned dependencies, repository candidates and advisory IDs are unknown until collection. Each later request is checked before sending. A missing version also requires version discovery.",
    }


def invoke(operation, *args, policy_path=None, **kwargs):
    """Read explicit settings once per operation; never accept per-tool policy overrides."""
    try:
        config = load_policy(policy_path)
    except (OSError, ValueError) as exc:
        return json.dumps(
            {"error": "cannot load selected policy", "code": "policy_invalid", "error_type": type(exc).__name__}
        )
    operations = {
        "lookup_package": api._lookup_package,
        "get_dependencies": api._get_dependencies,
        "get_advisory": api._get_advisory,
        "get_project": api._get_project,
        "audit_manifest": api._audit_manifest,
        "collect_review": lambda *a, **k: collect(api, *a, **k),
        "plan": plan,
    }
    if operation not in operations:
        return json.dumps({"error": "unknown operation", "code": "invalid_operation"})
    with policy_scope(config) as events:
        try:
            with nullcontext() if operation == "plan" else api.client_scope(config):
                result = json.loads(api._run(operations[operation], *args, **kwargs))
                if operation != "plan" and TLS_EVIDENCE.get() is not None:
                    result["tls_trust"] = dict(TLS_EVIDENCE.get())
        except TLSConfigurationError:
            result = {"error": "cannot load selected additional CA certificates", "code": "tls_configuration_invalid"}
        if config is not None:
            result["selected_policy"] = {
                "name": config["name"],
                "version": config["version"],
                "sha256": fingerprint(config),
            }
            result["network_decisions"] = events
        return json.dumps(result, ensure_ascii=False)
