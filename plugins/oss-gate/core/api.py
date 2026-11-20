"""Public metadata collection independent of the MCP and CLI transports."""

from __future__ import annotations

import json
from contextvars import ContextVar, copy_context

import re
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote

import httpx

VERSION = "0.3.0"
DEPSDEV_BASE = "https://api.deps.dev/v3"
OSV_BASE = "https://api.osv.dev/v1"
USER_AGENT = f"oss-gate-depsdev/{VERSION}"
TIMEOUT = 15.0
RETRY_STATUSES = {429, 500, 502, 503, 504}
MAX_RETRY_DELAY = 2.0
MAX_MANIFEST_BYTES = 512_000
MAX_MANIFEST_ENTRIES = 2000
MAX_FALLBACK_ATTEMPTS = 8
GRAPH_404_HINT = "deps.dev has no resolved graph for this version yet; try previous_version from lookup_package"

SYSTEMS = ("npm", "pypi", "go", "maven", "cargo", "nuget", "rubygems")
_OSV_ECO = {
    "npm": "npm",
    "pypi": "PyPI",
    "go": "Go",
    "maven": "Maven",
    "cargo": "crates.io",
    "nuget": "NuGet",
    "rubygems": "RubyGems",
}

from core.licenses import CATEGORIES, _SEV, classify_license
from .registry import check_registry
from .settings import guard_request, PolicyBlocked

_client = httpx.Client(timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}, follow_redirects=False, trust_env=False)


class ApiError(Exception):
    def __init__(self, message: str, status: int | None = None, hint: str | None = None, extra: dict | None = None):
        super().__init__(message)
        self.message, self.status, self.hint, self.extra = message, status, hint, extra


# ----------------------------------------------------------------- shape guards / validation
def _as_list(x: Any) -> list:
    return x if isinstance(x, list) else []


def _as_dict(x: Any) -> dict:
    return x if isinstance(x, dict) else {}


def _dicts(x: Any) -> list[dict]:
    return [i for i in _as_list(x) if isinstance(i, dict)]


def _strs(x: Any) -> list[str]:
    return [i for i in _as_list(x) if isinstance(i, str)]


def _seg(x: Any, what: str) -> str:
    """Validate a nonempty identifier and reject path traversal segments."""
    if not isinstance(x, str) or not x.strip():
        raise ApiError(f"invalid input: {what} is empty")
    s = x.strip()
    if len(s) > 2048 or re.search(r"[\x00-\x20\x7f]", s):
        raise ApiError(f"invalid input: {what} contains whitespace/control characters or is too long")
    if any(p in (".", "..") for p in s.split("/")) or quote(s, safe="") in (".", ".."):
        raise ApiError(f"invalid input: {what} is not a valid identifier")
    return s


def norm_system(system: str) -> str:
    s = (system or "").strip().lower() if isinstance(system, str) else ""
    if s not in SYSTEMS:
        raise ApiError(f"unsupported system; use one of {', '.join(SYSTEMS)}")
    return s


def osv_ecosystem(system: str) -> str:
    """Map a deps.dev ecosystem to its OSV identifier."""
    return _OSV_ECO[norm_system(system)]


# ----------------------------------------------------------------- license classification
# ----------------------------------------------------------------- repo / manifest helpers
def normalize_repo(s: str) -> str:
    """'owner/repo' | 'github.com/owner/repo' | 'https://github.com/owner/repo(.git)' → 'github.com/owner/repo'."""
    r = (s or "").strip() if isinstance(s, str) else ""
    r = re.sub(r"^[a-z]+://", "", r, flags=re.I)
    r = re.sub(r"^(www\.)?", "", r, flags=re.I).strip("/")
    if r.lower().endswith(".git"):
        r = r[:-4]
    parts = [p for p in r.split("/") if p]
    if not parts:
        raise ApiError("invalid input: empty repo id")
    if "." not in parts[0]:
        parts = ["github.com"] + parts
    if len(parts) < 3 or any(p in (".", "..") for p in parts[:3]):
        raise ApiError("invalid input: repo id must look like owner/repo")
    return "/".join(parts[:3]).lower()


