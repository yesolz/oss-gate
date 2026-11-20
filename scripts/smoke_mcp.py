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
    params = StdioServerParameters(
        command=uv, args=["run", "--frozen", "--project", str(plugin), "python", str(plugin / "mcp/deepwiki/server.py")]
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            names = {t.name for t in (await session.list_tools()).tools}
            assert names == {"read_wiki_structure", "read_wiki_contents", "ask_question"}
            result = await session.call_tool("ask_question", {"repoName": "owner/repo", "topic": "invalid"})
            assert json.loads(result.content[0].text)["code"] == "invalid_input"
            print("PASS: local DeepWiki discovery and offline validation")
            if live:
                result = await session.call_tool("read_wiki_structure", {"repoName": "psf/requests"})
                data = json.loads(result.content[0].text)
                assert not data.get("error") and not data.get("isError") and data["content"], data
                print("PASS: controlled DeepWiki public repository structure")
    with tempfile.TemporaryDirectory(prefix="oss-gate-policy-smoke-") as tmp:
        policy = Path(tmp) / "settings.json"
        policy.write_text(
            json.dumps(
                {
                    "schema": "oss-gate.settings/1",
                    "name": "Smoke policy",
                    "version": "1",
                    "network": {"services": []},
                }
            ),
            encoding="utf-8",
        )
        for adapter, tool, arguments in [
            ("depsdev", "lookup_package", {"system": "npm", "name": "demo", "version": "1.0.0"}),
            ("deepwiki", "ask_question", {"repoName": "owner/repo"}),
        ]:
            params = StdioServerParameters(
                command=uv,
                args=["run", "--frozen", "--project", str(plugin), "python", str(plugin / f"mcp/{adapter}/server.py")],
                env={"OSS_GATE_POLICY": str(policy)},
            )
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool, arguments)
                    assert json.loads(result.content[0].text)["code"] == "policy_blocked"
        print("PASS: both MCP adapters enforce launch-selected policy")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.live))
