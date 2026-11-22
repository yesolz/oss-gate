"""Small, local writers for explanation indexes and attributed agent checks."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .snapshot import sha256, verify, write_json


def local_file(folder, name):
    """Only ordinary files directly inside the selected review are evidence."""
    if not isinstance(name, str) or not name:
        raise ValueError("missing evidence filename")
    path = folder / name
    if Path(name).name != name or path.is_symlink() or not path.is_file():
        raise ValueError("expected a regular file inside the review directory")
    return path


def read_json(path):
    with Path(path).open(encoding="utf-8") as source:
        text = source.read(4_000_001)
    if len(text) > 4_000_000:
        raise ValueError("record exceeds 4000000 characters")
    return json.loads(text)


def index_explanations(folder, names):
    folder = Path(folder).resolve()
    if not 1 <= len(names) <= 4 or len(set(names)) != len(names):
        raise ValueError("select one to four distinct topic responses")
    entries = []
    repositories, topics = set(), set()
    for name in names:
        if name == "deepwiki.json" or not name.endswith(".json"):
            raise ValueError("topic responses must be separate JSON files")
        path = local_file(folder, name)
        response = read_json(path)
        if not isinstance(response, dict) or response.get("schema") != "oss-gate.explanation/1":
            raise ValueError("expected a tool-recorded explanation")
        topic = response.get("topic")
        if topic not in ("overview", "communication", "dependencies", "maintenance") or topic in topics:
            raise ValueError("expected distinct supported topics")
        if not isinstance(response.get("repository"), str) or not response["repository"]:
            raise ValueError("missing repository")
        topics.add(topic)
        repositories.add(response["repository"])
        entries.append(
            {
                "file": name,
                "sha256": sha256(path),
                "topic": topic,
                "status": "error" if response.get("error") or response.get("isError") else "response",
            }
        )
    if len(repositories) != 1:
        raise ValueError("cannot mix repositories in one explanation index")
    destination = folder / "deepwiki.json"
    write_json(
        destination,
        {
            "schema": "oss-gate.explanation-index/1",
            "repository": repositories.pop(),
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "responses": entries,
        },
    )
    return {"file": str(destination), "responses": len(entries)}


def check_fields(value):
    required = {"status", "checked_fields", "mismatches", "unresolved"}
    if not isinstance(value, dict) or set(value) != required or value["status"] not in ("PASS", "WARN", "FAIL"):
        raise ValueError("invalid agent check fields")
    for field in required - {"status"}:
        items = value[field]
        if (
            not isinstance(items, list)
            or len(items) > 200
            or any(not isinstance(item, str) or not item.strip() or len(item) > 4000 for item in items)
        ):
            raise ValueError("check fields must be bounded lists of nonempty strings")
    if not value["checked_fields"]:
        raise ValueError("name the fields actually checked")
    if value["status"] == "PASS" and (value["mismatches"] or value["unresolved"]):
        raise ValueError("PASS cannot contain mismatches or unresolved items")


def evidence_hashes(folder):
    folder = Path(folder).resolve()
    names = set(verify(folder)) | {"evidence-sha256.json"}
    names.update(p.name for p in folder.glob("review.*.md"))
    if (folder / "review.md").exists():
        names.add("review.md")
    names.update(p.name for p in folder.glob("deepwiki*.json"))
    if (folder / "deepwiki-transcription.md").exists():
        names.add("deepwiki-transcription.md")
    if "review.md" not in names and not any(name.startswith("review.") and name.endswith(".md") for name in names):
        raise ValueError("write the review narrative before recording its check")
    index = folder / "deepwiki.json"
    if index.exists():
        value = read_json(index)
        if isinstance(value, dict) and value.get("schema") == "oss-gate.explanation-index/1":
            entries = value.get("responses")
            if not isinstance(entries, list) or not 1 <= len(entries) <= 4:
                raise ValueError("invalid explanation index")
            for entry in entries:
                if not isinstance(entry, dict) or sha256(local_file(folder, entry.get("file"))) != entry.get("sha256"):
                    raise ValueError("explanation response has changed")
                names.add(entry["file"])
    return {name: sha256(local_file(folder, name)) for name in sorted(names)}


def record_verification(folder, input_path, replace=False):
    folder = Path(folder).resolve()
    check = read_json(input_path)
    check_fields(check)
    hashes = evidence_hashes(folder)
    data = read_json(folder / "data.json")
    if not isinstance(data, dict) or data.get("schema") not in ("oss-gate.review/1", "oss-gate.review/2"):
        raise ValueError("unsupported review schema")
    if isinstance(data.get("verification"), dict) and data["verification"].get("status") == "FAIL":
        check = {**check, "status": "FAIL"}
    destination = folder / "verification.json"
    record = {
        **check,
        "schema": "oss-gate.verification/1",
        "kind": "agent_evidence_check",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "files_sha256": hashes,
    }
    previous = None
    if destination.exists() and replace:
        local_file(folder, destination.name)
        previous = folder / f"verification.previous.{sha256(destination)}.json"
        original = destination.read_bytes()
        if previous.exists():
            if local_file(folder, previous.name).read_bytes() != original:
                raise ValueError("previous verification archive differs")
        else:
            with previous.open("xb") as out:
                out.write(original)
        temporary = folder / f".verification-{uuid4().hex}.json"
        try:
            write_json(temporary, record)
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
    else:
        write_json(destination, record)
    return {
        "file": str(destination),
        "status": check["status"],
        "automated_verification": False,
        "previous": str(previous) if previous else None,
    }


def validate_record(folder, record):
    """Legacy records remain readable; new records must match the checked inputs."""
    if "schema" not in record:
        return
    if record["schema"] != "oss-gate.verification/1":
        raise ValueError("unsupported verification schema")
    check_fields({key: record.get(key) for key in ("status", "checked_fields", "mismatches", "unresolved")})
    timestamp = datetime.fromisoformat(record.get("recorded_at", ""))
    if timestamp.tzinfo is None or record.get("kind") != "agent_evidence_check":
        raise ValueError("invalid verification metadata")
    if record.get("files_sha256") != evidence_hashes(folder):
        raise ValueError("checked evidence or narrative changed; a fresh agent check is required")
