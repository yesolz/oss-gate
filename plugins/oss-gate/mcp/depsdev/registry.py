"""Narrow existence checks against public registries, never substitute review evidence."""

import re
from urllib.parse import quote

import httpx


def check_registry(system, name, version, get):
    """Check npm/PyPI after a deps.dev miss, using at most two distinct URLs.

    `get` supplies the shared bounded HTTP retry policy. Redirects, malformed
    metadata and transport failures leave existence unverified.
    """
    if system not in ("npm", "pypi"):
        return {"status": "unsupported", "reason": "No public registry check for this ecosystem."}

    def normalize(value):
        if not isinstance(value, str):
            return None
        return re.sub(r"[-_.]+", "-", value).lower() if system == "pypi" else value

    encoded = quote(name, safe="")
    package_url = (
        f"https://registry.npmjs.org/{encoded}" if system == "npm" else f"https://pypi.org/pypi/{encoded}/json"
    )
    version_url = (
        f"{package_url}/{quote(version, safe='')}"
        if system == "npm"
        else f"https://pypi.org/pypi/{encoded}/{quote(version, safe='')}/json"
    )
    result = {"registry": "npm" if system == "npm" else "PyPI", "status": "unverified", "checks": []}

    def probe(url, expected_version=""):
        check = {"url": url, "status": None}
        result["checks"].append(check)
        try:
            response = get(url)
            check["status"] = response.status_code
            if response.status_code == 404:
                return "missing"
            if response.status_code != 200:
                check["reason"] = "Registry did not return successful metadata."
                return "unknown"
            payload = response.json()
            metadata = payload.get("info") if system == "pypi" and isinstance(payload, dict) else payload
            if (
                not isinstance(metadata, dict)
                or normalize(metadata.get("name")) != normalize(name)
                or (expected_version and metadata.get("version") != expected_version)
            ):
                check["reason"] = "Registry metadata does not identify the exact requested target."
                return "unknown"
            return "found"
        except (httpx.HTTPError, ValueError):
            check["reason"] = "Registry request failed or returned invalid JSON."
            return "unknown"

    if version:
        state = probe(version_url, version)
        if state == "found":
            result["status"] = "found"
            return result
        if state != "missing":
            return result
    state = probe(package_url)
    if state == "missing":
        result["status"] = "package_not_found"
    elif state == "found":
        result["status"] = "version_not_found" if version else "found"
    return result
