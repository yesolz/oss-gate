"""Create evidence files without overwriting earlier runs."""

from __future__ import annotations
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def new_run(root, name, version):
    root = Path(root).expanduser().resolve()
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", f"{name}-{version}").strip(".-")[:120] or "review"
    folder = root / slug / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8])
    folder.mkdir(parents=True, exist_ok=False)
    return folder


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as out:
        json.dump(value, out, ensure_ascii=False, indent=2, allow_nan=False)
        out.write("\n")


def seal(folder, filenames):
    folder = Path(folder)
    manifest = {name: sha256(folder / name) for name in filenames}
    write_json(folder / "evidence-sha256.json", manifest)
    return manifest


def verify(folder):
    folder = Path(folder).resolve()
    manifest = json.loads((folder / "evidence-sha256.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or "data.json" not in manifest:
        raise ValueError("invalid evidence manifest")
    for name, expected in manifest.items():
        file = (folder / name).resolve()
        if file.parent != folder or not file.is_file() or sha256(file) != expected:
            raise ValueError(f"evidence integrity check failed: {name}")
    return manifest


def load_review(path):
    """Read verified evidence and the same verification overlay for every consumer."""
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") not in ("oss-gate.review/1", "oss-gate.review/2"):
        raise ValueError("unsupported review schema")
    folder = path.parent
    if data["schema"] == "oss-gate.review/2" or (folder / "evidence-sha256.json").exists():
        manifest = verify(folder)
        if manifest.get(path.name) != sha256(path):
            raise ValueError("review file is not covered by the evidence manifest")
    verification_path = folder / "verification.json"
    if verification_path.exists():
        verification = json.loads(verification_path.read_text(encoding="utf-8"))
        if not isinstance(verification, dict) or verification.get("status") not in ("PASS", "WARN", "FAIL"):
            raise ValueError("invalid verification status")
        # A later PASS cannot erase a failure already recorded in sealed evidence.
        if isinstance(data.get("verification"), dict) and data["verification"].get("status") == "FAIL":
            verification = {**verification, "status": "FAIL"}
        data = {**data, "verification": verification}
    return data
