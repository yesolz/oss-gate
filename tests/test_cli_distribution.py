"""Exercise the CLI distribution from a standalone installed-like directory."""

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("cli_builder", ROOT / "scripts/build_cli_plugin.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class CLIDistribution(unittest.TestCase):
    def test_generated_package_and_marketplaces_match(self):
        builder.build(check=True)
        plugin = ROOT / "plugins/oss-gate-cli"
        self.assertFalse((plugin / "mcp.json").exists())
        self.assertFalse((plugin / ".mcp.json").exists())
        self.assertFalse((plugin / "mcp").exists())
        for file in ("plugin.json", ".claude-plugin/plugin.json"):
            manifest = json.loads((plugin / file).read_text())
            self.assertEqual(manifest["name"], "oss-gate-cli")
            self.assertNotIn("mcpServers", manifest)
            self.assertNotIn("mcp", manifest)
        for file in (".agents/plugins/marketplace.json", ".claude-plugin/marketplace.json"):
            manifest = json.loads((ROOT / file).read_text())
            self.assertEqual({p["name"] for p in manifest["plugins"]}, {"oss-gate", "oss-gate-cli"})
        # Demonstrate that stale or accidentally registered MCP files fail the gate.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(
                ROOT / "plugins/oss-gate",
                root / "plugins/oss-gate",
                ignore=shutil.ignore_patterns(".venv", "__pycache__"),
            )
            builder.build(root=root)
            (root / "plugins/oss-gate-cli/.mcp.json").write_text('{"mcpServers":{}}')
            with self.assertRaises(ValueError):
                builder.build(check=True, root=root)

    def test_standalone_cli_plan_block_and_bilingual_render(self):
        with tempfile.TemporaryDirectory(prefix="oss gate isolated ") as tmp:
            root = Path(tmp)
            plugin = root / "installed"
            shutil.copytree(
                ROOT / "plugins/oss-gate-cli", plugin, ignore=shutil.ignore_patterns(".venv", "__pycache__")
            )
            env = {**os.environ, "PYTHONPATH": ""}
            env.pop("OSS_GATE_POLICY", None)

            def run(*args):
                return subprocess.run(
                    [sys.executable, str(plugin / "cli.py"), *args],
                    cwd=root,
                    env=env,
                    text=True,
                    capture_output=True,
                    timeout=30,
                )

            planned = run("plan", "npm", "demo", "--version", "1.0.0")
            self.assertEqual(planned.returncode, 0, planned.stderr)
            self.assertFalse(json.loads(planned.stdout)["network_performed"])
            policy = root / "settings.json"
            policy.write_text(
                json.dumps(
                    {
                        "schema": "oss-gate.settings/1",
                        "name": "Offline test",
                        "version": "1",
                        "network": {"services": []},
                    }
                )
            )
            blocked = run(
                "--policy",
                str(policy),
                "collect",
                "npm",
                "demo",
                "--version",
                "1.0.0",
                "--output-root",
                str(root / "reviews"),
            )
            self.assertEqual(blocked.returncode, 1)
            self.assertEqual(json.loads(blocked.stdout)["code"], "policy_blocked")
            self.assertFalse((root / "reviews").exists())
            review = root / "saved review"
            shutil.copytree(ROOT / "examples/reviews/psf-requests-2.34.2", review)
            for lang in ("ko", "en"):
                (review / f"report.{lang}.html").unlink()
            rendered = run("render", str(review), "--language", "both")
            self.assertEqual(rendered.returncode, 0, rendered.stderr)
            for lang in ("ko", "en"):
                html = (review / f"report.{lang}.html").read_text(encoding="utf-8")
                self.assertIn(f'lang="{lang}"', html)
                self.assertIn("requests", html)
