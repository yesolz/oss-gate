"""Shared bounded readers and adapter result helpers. No target code execution."""

import hashlib
import json
import math


def object_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def invalid(value):
        raise ValueError("non-finite JSON number")

    result = json.loads(text, object_pairs_hook=pairs, parse_constant=invalid)
    if not isinstance(result, dict):
        raise ValueError("JSON object required")
    pending, count = [(result, 0)], 0
    while pending:
        value, depth = pending.pop()
        count += 1
        if depth > 64 or count > 250000:
            raise ValueError("JSON resource limit")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("non-finite JSON number")
        if isinstance(value, dict):
            pending.extend((v, depth + 1) for v in value.values())
        elif isinstance(value, list):
            pending.extend((v, depth + 1) for v in value)
    return result


def empty():
    return {"projects": [], "packages": [], "coverage_gaps": [], "unresolved": [], "statuses": {}}


def gap(result, code, source):
    result["coverage_gaps"].append({"code": code, "source": source})


def unresolved(result, source, kind, value):
    result["unresolved"].append(
        {"source": source, "source_type": kind, "locator_sha256": hashlib.sha256(str(value).encode()).hexdigest()}
    )


def package(system, name, version, source, project, basis="locked", **extra):
    return {
        "system": system,
        "name": name,
        "version": version,
        "lockfile": source,
        "projects": [project],
        "direct_uses": [],
        "basis": basis,
        **extra,
    }
