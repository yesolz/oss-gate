"""Deterministic license screening with explicit uncertainty and selected OR branches."""

import hashlib
import json
import re
from pathlib import Path
from typing import Any

_DATA = Path(__file__).with_name("license_data")
SPDX = json.loads((_DATA / "spdx.json").read_text(encoding="utf-8"))
REVIEWED = json.loads((_DATA / "reviewed.json").read_text(encoding="utf-8"))["licenses"]
IDS = {key.upper(): key for key in SPDX["licenses"]}
EXCEPTIONS = {key.upper(): key for key in SPDX["exceptions"]}
DATA_SHA256 = hashlib.sha256((_DATA / "spdx.json").read_bytes() + (_DATA / "reviewed.json").read_bytes()).hexdigest()
CATEGORIES = ("permissive", "attribution", "weak-copyleft", "strong-copyleft", "network-copyleft", "unknown")
_SEV = {category: index for index, category in enumerate(CATEGORIES)}
_CAT_TIER = dict(zip(CATEGORIES, ("allow", "conditional", "conditional", "hold", "hold", "hold")))
RANK = {"allow": 0, "conditional": 1, "hold": 2}
_TOK = re.compile(r"\(|\)|[^\s()]+")


def result(category: str, reason: str, selected=(), notes=()) -> dict:
    return {
        "category": category,
        "tier": _CAT_TIER[category],
        "reasons": [reason],
        "selected": list(selected),
        "choices": [],
        "notes": list(notes),
    }


def combine(values: list[dict]) -> dict:
    worst = max(values, key=lambda value: (RANK[value["tier"]], _SEV[value["category"]]))
    return {
        "category": worst["category"],
        "tier": worst["tier"],
        **{
            key: list(dict.fromkeys(item for value in values for item in value[key]))
            for key in ("reasons", "selected", "choices", "notes")
        },
    }


def atom(token: str, restrictions: dict) -> dict:
    upper = token.upper()
    if upper in {"NONE", "NOASSERTION", "UNKNOWN", "NON-STANDARD"}:
        return result("unknown", "missing_metadata")
    if upper.startswith(("LICENSEREF-", "DOCUMENTREF-")):
        return result("unknown", "custom_license", [token])
    canonical = IDS.get(upper)
    if canonical is None:
        return result("unknown", "unrecognized_identifier", [token])
    rule = REVIEWED.get(canonical)
    value = (
        result(rule["category"], "reviewed", [canonical], [rule["note"]])
        if rule
        else result("unknown", "unclassified_spdx", [canonical])
    )
    requested = restrictions.get(canonical)
    if requested and RANK[requested] > RANK[value["tier"]]:
        value["tier"] = requested
        value["reasons"].append("selected_license_restriction")
    return value


def expression(expr: str, restrictions: dict) -> dict:
    if not expr.strip():
        return result("unknown", "missing_metadata")
    if len(expr) > 8192:
        return result("unknown", "invalid_expression")
    tokens = _TOK.findall(expr)
    if len(tokens) > 512:
        return result("unknown", "invalid_expression")
    position = 0

    def peek():
        return tokens[position].upper() if position < len(tokens) else None

    def take():
        nonlocal position
        token = tokens[position]
        position += 1
        return token

    def primary():
        if peek() is None or peek() in ("AND", "OR", ")", "WITH"):
            raise ValueError("expected license")
        if peek() == "(":
            take()
            value = or_expr()
            if peek() != ")":
                raise ValueError("unclosed expression")
            take()
            return value
        token = take()
        if not re.fullmatch(
            r"(?:[A-Za-z0-9][A-Za-z0-9.-]*\+?|DocumentRef-[A-Za-z0-9.-]+:LicenseRef-[A-Za-z0-9.-]+)", token, re.I
        ):
            raise ValueError("invalid license token")
        value = atom(token, restrictions)
        if peek() == "WITH":
            take()
            if peek() is None or peek() in ("AND", "OR", "WITH", "(", ")"):
                raise ValueError("expected exception")
            exception = take()
            if token.upper() != "APACHE-2.0" or exception.upper() != "LLVM-EXCEPTION":
                code = "unsupported_exception" if exception.upper() in EXCEPTIONS else "unrecognized_exception"
                return result("unknown", code, [token + " WITH " + exception])
            value["selected"] = ["Apache-2.0 WITH LLVM-exception"]
            value["notes"].append("Apply the LLVM exception with Apache-2.0; retain the applicable notices.")
        return value

    def and_expr():
        values = [primary()]
        while peek() == "AND":
            take()
            values.append(primary())
        return combine(values)

    def or_expr():
        values = [and_expr()]
        while peek() == "OR":
            take()
            values.append(and_expr())
        chosen = min(values, key=lambda value: (RANK[value["tier"]], _SEV[value["category"]]))
        if len(values) > 1:
            chosen["choices"].append(" AND ".join(chosen["selected"]) or "unresolved branch")
        return chosen

    try:
        value = or_expr()
        if position != len(tokens):
            raise ValueError("trailing tokens")
        return value
    except (ValueError, IndexError, RecursionError):
        return result("unknown", "invalid_expression")


def classify_license(licenses: Any, restrictions: dict | None = None) -> dict:
    """Lists use AND as a screening assumption; no unknown branch becomes approval."""
    items = [licenses] if isinstance(licenses, str) else licenses
    if items is None or items == []:
        value = result("unknown", "missing_metadata")
    elif not isinstance(items, list) or len(items) > 200 or any(not isinstance(x, str) for x in items):
        value = result("unknown", "invalid_metadata")
    else:
        value = combine([expression(item, restrictions or {}) for item in items])
    return {
        **value,
        "reason": "; ".join(value["selected"] + value["reasons"]),
        "spdx_version": SPDX["version"],
        "classification_sha256": DATA_SHA256,
    }
