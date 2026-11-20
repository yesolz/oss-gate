"""Collect version-specific public evidence and preserve normalized and raw responses."""

from datetime import datetime, timezone
import json
from pathlib import Path

from core.policy import evaluate
from core.settings import CURRENT, EVENTS, fingerprint
from core.additional_policy import validate_communication
from core.snapshot import new_run, seal, write_json


def collect(server, system, name, version="", repo="", output_root="reviews", communication_path=""):
    communication = None
    if communication_path:
        source = Path(communication_path)
        if not source.is_absolute() or source.stat().st_size > 512_000:
            raise ValueError("communication evidence requires an absolute path and at most 512000 bytes")
        communication = validate_communication(json.loads(source.read_text(encoding="utf-8")))
    calls = []
    token = server._capture.set(calls)
    try:

        def call(fn, *args):
            return json.loads(server._run(fn, *args))

        lp = call(server._lookup_package, system, name, version)
        if lp.get("error"):
            return lp
        target = {
            "system": lp["system"],
            "name": lp["name"],
            "version": lp["version"],
            "repo": repo or next(iter(lp.get("repo_candidates") or []), ""),
        }
        gd = call(server._get_dependencies, target["system"], target["name"], target["version"], True, True, 200, False)
        root_results, root_incomplete = server._osv_batch(
            [(server.osv_ecosystem(target["system"]), target["name"], target["version"])]
        )
        root_ids = root_results[0] if root_results else None
        ids = set(lp.get("advisories") or []) | set(root_ids or [])
        for node in gd.get("nodes") or []:
            ids.update(node.get("vuln_ids") or [])
        # The cap is explicit in evidence and forces an incomplete-data verdict.
        selected_ids = sorted(ids)[:200]
        adv = {aid: call(server._get_advisory, aid) for aid in selected_ids}
        gp = call(server._get_project, target["repo"]) if target["repo"] else None
        data = {
            "schema": "oss-gate.review/2",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "target": target,
            "lookup_package": lp,
            "get_dependencies": gd,
            "root_osv": {"ids": root_ids, "queried": root_ids is not None, "incomplete": root_incomplete},
            "advisories": adv,
            "get_project": gp,
            "get_project_fallback": None,
            "advisories_truncated": len(ids) > len(selected_ids),
            "deepwiki": None,
            "evidence_note": "Normalized API fields. Unabridged successful JSON responses and HTTP error JSON are in api-responses.json. Network failures appear in normalized error fields.",
        }
        if communication is not None:
            if communication["target"] != {k: target[k] for k in ("system", "name", "version")}:
                raise ValueError("communication evidence does not match the reviewed target")
            data["communication"] = communication
        config = CURRENT.get()
        if config is not None:
            data["policy_context"] = {
                "schema": "oss-gate.policy-context/1",
                "config": config,
                "sha256": fingerprint(config),
                "evaluated_at": data["generated_at"],
            }
            data["network_decisions"] = list(EVENTS.get() or [])
        data["verdict"] = evaluate(data)
        folder = new_run(output_root, target["name"], target["version"])
        write_json(folder / "data.json", data)
        write_json(folder / "api-responses.json", calls)
        seal(folder, ["data.json", "api-responses.json"])
        return {
            "folder": str(folder),
            "data": str(folder / "data.json"),
            "verdict": data["verdict"],
            "target": target,
            "direct_dependencies": [n["name"] for n in gd.get("nodes", []) if n.get("relation") == "DIRECT"],
            "note": "Read the saved data. Add DeepWiki responses in a separate file; do not modify sealed evidence.",
        }
    finally:
        server._capture.reset(token)
