# CLI execution

This installation is `oss-gate-cli`. Execute the review through the bundled CLI;
do not register or call OSS Gate MCP tools. Resolve `<plugin-root>` from this
skill's location (`../..`). Read `execution.md` for command arguments and policy.

Workflow operation mapping:

| Operation | CLI command |
|---|---|
| `get_project(repo)` | `project <repo> --out <new-project.json>` |
| `audit_manifest(text, type)` | `audit <sanitized-file> --type <type> --out <new-audit.json>` |
| `collect_review(...)` | `collect <system> <name> --version <version> --repo <repo> --output-root <directory>` |
| DeepWiki explanation | `explain <owner/repo> --topic <topic> --out <new-topic.json>` |
| Explanation index | `index-explanations <review-directory> <topic-files...>` |
| Agent evidence check | `record-verification <review-directory> --input <check-input.json>` |
| HTML output | `render <review-directory> --language <ko|en|both>` |

Prefix every command with `uv run --frozen --project "<plugin-root>" python
"<plugin-root>/cli.py"`. Place optional `--policy` before the subcommand.
Use new output paths in an existing directory. Read the full saved JSON, not
only the short stdout result. `project` candidates require identity checks;
`audit` consumes only a locally inspected, sanitized manifest. A policy block
or an unsupported repository host is a coverage gap, never a reason to switch
tools. DeepWiki remains an optional external service accessed by fixed topics.

Write the narrative from the collected evidence before rendering. The same
workflow, language rules and verification requirements apply in CLI mode.
