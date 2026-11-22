"""Run OSS Gate locally without loading its MCP tool definitions."""

import argparse
import asyncio
import json
from pathlib import Path

from core.service import invoke
from core import render
from core.deepwiki import QUESTIONS, request


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", help="Absolute path to optional policy JSON; no automatic discovery")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("plan", "collect"):
        sub = commands.add_parser(command)
        sub.add_argument("system")
        sub.add_argument("name")
        sub.add_argument("--version", default="")
        sub.add_argument("--repo", default="")
        if command == "collect":
            sub.add_argument("--output-root", default="reviews")
            sub.add_argument(
                "--communication", default="", help="Absolute path to explicitly supplied communication evidence"
            )
    sub = commands.add_parser("project", help="Resolve a public repository to package candidates")
    sub.add_argument("repo")
    sub.add_argument("--out", type=Path, required=True)
    sub = commands.add_parser("audit", help="Audit a locally sanitized dependency manifest")
    sub.add_argument("manifest", type=Path)
    sub.add_argument("--type", choices=("package.json", "requirements.txt", "go.mod"), required=True)
    sub.add_argument("--out", type=Path, required=True)
    sub = commands.add_parser("explain")
    sub.add_argument("repo", help="Public owner/repo")
    sub.add_argument("--topic", choices=QUESTIONS, default="overview")
    sub.add_argument("--out", type=Path, required=True, help="New JSON file for the full response")
    sub = commands.add_parser("index-explanations", help="Index saved topic responses without rewriting them")
    sub.add_argument("source", type=Path, help="Review directory")
    sub.add_argument("files", nargs="+", help="Response filenames inside the review directory")
    sub = commands.add_parser("record-verification", help="Save an agent check with machine-recorded time and hashes")
    sub.add_argument("source", type=Path, help="Review directory")
    sub.add_argument("--input", type=Path, required=True, help="Agent check JSON; see references/evidence-files.md")
    sub.add_argument("--replace", action="store_true", help="Archive the previous check before recording a new one")
    sub = commands.add_parser("reassess", help="Reassess saved evidence with an explicit policy; no network")
    sub.add_argument("source")
    sub.add_argument("--output-root", default="reviews")
    sub = commands.add_parser("render")
    sub.add_argument("source")
    sub.add_argument("--language", choices=("ko", "en", "both"), default="ko")
    args = parser.parse_args(argv)
    if args.command == "render":
        if args.policy:
            parser.error("render uses the policy sealed in the snapshot; --policy cannot change it")
        return render.main([args.source, "--language", args.language]) or 0
    if args.command in ("index-explanations", "record-verification"):
        from core.records import index_explanations, record_verification

        try:
            if args.command == "index-explanations":
                result = index_explanations(args.source, args.files)
            else:
                result = record_verification(args.source, args.input, replace=args.replace)
        except (ValueError, OSError, KeyError, TypeError) as exc:
            result = {
                "error": "cannot record evidence; check input format and use a new output file",
                "code": "invalid_input",
                "error_type": type(exc).__name__,
            }
    elif args.command == "reassess":
        from core.reassess import reassess

        try:
            result = reassess(args.source, args.output_root, args.policy)
        except (ValueError, OSError, KeyError, TypeError):
            result = {"error": "cannot reassess the selected evidence or policy", "code": "invalid_input"}
    elif args.command in ("explain", "project", "audit"):
        if args.out.exists() or not args.out.parent.is_dir():
            parser.error("--out must be a new file in an existing directory")
        if args.command == "explain":
            result = asyncio.run(request(args.repo, topic=args.topic, policy_path=args.policy))
        elif args.command == "project":
            result = json.loads(invoke("get_project", args.repo, policy_path=args.policy))
        else:
            try:
                with args.manifest.open("r", encoding="utf-8") as source:
                    content = source.read(512001)
                if len(content) > 512000:
                    raise ValueError("manifest too large")
            except (OSError, ValueError):
                result = {"error": "cannot read manifest or it exceeds 512000 characters", "code": "invalid_input"}
            else:
                result = json.loads(invoke("audit_manifest", content, args.type, policy_path=args.policy))
        if args.command == "explain" or (not result.get("error") and not result.get("isError")):
            try:
                # Exclusive creation prevents concurrent runs overwriting evidence.
                with args.out.open("x", encoding="utf-8") as destination:
                    destination.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
                result = {
                    "file": str(args.out.resolve()),
                    **{
                        k: result[k]
                        for k in (
                            "repository",
                            "topic",
                            "source",
                            "primary_package",
                            "summary",
                            "osv_incomplete",
                            "selected_policy",
                            "error",
                            "code",
                            "isError",
                            "capture_kind",
                            "recorded_at",
                        )
                        if k in result
                    },
                }
            except OSError:
                result = {"error": "cannot write result file", "code": "output_unavailable"}
    else:
        operation = "collect_review" if args.command == "collect" else "plan"
        extra = (
            {"output_root": args.output_root, "communication_path": args.communication}
            if args.command == "collect"
            else {}
        )
        result = json.loads(
            invoke(operation, args.system, args.name, args.version, args.repo, policy_path=args.policy, **extra)
        )
        if args.command == "collect" and "folder" in result:
            result = {k: result[k] for k in ("folder", "data", "target", "verdict", "selected_policy") if k in result}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result.get("error") or result.get("isError") else 0


if __name__ == "__main__":
    raise SystemExit(main())
