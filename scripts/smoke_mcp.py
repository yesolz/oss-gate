"""Test stdio discovery locally; opt into public API and DeepWiki calls with --live."""

import argparse
import asyncio
import json
import shutil
import sys
import tempfile
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

ROOT = Path(__file__).resolve().parents[1]


async def run(live=False):
    uv = shutil.which("uv")
    if not uv:
        raise RuntimeError("uv is required")
    plugin = ROOT / "plugins/oss-gate"
    params = StdioServerParameters(
        command=uv, args=["run", "--frozen", "--project", str(plugin), "python", str(plugin / "mcp/depsdev/server.py")]
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            names = {t.name for t in (await session.list_tools()).tools}
            assert names == {
                "lookup_package",
                "get_dependencies",
                "get_advisory",
                "get_project",
                "audit_manifest",
                "collect_review",
            }, names
            result = await session.call_tool("lookup_package", {"system": "unsupported", "name": "demo"})
            assert "unsupported system" in result.content[0].text
            print("PASS: stdio initialize, six tools, validation error round-trip")
            if live:
                result = await session.call_tool(
                    "lookup_package", {"system": "pypi", "name": "requests", "version": "2.25.1"}
                )
                data = json.loads(result.content[0].text)
                assert data.get("version") == "2.25.1" and data.get("licenses"), data
                print("PASS: deps.dev version-specific metadata")
                result = await session.call_tool(
                    "audit_manifest", {"text": "requests==2.25.1", "manifest_type": "requirements.txt"}
                )
                data = json.loads(result.content[0].text)
                assert data["packages"][0]["vulns_queried"] is True and data["packages"][0]["vuln_count"] > 0, data
                print("PASS: OSV known vulnerable pin")
                with tempfile.TemporaryDirectory(prefix="oss-gate-live-") as output:
                    result = await session.call_tool(
                        "collect_review",
                        {"system": "pypi", "name": "requests", "version": "2.25.1", "output_root": output},
                    )
                    data = json.loads(result.content[0].text)
                    assert "folder" in data, data
                    sys.path.insert(0, str(plugin))
                    from core.snapshot import load_review

                    snapshot = load_review(Path(data["folder"]) / "data.json")
                    assert snapshot["target"]["version"] == "2.25.1"
                    assert snapshot["root_osv"]["queried"] is True
                    assert snapshot["verdict"]["overall"] != "allow"
                    assert (Path(data["folder"]) / "api-responses.json").stat().st_size > 0
                    print("PASS: live collector, raw evidence, integrity hashes and non-approval of vulnerable pin")
    if live:
        async with streamablehttp_client("https://mcp.deepwiki.com/mcp") as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                names = {t.name for t in (await session.list_tools()).tools}
                assert "read_wiki_structure" in names
                result = await session.call_tool("read_wiki_structure", {"repoName": "psf/requests"})
                assert not result.isError
                print("PASS: DeepWiki discovery and public repository structure")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.live))
