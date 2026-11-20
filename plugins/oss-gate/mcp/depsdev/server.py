"""MCP adapter for the shared OSS Gate service."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mcp.server.fastmcp import FastMCP
from core.service import invoke

mcp = FastMCP("depsdev")


@mcp.tool()
def lookup_package(system: str, name: str, version: str = "") -> str:
    """Read metadata for one public package version from deps.dev.

    Supports npm, pypi, go, maven, cargo, nuget and rubygems. An empty version
    selects the registry default or newest dated publication. Returns licenses,
    license_policy, advisories, repository candidates, links and release timeline.
    Unknown licenses are review questions, not proof of a license violation.
    Errors have error/status; upstream lookup failures add a code and hint. On a deps.dev 404,
    npm/PyPI registries are checked for existence only, not approval. A configured npm mirror
    replaces public npm; its absence result applies only to that mirror.
    Other ecosystems remain unverified; a 404 is not proof of nonexistence."""
    return invoke("lookup_package", system, name, version)


@mcp.tool()
def get_dependencies(
    system: str,
    name: str,
    version: str,
    include_vulns: bool = True,
    include_licenses: bool = True,
    max_nodes: int = 200,
    fallback_to_previous: bool = False,
) -> str:
    """Read the resolved dependency graph and query node licenses and OSV records.

    Returns nodes, edges_named, counts, paths and explicit completeness flags.
    max_nodes must be 1..2000; unqueried node values are null, not zero.
    The default is 200. Optional fallback checks at most eight earlier publications.
    When fallback_used is true, ALL graph facts describe resolved_version, not
    requested_version. That graph cannot approve the requested version.
    Check truncated, graph_error, nodes_with_errors, osv_incomplete and
    license_lookup_failures. A registry graph can differ from a local lockfile."""
    return invoke(
        "get_dependencies", system, name, version, include_vulns, include_licenses, max_nodes, fallback_to_previous
    )


@mcp.tool()
def get_advisory(id: str) -> str:
    """Read one vulnerability advisory from deps.dev and OSV, following one ecosystem alias when needed.

    Returns id/canonical_id/aliases, score/vector, summary, affected ranges,
    references, timestamps, sources and source_errors. Narrative is capped at
    1800 characters and references at six; collect_review preserves full API JSON.
    fixed_versions spans multiple packages and branches: do not recommend one
    without matching ecosystem, package and applicable range."""
    return invoke("get_advisory", id)


@mcp.tool()
def get_project(repo: str) -> str:
    """Read project metadata, Scorecard, package candidates and a heuristic primary_package.

    Accept owner/repo or a GitHub URL. Scorecard has date/overall/checks; missing
    data is null and unevaluated checks may be -1. Reasons are capped at 200
    characters. Candidate ranking is not a verified package-to-repository identity."""
    return invoke("get_project", repo)


@mcp.tool()
def audit_manifest(text: str, manifest_type: str) -> str:
    """Check exact direct dependency declarations with OSV. Does not resolve versions.

    Supports package.json (dependencies/dev/peer/optional), requirements.txt
    (exact == pins only) and go.mod (require and replace). Ranges, wildcard pins
    and local replacements are skipped. Limits: 512000 characters, 2000 entries.
    Returns packages, skipped, osv_incomplete and counts. Network failure stays
    unknown. Environment markers are not evaluated; this is not an installed-environment scan."""
    return invoke("audit_manifest", text, manifest_type)


@mcp.tool()
def collect_review(
    system: str,
    name: str,
    version: str = "",
    repo: str = "",
    output_root: str = "reviews",
    communication_path: str = "",
) -> str:
    """Collect public package evidence and WRITE a new local review folder.

    Reads deps.dev and OSV, saves data.json, api-responses.json and SHA-256 manifest.
    No overwrite, source code upload, execution of package code, or external write.
    output_root is a user-chosen local folder. Version defaults to the registry default.
    Use this for reproducible reviews; DeepWiki is collected separately by the agent.
    """
    return invoke("collect_review", system, name, version, repo, output_root, communication_path)


if __name__ == "__main__":
    mcp.run()
