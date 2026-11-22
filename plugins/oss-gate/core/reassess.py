"""Reassess verified saved evidence without requests or rewriting the source snapshot."""

import shutil
from datetime import datetime, timezone
from pathlib import Path

from .policy import evaluate
from .settings import fingerprint, load_policy
from .snapshot import load_review, new_run, seal, sha256, verify, write_json


def reassess(source, output_root, policy_path=None):
    path = Path(source)
    if path.is_dir():
        path = path / "data.json"
    manifest = verify(path.parent)
    data = load_review(path)
    config = load_policy(policy_path)
    if config is None:
        raise ValueError("reassessment requires an explicitly selected policy")
    data = {
        **data,
        "policy_context": {
            "schema": "oss-gate.policy-context/1",
            "config": config,
            "sha256": fingerprint(config),
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        },
        "reassessment": {
            "source_sha256": sha256(path),
            "network_performed": False,
            "previous_policy": data.get("verdict", {}).get("policy"),
        },
    }
    data["verdict"] = evaluate(data)
    folder = new_run(output_root, data["target"]["name"], data["target"]["version"])
    write_json(folder / "data.json", data)
    shutil.copyfile(path, folder / "source-data.json")
    files = ["data.json", "source-data.json"]
    # Historical response files are copied only if verified by the source manifest.
    if "api-responses.json" in manifest:
        shutil.copyfile(path.parent / "api-responses.json", folder / "api-responses.json")
        files.append("api-responses.json")
    seal(folder, files)
    return {
        "folder": str(folder),
        "verdict": data["verdict"],
        "network_performed": False,
        "note": "Write a new narrative from this evaluation before rendering; the source review is unchanged.",
    }