_VER_RE = re.compile(r"^v?\d+(\.\d+)*(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$")
_NPM_NUM = r"(?:0|[1-9]\d*)"
_NPM_PRE = r"(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)"
_NPM_VERSION_RE = re.compile(
    rf"^v?{_NPM_NUM}\.{_NPM_NUM}\.{_NPM_NUM}(?:-{_NPM_PRE}(?:\.{_NPM_PRE})*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


def _pkgjson_spec(spec: str) -> tuple[str, bool]:
    """Accept an exact version only. Ranges, tags and URLs remain unresolved."""
    s = spec.strip()
    if _NPM_VERSION_RE.fullmatch(s):
        return s, True
    return "", False


def _parse_package_json(text: str) -> list[dict]:
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ApiError("invalid input: package.json must be an object")
    out = []
    for key in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
        if key in data and not isinstance(data[key], dict):
            raise ApiError(f"invalid input: {key} must be an object")
        for name, spec in _as_dict(data.get(key)).items():
            spec = spec.strip() if isinstance(spec, str) else ""
            entry = {"name": name, "version": "", "pinned": False, "group": key}
            if spec.startswith("npm:") and "@" in spec[4:]:
                real, _, spec = spec[4:].rpartition("@")
                if real:
                    entry.update(name=real, aliased_from=name)
            entry["version"], entry["pinned"] = _pkgjson_spec(spec)
            out.append(entry)
    return out


_REQ_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(\[[^\]]*\])?\s*(==(?!=)\s*([^\s,\\;#]+))?")


def _parse_requirements(text: str) -> list[dict]:
    out = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].split(";", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        m = _REQ_RE.match(line)
        if not m:
            continue
        ver = m.group(4) or ""
        trailing = line[m.end() :].strip()
        if ver and (
            not _VER_RE.fullmatch(ver)
            or "," in line
            or (trailing not in ("", "\\") and not re.fullmatch(r"(?:--hash=[^\s]+\s*)+\\?", trailing))
        ):
            ver = ""
        out.append({"name": m.group(1), "version": ver, "pinned": bool(ver)})
    return out


def _parse_go_mod(text: str) -> list[dict]:
    reqs: list[dict] = []
    replaces: dict[str, tuple[str | None, str, str]] = {}  # old -> (old_ver|None, new, new_ver)
    block = None
    for raw in text.splitlines():
        code, _, comment = raw.partition("//")
        line = code.strip()
        if not line:
            continue
        if block and line == ")":
            block = None
            continue
        m = re.match(r"^(require|replace)\s*\(\s*$", line)
        if m:
            block = m.group(1)
            continue
        kind = block
        for k in ("require", "replace"):
            if line.startswith(k + " ") or line.startswith(k + "\t"):
                kind, line = k, line[len(k) :].strip()
        if kind == "require":
            parts = line.split()
            if len(parts) >= 2 and parts[1].startswith("v"):
                reqs.append({"name": parts[0], "version": parts[1], "pinned": True, "indirect": "indirect" in comment})
        elif kind == "replace" and "=>" in line:
            left, right = (x.split() for x in line.split("=>", 1))
            if left and right:
                replaces[left[0]] = (left[1] if len(left) > 1 else None, right[0], right[1] if len(right) > 1 else "")
    for r in reqs:
        rep = replaces.get(r["name"])
        if rep and (rep[0] is None or rep[0] == r["version"]):
            r["replaced_from"] = f"{r['name']}@{r['version']}"
            if rep[2]:
                r["name"], r["version"] = rep[1], rep[2]
            else:
                r["version"], r["pinned"], r["note"] = "", False, "replaced by local path"
    return reqs


def parse_manifest(text: str, manifest_type: str) -> list[dict]:
    """Parse direct declarations with pinned status, aliases and Go replacements.

    This does not resolve a lockfile or determine installed dependencies."""
    mt = (manifest_type or "").strip().lower() if isinstance(manifest_type, str) else ""
    if not isinstance(text, str):
        raise ApiError("invalid input: text must be a string")
    if len(text) > MAX_MANIFEST_BYTES:
        raise ApiError(f"invalid input: text exceeds {MAX_MANIFEST_BYTES} characters")
    parser = {
        "package.json": _parse_package_json,
        "requirements.txt": _parse_requirements,
        "go.mod": _parse_go_mod,
    }.get(mt)
    if not parser:
        raise ApiError("invalid input: manifest_type must be package.json, requirements.txt or go.mod")
    out = parser(text)
    if len(out) > MAX_MANIFEST_ENTRIES:
        raise ApiError(f"invalid input: more than {MAX_MANIFEST_ENTRIES} entries")
    return out


# ----------------------------------------------------------------- HTTP layer
def _q(x: str) -> str:
    return quote(x, safe="")


def _parse(resp: httpx.Response) -> Any:
    if resp.status_code == 404:
        raise ApiError("not found", 404)
    if not 200 <= resp.status_code < 300:
        raise ApiError(f"upstream http {resp.status_code}", resp.status_code)
    try:
        return resp.json()
    except ValueError:
        raise ApiError("non-JSON response from upstream", resp.status_code)


_capture = ContextVar("api_capture", default=None)


def _record(method: str, url: str, body, response):
    capture = _capture.get()
    if capture is not None:
        try:
            payload = response.json()
        except ValueError:
            payload = None
        capture.append(
            {"method": method, "url": url, "request": body, "status": response.status_code, "response": payload}
        )


def _retry_delay(response) -> float | None:
    """Honor Retry-After without blocking a review for an unbounded interval."""
    value = getattr(response, "headers", {}).get("Retry-After")
    delay = 0.25
    if value:
        try:
            if re.fullmatch(r"[0-9]+", value.strip()):
                delay = float(value)
            else:
                when = parsedate_to_datetime(value)
                if when.tzinfo is None:
                    when = when.replace(tzinfo=timezone.utc)
                delay = max(0.0, (when - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            pass
    return delay if delay <= MAX_RETRY_DELAY else None


def _request(method: str, url: str, body=None):
    """At most two attempts for reads, including OSV's read-only query POST."""
    try:
        guard_request(url, body)
    except PolicyBlocked as exc:
        raise ApiError(
            "request blocked by selected policy", extra={"code": "policy_blocked", "reason": exc.code}
        ) from exc
    for attempt in range(2):
        try:
            response = _client.get(url) if method == "GET" else _client.post(url, json=body)
        except (httpx.TimeoutException, httpx.NetworkError):
            if attempt:
                raise
            time.sleep(0.25)
            continue
        _record(method, url, body, response)
        delay = _retry_delay(response) if response.status_code in RETRY_STATUSES and not attempt else None
        if delay is None:
            return response
        time.sleep(delay)
    return response


def _get(url: str) -> dict:
    response = _request("GET", url)
    data = _parse(response)
    if not isinstance(data, dict):
        raise ApiError("unexpected upstream shape")
    return data


def _post(url: str, body: dict) -> dict:
    response = _request("POST", url, body)
    data = _parse(response)
    if not isinstance(data, dict):
        raise ApiError("unexpected upstream shape")
    return data


def _osv_batch(queries: list[tuple[str, str, str]]) -> tuple[list[list[str] | None], bool]:
    """Query OSV in batches. Failed or missing results are None, never zero."""
    out: list[list[str] | None] = []
    incomplete = False
    for i in range(0, len(queries), 500):
        chunk = queries[i : i + 500]
        body = {"queries": [{"package": {"name": n, "ecosystem": e}, "version": v} for e, n, v in chunk]}
        try:
            results = _as_list(_post(f"{OSV_BASE}/querybatch", body).get("results"))
        except (ApiError, httpx.HTTPError):
            out.extend([None] * len(chunk))
            incomplete = True
            continue
        for r in results[: len(chunk)]:
            if not isinstance(r, dict):
                incomplete = True
                out.append(None)
                continue
            if r.get("next_page_token"):
                incomplete = True
            vulns = r.get("vulns", [])
            if (
                r.get("error")
                or not isinstance(vulns, list)
                or any(not isinstance(v, dict) or not isinstance(v.get("id"), str) or not v["id"] for v in vulns)
            ):
                incomplete = True
                out.append(None)
                continue
            out.append(sorted({v["id"] for v in vulns}))
        if len(results) > len(chunk):
            incomplete = True
        if len(results) < len(chunk):
            incomplete = True
            out.extend([None] * (len(chunk) - len(results)))
    return out, incomplete


def _vkey(node: Any) -> dict:
    return _as_dict(_as_dict(node).get("versionKey"))


def _run(fn, *a, **kw) -> str:
    try:
        return json.dumps(fn(*a, **kw), ensure_ascii=False)
    except ApiError as e:
        body = {"error": e.message, "status": e.status}
        if e.hint:
            body["hint"] = e.hint
        body.update(e.extra or {})
        return json.dumps(body, ensure_ascii=False)
    except OSError:
        return json.dumps({"error": "local file operation failed", "status": None})
    except httpx.TimeoutException:
        return json.dumps({"error": "upstream timeout", "status": None}, ensure_ascii=False)
    except httpx.HTTPError:
        return json.dumps({"error": "network error", "status": None}, ensure_ascii=False)
    except (AttributeError, IndexError, RecursionError, TypeError, ValueError, KeyError) as e:
        return json.dumps({"error": f"invalid input: {type(e).__name__}", "status": None}, ensure_ascii=False)


# ----------------------------------------------------------------- pure aggregation helpers
def _label(n: dict) -> str:
    return f"{n.get('name')}@{n.get('version')}"


def summarize_dep_licenses(nodes: list[dict], edges: list[dict]) -> dict:
    """Copy nodes and compute license categories and shortest paths from SELF.

    Only queried nodes enter license totals. Unknown metadata is a review blocker.
    Input edges use fromNode/toNode indices; output edges use package@version labels."""
    nodes = [dict(_as_dict(n)) for n in _as_list(nodes)]
    adj: dict[int, list[int]] = {}
    edges_named: list[list[str]] = []
    for e in _dicts(edges):
        f, t = e.get("fromNode"), e.get("toNode")
        if isinstance(f, int) and isinstance(t, int) and 0 <= f < len(nodes) and 0 <= t < len(nodes):
            adj.setdefault(f, []).append(t)
            edges_named.append([_label(nodes[f]), _label(nodes[t])])
    root = next((i for i, n in enumerate(nodes) if n.get("relation") == "SELF"), None)
    prev: dict[int, int | None] = {}
    if root is not None:
        prev[root] = None
        dq = deque([root])
        while dq:
            cur = dq.popleft()
            for nxt in adj.get(cur, []):
                if nxt not in prev:
                    prev[nxt] = cur
                    dq.append(nxt)
    summary = {c: 0 for c in CATEGORIES}
    non_perm, failures, strictest = [], 0, None
    for i, n in enumerate(nodes):
        path = None
        if i in prev:
            path, cur = [], i
            while cur is not None:
                path.append(_label(nodes[cur]))
                cur = prev[cur]
            path.reverse()
        n["path"] = path
        if n.get("relation") == "SELF" or not n.get("licenses_queried", True):
            n["license_category"] = None
            continue
        if n.get("licenses") is None:
            cat = "unknown"
            if n.get("license_error"):
                failures += 1
        else:
            cat = classify_license(n.get("licenses"))["category"]
        n["license_category"] = cat
        summary[cat] += 1

        strictest = cat if strictest is None else max(strictest, cat, key=_SEV.get)
        if cat != "permissive":
            non_perm.append(
                {k: n.get(k) for k in ("name", "version", "relation", "licenses", "license_category", "path")}
            )
    known = [c for c in CATEGORIES if c != "unknown" and summary[c]]
    strictest_known = max(known, key=_SEV.get) if known else None
    non_perm.sort(key=lambda x: (-_SEV[x["license_category"]], str(x["name"])))
    vulnerable = [
        {
            "name": n.get("name"),
            "version": n.get("version"),
            "relation": n.get("relation"),
            "vuln_count": n.get("vuln_count"),
            "path": n.get("path"),
        }
        for n in nodes
        if isinstance(n.get("vuln_count"), int) and n.get("vuln_count") > 0
    ]
    vulnerable.sort(key=lambda x: (x["relation"] != "DIRECT", -x["vuln_count"], str(x["name"])))
    return {
        "nodes": nodes,
        "license_summary": summary,
        "non_permissive": non_perm,
        "strictest_category": strictest,
        "strictest_known_category": strictest_known,
        "license_lookup_failures": failures,
        "edges_named": edges_named,
        "vulnerable_nodes": vulnerable,
    }


def _osv_affected(osv: dict) -> tuple[list[dict], list[str], bool]:
    """Preserve ordered OSV affected-range events and collect reported fixes."""
    affected, fixed, has_eco = [], [], False
    for a in _dicts(osv.get("affected")):
        pk = _as_dict(a.get("package"))
        ranges = []
        for r in _dicts(a.get("ranges")):
            rtype = r.get("type")
            eco = rtype in ("ECOSYSTEM", "SEMVER")
            has_eco = has_eco or eco
            cur = None
            for ev in _dicts(r.get("events")):
                if "introduced" in ev:
                    if cur:
                        ranges.append(cur)
                    cur = {"type": rtype, "introduced": ev["introduced"], "fixed": None, "last_affected": None}
                elif "fixed" in ev or "last_affected" in ev:
                    cur = cur or {"type": rtype, "introduced": None, "fixed": None, "last_affected": None}
                    cur.update({k: ev[k] for k in ("fixed", "last_affected") if k in ev})
                    if eco and ev.get("fixed"):
                        fixed.append(f"{pk.get('name')}@{ev['fixed']}")
                    ranges.append(cur)
                    cur = None
            if cur:
                ranges.append(cur)
        affected.append({"ecosystem": pk.get("ecosystem"), "package": pk.get("name"), "ranges": ranges})
    return affected, fixed, has_eco


def _dedupe_ci(items: Any) -> list[str]:
    """Deduplicate strings case-insensitively while preserving the first spelling."""
    seen, out = set(), []
    for x in _as_list(items):
        if isinstance(x, str) and x and x.lower() not in seen:
            seen.add(x.lower())
            out.append(x)
    return out


def _related_project_ids(detail: dict) -> list[str]:
    """Deduplicate source and issue-tracker links to the same project."""
    return _dedupe_ci([_as_dict(p.get("projectKey")).get("id") for p in _dicts(detail.get("relatedProjects"))])


def _repo_candidates(detail: dict) -> list[str]:
    cands = _related_project_ids(detail)
    cands += [l.get("url") for l in _dicts(detail.get("links")) if "github.com/" in str(l.get("url", "")).lower()]
    out: list[str] = []
    for c in cands:
        try:
            r = normalize_repo(c) if isinstance(c, str) else ""
        except ApiError:
            continue
        if r.startswith("github.com/"):
            out.append(r[len("github.com/") :])
    return _dedupe_ci(out)


def _published_ts(v: dict) -> float:
    """Parse publishedAt as epoch seconds; unparseable dates sort last."""
    try:
        return datetime.fromisoformat(str(_as_dict(v).get("publishedAt", "")).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return float("-inf")


def _sorted_versions(versions: Any) -> list[tuple[float, dict]]:
    items = [(_published_ts(v), v) for v in _dicts(versions)]
    items.sort(key=lambda t: -t[0])
    return items


def older_versions(versions: list[dict], selected: str | None) -> list[str]:
    """Return strictly earlier publication dates, newest first; no semver inference."""
    items = _sorted_versions(versions)
    sel_ts = next((ts for ts, v in items if _vkey(v).get("version") == selected), float("-inf"))
    return [
        str(_vkey(v).get("version"))
        for ts, v in items
        if ts > float("-inf") and ts < sel_ts and _vkey(v).get("version")
    ]


def version_timeline(versions: list[dict], selected: str | None, limit: int = 8) -> dict:
    """Summarize recent versions and the previous publication, if known."""
    recent = [
        {
            "version": _vkey(v).get("version"),
            "published_at": v.get("publishedAt"),
            "is_default": v.get("isDefault") is True,
        }
        for _, v in _sorted_versions(versions)[:limit]
    ]
    older = older_versions(versions, selected)
    return {"recent_versions": recent, "previous_version": older[0] if older else None}


def pick_primary_package(project_id: str, packages: list[dict]) -> dict | None:
    """Suggest a package by source-name match then version count, excluding Go pseudo-packages.

    This heuristic is not proof of identity; review competing candidates."""
    pid = (project_id or "").lower()
    repo = pid.rsplit("/", 1)[-1]
    cands = [
        p
        for p in _dicts(packages)
        if not (str(p.get("system", "")).lower() == "go" and str(p.get("name", "")).lower() == pid)
    ]
    if not cands:
        return None
    matches = [p for p in cands if str(p.get("name", "")).lower().rsplit("/", 1)[-1] == repo]
    pool = matches or cands
    return max(pool, key=lambda p: p.get("versions") or 0)


# ----------------------------------------------------------------- advisory helpers (pure)
_CVSS_W = {
    "AV": {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2},
    "AC": {"L": 0.77, "H": 0.44},
    "UI": {"N": 0.85, "R": 0.62},
    "CIA": {"H": 0.56, "L": 0.22, "N": 0.0},
}


def cvss3_base_score(vector: Any) -> float | None:
    """Compute a CVSS v3.x base score using the CVSS 3.1 Roundup rule."""
    if not isinstance(vector, str) or not vector.upper().startswith("CVSS:3"):
        return None
    m = dict(p.split(":", 1) for p in vector.upper().split("/")[1:] if ":" in p)
    try:
        changed = m["S"] == "C"
        pr = {"N": 0.85, "L": 0.68 if changed else 0.62, "H": 0.5 if changed else 0.27}[m["PR"]]
        iss = 1 - (1 - _CVSS_W["CIA"][m["C"]]) * (1 - _CVSS_W["CIA"][m["I"]]) * (1 - _CVSS_W["CIA"][m["A"]])
        expl = 8.22 * _CVSS_W["AV"][m["AV"]] * _CVSS_W["AC"][m["AC"]] * pr * _CVSS_W["UI"][m["UI"]]
    except KeyError:
        return None
    impact = 7.52 * (iss - 0.029) - 3.25 * (iss - 0.02) ** 15 if changed else 6.42 * iss
    if impact <= 0:
        return 0.0
    raw = min((1.08 if changed else 1.0) * (impact + expl), 10.0)
    i = round(raw * 100000)
    return i / 100000.0 if i % 10000 == 0 else (i // 10000 + 1) / 10.0


def severity_label(score: Any) -> str | None:
    """Map a numeric CVSS score to severity; missing scores stay unknown."""
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        return None
    if score <= 0:
        return "none"
    return "Critical" if score >= 9.0 else "High" if score >= 7.0 else "Medium" if score >= 4.0 else "Low"


def canonical_id(ids: Any) -> str | None:
    """Prefer GHSA, then CVE, then ecosystem IDs; break ties lexicographically."""

    def rank(i: str) -> int:
        u = i.upper()
        return (
            0
            if u.startswith("GHSA-")
            else 1
            if u.startswith("CVE-")
            else 2
            if u.startswith(("PYSEC-", "GO-", "RUSTSEC-", "OSV-"))
            else 3
        )

    cands = [i for i in _as_list(list(ids) if isinstance(ids, (set, tuple)) else ids) if isinstance(i, str) and i]
    return min(cands, key=lambda i: (rank(i), i)) if cands else None


def _truncate(text: Any, limit: int) -> str | None:
    t = str(text) if text is not None else ""
    return (t if len(t) <= limit else t[:limit] + "…") or None


_REF_RANK = {"ADVISORY": 0, "FIX": 1, "REPORT": 2}


def _pick_references(refs: list[dict], limit: int = 6) -> list[dict]:
    seen, out = set(), []
    for r in refs:
        url = r.get("url")
        if isinstance(url, str) and url not in seen:
            seen.add(url)
            out.append({"type": r.get("type"), "url": url})
    out.sort(key=lambda r: _REF_RANK.get(str(r["type"]).upper(), 3))
    return out[:limit]


def _affected_summary(affected: list[dict]) -> list[dict]:
    return [
        {
            "ecosystem": a.get("ecosystem"),
            "package": a.get("package"),
            "introduced": r.get("introduced"),
            "fixed": r.get("fixed"),
        }
        for a in affected
        for r in _dicts(a.get("ranges"))
        if r.get("type") in ("ECOSYSTEM", "SEMVER")
    ]


# ----------------------------------------------------------------- tools
def _lookup_metadata(url, system, name, version, stage):
    """Explain lookup failures without turning registry existence into approval."""
    extra = {"source": "deps.dev", "lookup_stage": stage}
    try:
        return _get(url)
    except ApiError as error:
        if (error.extra or {}).get("code") == "policy_blocked":
            raise
        if error.status == 404:
            registry = check_registry(system, name, version, lambda address: _request("GET", address))
            extra["registry_check"] = registry
            state = registry["status"]
            if state == "found":
                extra["code"] = "depsdev_metadata_unavailable"
                hint = "The public registry confirms this target exists, but deps.dev metadata is unavailable. Retry later or review the sources manually; existence alone is not approval."
            elif state == "package_not_found":
                extra["code"] = state
                hint = f"The package was not found in public {registry['registry']}. Check the package name and ecosystem. Private/custom registries are not checked."
            elif state == "version_not_found":
                extra["code"] = state
                hint = f"The package exists in public {registry['registry']}, but the requested version was not found. Check the exact version; no other version was substituted."
            else:
                extra["code"] = "lookup_unresolved"
                hint = "deps.dev has no metadata for this target; registry existence could not be verified. Do not conclude that the package does not exist."
            raise ApiError("target not found in deps.dev", 404, hint, extra) from error
        extra["code"] = "upstream_rate_limited" if error.status == 429 else "upstream_lookup_failed"
        raise ApiError(
            error.message,
            error.status,
            "Try again later or check the upstream service. This lookup did not complete; it is not a clean review.",
            extra,
        ) from error
    except httpx.HTTPError as error:
        extra["code"] = "upstream_timeout" if isinstance(error, httpx.TimeoutException) else "upstream_network_error"
        raise ApiError(
            "upstream timeout" if isinstance(error, httpx.TimeoutException) else "network error",
            None,
            "Check connectivity and try again later. Registry existence was not checked because deps.dev did not return a not-found response.",
            extra,
        ) from error


def _lookup_package(system: str, name: str, version: str) -> dict:
    sysn, name = norm_system(system), _seg(name, "name")
    version = version.strip() if isinstance(version, str) else ""
    if version:
        version = _seg(version, "version")
    pkg = _lookup_metadata(f"{DEPSDEV_BASE}/systems/{sysn}/packages/{_q(name)}", sysn, name, version, "package")
    versions = _dicts(pkg.get("versions"))
    default = next((v for v in versions if v.get("isDefault") is True), None)
    latest = _vkey(default).get("version") if default else None
    if latest is None:
        dated = [v for v in versions if _published_ts(v) > float("-inf")]
        latest = _vkey(max(dated, key=_published_ts)).get("version") if dated else None
    ver = version or latest
    if not ver:
        raise ApiError(
            "package has no resolvable default version",
            404,
            "Specify an exact version. deps.dev returned package metadata but no usable default version.",
            {"code": "version_unresolved", "source": "deps.dev"},
        )
    ver = _seg(ver, "version")
    det = _lookup_metadata(
        f"{DEPSDEV_BASE}/systems/{sysn}/packages/{_q(name)}/versions/{_q(ver)}", sysn, name, ver, "version"
    )
    if _vkey(det).get("version") != ver:
        raise ApiError("version mismatch from upstream")
    licenses = _strs(det.get("licenses"))
    related = _related_project_ids(det)
    description = homepage = None
    if related:
        proj = _try_get(f"{DEPSDEV_BASE}/projects/{_q(related[0])}", [])
        if proj:
            description, homepage = proj.get("description") or None, proj.get("homepage") or None
    return {
        "system": sysn,
        "name": _vkey(det).get("name") or name,
        "version": ver,
        "is_default": det.get("isDefault") is True,
        "published_at": det.get("publishedAt"),
        "description": description,
        "homepage": homepage,
        "licenses": licenses,
        "license_policy": classify_license(licenses),
        "advisories": [a.get("id") for a in _dicts(det.get("advisoryKeys")) if a.get("id")],
        "related_projects": related,
        "repo_candidates": _repo_candidates(det),
        "links": _dicts(det.get("links")),
        "total_versions": len(versions),
        "latest_version": latest,
        **version_timeline(versions, ver),
    }


def _fetch_licenses(sysn: str, name: str, version: str) -> tuple[list[str] | None, str | None]:
    try:
        det = _get(f"{DEPSDEV_BASE}/systems/{sysn}/packages/{_q(name)}/versions/{_q(version)}")
        return _strs(det.get("licenses")), None
    except ApiError as e:
        return None, e.message
    except httpx.HTTPError as e:
        return None, type(e).__name__


def _fetch_graph(sysn: str, name: str, version: str) -> dict | None:
    """Return a resolved graph or None for HTTP 404. Propagate other errors."""
    try:
        return _get(f"{DEPSDEV_BASE}/systems/{sysn}/packages/{_q(name)}/versions/{_q(version)}:dependencies")
    except ApiError as e:
        if e.status == 404:
            return None
        raise


def _get_dependencies(
    system: str,
    name: str,
    version: str,
    include_vulns: bool,
    include_licenses: bool,
    max_nodes: int,
    fallback_to_previous: bool = False,
) -> dict:
    sysn, name, requested = norm_system(system), _seg(name, "name"), _seg(version, "version")
    if not isinstance(max_nodes, int) or isinstance(max_nodes, bool) or not 1 <= max_nodes <= 2000:
        raise ApiError("invalid input: max_nodes must be between 1 and 2000")
    resolved, tried = requested, []
    data = _fetch_graph(sysn, name, requested)
    if data is None and fallback_to_previous:
        try:
            pkg = _get(f"{DEPSDEV_BASE}/systems/{sysn}/packages/{_q(name)}")
        except ApiError as e:
            if e.status == 404:
                raise ApiError("not found", 404, GRAPH_404_HINT, {"fallback_tried": []})
            raise
        for cand in older_versions(_dicts(pkg.get("versions")), requested)[:MAX_FALLBACK_ATTEMPTS]:
            data = _fetch_graph(sysn, name, cand)
            if data is not None:
                resolved = cand
                break
            tried.append(cand)
    if data is None:
        raise ApiError("not found", 404, GRAPH_404_HINT, {"fallback_tried": tried} if fallback_to_previous else None)
    version = resolved
    raw = _dicts(data.get("nodes"))
    nodes = [
        {
            "name": _vkey(n).get("name"),
            "version": _vkey(n).get("version"),
            "relation": n.get("relation"),
            "vuln_count": None,
            "vuln_ids": None,
            "vulns_queried": False,
            "licenses": None,
            "license_category": None,
            "license_error": None,
            "licenses_queried": False,
            "path": None,
        }
        for n in raw
    ]
    idx = [i for i, n in enumerate(nodes) if n["relation"] != "SELF"]
    truncated = len(idx) > max_nodes
    if truncated:
        idx = [i for i in idx if nodes[i]["relation"] == "DIRECT"][:max_nodes]
    osv_incomplete = False
    if include_licenses and idx:
        keys = sorted({(nodes[i]["name"], nodes[i]["version"]) for i in idx}, key=str)
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(copy_context().run, _fetch_licenses, sysn, str(k[0]), str(k[1])) for k in keys]
            fetched = dict(zip(keys, (future.result() for future in futures)))
        for i in idx:
            lic, err = fetched[(nodes[i]["name"], nodes[i]["version"])]
            nodes[i].update(licenses=lic, license_error=err, licenses_queried=True)
    if include_vulns and idx:
        eco = osv_ecosystem(sysn)
        results, osv_incomplete = _osv_batch([(eco, str(nodes[i]["name"]), str(nodes[i]["version"])) for i in idx])
        for i, vids in zip(idx, results):
            if vids is not None:
                nodes[i].update(vuln_count=len(vids), vuln_ids=vids, vulns_queried=True)
    agg = summarize_dep_licenses(nodes, _dicts(data.get("edges")))
    counts = {
        "total": len(nodes),
        "direct": sum(1 for n in nodes if n["relation"] == "DIRECT"),
        "indirect": sum(1 for n in nodes if n["relation"] == "INDIRECT"),
    }
    return {
        "system": sysn,
        "name": name,
        "version": version,
        "requested_version": requested,
        "resolved_version": resolved,
        "fallback_used": resolved != requested,
        "fallback_attempts": len(tried) + (1 if resolved != requested else 0),
        "fallback_tried": tried,
        "counts": counts,
        "nodes": agg["nodes"],
        "nodes_with_errors": [_vkey(n).get("name") for n in raw if n.get("errors")],
        "truncated": truncated,
        "include_vulns": include_vulns,
        "include_licenses": include_licenses,
        "osv_incomplete": osv_incomplete,
        "graph_error": data.get("error") or None,
        "license_summary": agg["license_summary"] if include_licenses else None,
        "non_permissive": agg["non_permissive"] if include_licenses else None,
        "strictest_category": agg["strictest_category"] if include_licenses else None,
        "strictest_known_category": agg.get("strictest_known_category") if include_licenses else None,
        "license_lookup_failures": agg["license_lookup_failures"] if include_licenses else None,
        "edges_named": agg["edges_named"],
        "vulnerable_nodes": agg["vulnerable_nodes"],
    }


def _try_get(url: str, errors: list[str]) -> dict | None:
    try:
        return _get(url)
    except ApiError as e:
        if e.status != 404:
            errors.append(e.message)
    except httpx.HTTPError as e:
        errors.append(type(e).__name__)
    return None


def _get_advisory(adv_id: str) -> dict:
    aid = _seg(adv_id, "id")
    errors: list[str] = []
    dd = _try_get(f"{DEPSDEV_BASE}/advisories/{_q(aid)}", errors)
    osv = _try_get(f"{OSV_BASE}/vulns/{_q(aid)}", errors)
    if dd is None and osv is None:
        raise ApiError("upstream error: " + "; ".join(errors), None) if errors else ApiError("not found", 404)
    dd, osv = dd or {}, osv or {}
    sources = [s for s, ok in (("deps.dev", bool(dd)), ("osv.dev", bool(osv))) if ok]
    aliases = set(_strs(dd.get("aliases"))) | set(_strs(osv.get("aliases")))
    affected, fixed, has_eco = _osv_affected(osv)
    note, alias_rec = None, None
    if not has_eco:
        alias = next((a for a in sorted(aliases) if re.match(r"^(GHSA|PYSEC|GO|RUSTSEC)-", a)), None)
        alias_rec = _try_get(f"{OSV_BASE}/vulns/{_q(alias)}", errors) if alias else None
        if alias_rec:
            a2, f2, has_eco = _osv_affected(alias_rec)
            affected, fixed = affected + a2, fixed + f2
            aliases |= set(_strs(alias_rec.get("aliases")))
            sources.append(f"osv.dev:{alias}")
    vector = dd.get("cvss3Vector") or next(
        (s.get("score") for s in _dicts(osv.get("severity")) if str(s.get("type", "")).startswith("CVSS_V3")), None
    )
    if not has_eco:
        note = "no ecosystem ranges; only GIT ranges" if affected else "no affected ranges available"
    alias_rec = alias_rec or {}
    score, score_source = dd.get("cvss3Score"), None
    vector_score = cvss3_base_score(vector)
    # deps.dev may return zero with an empty vector when CVSS v3 is absent.
    # Only a valid zero-impact vector can establish a real zero score.
    if (
        isinstance(score, (int, float))
        and not isinstance(score, bool)
        and 0 <= score <= 10
        and (score > 0 or vector_score == 0)
    ):
        score_source = "deps.dev"
    else:
        score = vector_score
        score_source = "computed_from_vector" if score is not None else None
    rid = _as_dict(dd.get("advisoryKey")).get("id") or osv.get("id") or aid
    return {
        "id": rid,
        "canonical_id": canonical_id(aliases | {rid}),
        "title": dd.get("title") or osv.get("summary"),
        "summary": osv.get("summary") or dd.get("title"),
        "details": _truncate(osv.get("details") or alias_rec.get("details") or "", 1800),
        "severity_label": severity_label(score),
        "cvss3_score": score,
        "cvss3_score_source": score_source,
        "cvss3_vector": vector,
        "aliases": sorted(aliases - {aid}),
        "url": dd.get("url") or f"https://osv.dev/vulnerability/{aid}",
        "references": _pick_references(_dicts(osv.get("references")) + _dicts(alias_rec.get("references"))),
        "published": osv.get("published"),
        "modified": osv.get("modified"),
        "affected": affected,
        "affected_summary": _affected_summary(affected),
        "fixed_versions": sorted(set(fixed)) if has_eco else None,
        "note": note,
        "sources": sources,
        "source_errors": errors or None,
    }


def _get_project(repo: str) -> dict:
    pid = normalize_repo(repo)
    proj = _get(f"{DEPSDEV_BASE}/projects/{_q(pid)}")
    sc = _as_dict(proj.get("scorecard")) or None
    packages: dict[tuple[str, str], dict] = {}
    pv_error = None
    try:
        pv = _get(f"{DEPSDEV_BASE}/projects/{_q(pid)}:packageversions")
        for v in _dicts(pv.get("versions")):
            vk = _vkey(v)
            key = (str(vk.get("system", "")).lower(), str(vk.get("name", "")))
            ent = packages.setdefault(
                key, {"system": key[0], "name": key[1], "versions": 0, "relation_type": v.get("relationType")}
            )
            ent["versions"] += 1
    except ApiError as e:
        pv_error = e.message
    pkgs = sorted(packages.values(), key=lambda p: (p["system"], p["name"]))
    return {
        "project": pid,
        "license": proj.get("license"),
        "stars": proj.get("starsCount"),
        "forks": proj.get("forksCount"),
        "open_issues": proj.get("openIssuesCount"),
        "description": proj.get("description"),
        "homepage": proj.get("homepage"),
        "scorecard": None
        if not sc
        else {
            "date": sc.get("date"),
            "overall": sc.get("overallScore"),
            "checks": [
                {"name": c.get("name"), "score": c.get("score"), "reason": _truncate(c.get("reason"), 200)}
                for c in _dicts(sc.get("checks"))
            ],
        },
        "primary_package": pick_primary_package(pid, pkgs),
        "packages": pkgs,
        "packages_error": pv_error,
    }


def _audit_manifest(text: str, manifest_type: str) -> dict:
    parsed = parse_manifest(text, manifest_type)
    mt = manifest_type.strip().lower()
    eco = {"package.json": "npm", "requirements.txt": "PyPI", "go.mod": "Go"}[mt]
    usable = [e for e in parsed if e["version"] and e["pinned"]]
    skipped = [
        {"name": e["name"], "note": e.get("note") or "no exact version; skipped"}
        for e in parsed
        if not e["version"] or not e["pinned"]
    ]
    results, incomplete = _osv_batch([(eco, e["name"], e["version"]) for e in usable]) if usable else ([], False)
    pkgs = []
    for e, vids in zip(usable, results):
        pkgs.append(
            {
                **e,
                "vuln_count": None if vids is None else len(vids),
                "vuln_ids": vids,
                "vulns_queried": vids is not None,
            }
        )
    ignored_lines = []
    if mt == "requirements.txt":
        ignored_lines = [
            i
            for i, line in enumerate(text.splitlines(), 1)
            if line.strip()
            and not line.lstrip().startswith("#")
            and (line.lstrip().startswith("-") or not _REQ_RE.match(line.strip()))
        ]
    return {
        "scope": "declared direct dependencies only; markers not evaluated; no lockfile resolution",
        "ignored_line_numbers": ignored_lines,
        "manifest_type": mt,
        "ecosystem": eco,
        "packages": pkgs,
        "skipped": skipped,
        "osv_incomplete": incomplete,
        "summary": {
            "packages": len(pkgs),
            "with_vulns": sum(1 for p in pkgs if p["vuln_count"]),
            "skipped": len(skipped),
        },
    }
