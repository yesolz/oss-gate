"""Conservative screening categories, not legal conclusions or an SPDX validator."""

import re
from typing import Any


def _as_list(value):
    return value if isinstance(value, list) else []


CATEGORIES = ("permissive", "weak-copyleft", "strong-copyleft", "network-copyleft", "unknown")
_SEV = {c: i for i, c in enumerate(CATEGORIES)}
_CAT_TIER = {
    "permissive": "allow",
    "weak-copyleft": "conditional",
    "strong-copyleft": "hold",
    "network-copyleft": "hold",
    "unknown": "hold",
}
_PERMISSIVE = {
    "MIT",
    "MIT-0",
    "APACHE-2.0",
    "0BSD",
    "ISC",
    "UNLICENSE",
    "ZLIB",
    "PSF-2.0",
    "PYTHON-2.0",
    "CC0-1.0",
    "WTFPL",
    "ARTISTIC-2.0",
    "BSL-1.0",
    "X11",
    "POSTGRESQL",
}
_UNKNOWN_IDS = {"", "NON-STANDARD", "UNKNOWN", "NOASSERTION", "NONE"}


def _license_id_category(tok: str) -> str:
    l = tok.strip().upper()
    if re.match(r"^(A?GPL|LGPL)-", l):
        l = re.sub(r"(-ONLY|-OR-LATER|\+)$", "", l)
    if l in _UNKNOWN_IDS or l.startswith("LICENSEREF-"):
        return "unknown"
    if l in _PERMISSIVE or l in {
        "BSD-1-CLAUSE",
        "BSD-2-CLAUSE",
        "BSD-3-CLAUSE",
        "BSD-4-CLAUSE",
        "BLUEOAK-1.0.0",
        "OFL-1.0",
        "OFL-1.1",
    }:
        return "permissive"
    if l in {"AGPL-1.0", "AGPL-3.0"}:
        return "network-copyleft"
    if l in {
        "LGPL-2.0",
        "LGPL-2.1",
        "LGPL-3.0",
        "MPL-1.0",
        "MPL-1.1",
        "MPL-2.0",
        "EPL-1.0",
        "EPL-2.0",
        "CDDL-1.0",
        "CDDL-1.1",
        "CPL-1.0",
    }:
        return "weak-copyleft"
    if l in {
        "GPL-1.0",
        "GPL-2.0",
        "GPL-3.0",
        "OSL-1.0",
        "OSL-1.1",
        "OSL-2.0",
        "OSL-2.1",
        "OSL-3.0",
        "EUPL-1.0",
        "EUPL-1.1",
        "EUPL-1.2",
    }:
        return "strong-copyleft"
    return "unknown"


_TOK = re.compile(r"\(|\)|[^\s()]+")


def _expr_category(expr: str) -> str:
    """Parse AND, OR, parentheses and a small reviewed exception set conservatively.

    OR selects the least restrictive known option; AND selects the strictest.
    Unrecognized exceptions and malformed expressions require manual review."""
    toks = _TOK.findall(expr or "")
    pos = 0

    def peek() -> str | None:
        return toks[pos].upper() if pos < len(toks) else None

    def take() -> str:
        nonlocal pos
        pos += 1
        return toks[pos - 1]

    def primary() -> str:
        t = peek()
        if t is None or t in ("AND", "OR", ")", "WITH"):
            raise ValueError("syntax")
        if t == "(":
            take()
            c = or_expr()
            if peek() != ")":
                raise ValueError("paren")
            take()
            return c
        lic = take()
        if peek() == "WITH":
            take()
            if peek() is None:
                raise ValueError("with")
            exception = take()
            # Exceptions change obligations; do not interpret them automatically.
            if exception.upper() != "LLVM-EXCEPTION" or lic.upper() != "APACHE-2.0":
                return "unknown"
        return _license_id_category(lic)

    def and_expr() -> str:
        c = primary()
        while peek() == "AND":
            take()
            c = max(c, primary(), key=_SEV.get)
        return c

    def or_expr() -> str:
        c = and_expr()
        while peek() == "OR":
            take()
            c = min(c, and_expr(), key=_SEV.get)
        return c

    try:
        c = or_expr()
        return c if pos == len(toks) else "unknown"
    except (ValueError, IndexError, RecursionError):
        return "unknown"


def classify_license(licenses: Any) -> dict:
    """Return a conservative category, screening tier and explanation.

    Multiple declarations are treated as AND. This is not a legal conclusion.
    SSPL and unrecognized identifiers require manual review; no OSI claim is made."""
    if isinstance(licenses, str):
        licenses = [licenses]
    items = _as_list(licenses)
    if not items:
        return {"category": "unknown", "tier": "hold", "reason": "no license declared"}
    cats = [
        (x if isinstance(x, str) else repr(x), _expr_category(x) if isinstance(x, str) else "unknown") for x in items
    ]
    worst = max((c for _, c in cats), key=_SEV.get)
    reason = "; ".join(f"{x or '(empty)'} -> {c}" for x, c in cats)
    return {"category": worst, "tier": _CAT_TIER[worst], "reason": reason}
