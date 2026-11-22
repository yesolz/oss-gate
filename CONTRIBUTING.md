# Contributing

Open an issue describing the concrete behavior, input scope and expected result. For a security issue, follow SECURITY.md instead of posting exploit details publicly.

Use English for code comments, docstrings, development documents, skill instructions and commit messages. Keep README, installation/usage guides and example narratives available in Korean and English. Use ordinary punctuation instead of em dashes in authored prose; do not alter raw source evidence to enforce a writing style.

Run from the repository root:

The development/audit environment requires Python 3.11+. The installed plugin runtime continues to support Python 3.10. This keeps the audit tool's transitive filelock dependency on a patched release.

```sh
uv sync --frozen
uv run --frozen python scripts/build_cli_plugin.py
uv run --frozen python scripts/build_cli_plugin.py --check
uv run --frozen ruff check .
uv run --frozen python -m unittest discover -s tests -v
uv run --frozen python scripts/smoke_mcp.py
uv run --frozen python scripts/build_examples.py
uv run --frozen python scripts/build_site.py
uv run --frozen python scripts/check_distribution.py
```

Use `scripts/smoke_mcp.py --live` separately for upstream checks. Do not make ordinary unit tests depend on current registry versions, current Scorecard values or a fixed number of live advisories.

Policy changes need tests that could catch false approval or lost uncertainty. Renderer changes need hostile-input, missing-translation and visual checks. Keep evidence immutable and languages semantically aligned. Shared logic belongs in the plugin core; host manifests should remain thin adapters.

Update both runtime lockfiles when changing dependencies. Include a vulnerability audit and license inventory, and explain new outbound hosts or local side effects. Do not vendor credentials, generated private reviews, virtual environments or cloud deployment state. Review the actual release archive, not only the working tree.

A pull request should explain the problem, resulting behavior and relevant validation. Keep commits focused. Do not change commit dates to establish priority; use release publication records and commit identity transparently.

`plugins/oss-gate` is the maintained source. `plugins/oss-gate-cli` is a generated, self-contained distribution committed for marketplace installation; do not edit it directly. Regenerate it after changing common code, skills, policies, runtime locks or metadata. CI and release packaging reject stale generated files. The CLI-specific transport reference and metadata are owned by `scripts/build_cli_plugin.py`.

## License policy changes

Start at `core/licenses.py` (bounded expression parsing), `core/license_data/reviewed.json` (reviewed classifications), `core/license_policy.py` (optional restrictions and attributed decisions), and `core/policy.py` (overall screening). Data changes need a primary source and rationale. SPDX catalog membership alone must not imply approval. Add a regression that fails for the prior behavior and checks preserved uncertainty. Run `tests/test_license_policy.py` together with the full suite. Update policy/version documentation and regenerate the CLI distribution. No approval ratio is a release target.

Small, focused improvements are welcome. Report the exact input, observed result and expected behavior. A clear failure case is useful even without a patch. Keep behavior changes separate from unrelated file reorganizations.

For secret-pattern checks, run `gitleaks dir <extracted-release-directory> --config .gitleaks.toml --redact`. The config retains default rules and narrowly excludes the exact 64-hex SHA-256 entry for api-responses.json inside an evidence-sha256.json file. It does not exclude reports, source files or arbitrary API-key fields.

## Runtime updates

Update runtime dependencies for a documented compatibility, maintenance or security reason; do not refresh every pin merely to match the newest release. Keep the lock and validate it with a cache-free installation in an isolated copy before publishing. Check supported Python versions with the same offline tests and MCP smoke suite. Urgent security fixes should not wait for an arbitrary aging period. Mirror availability cannot be proven by a public-index install; record the tested index without credentials, and explain missing-artifact failures instead of silently changing sources or versions.

Explanation capture and agent-check file contracts are documented in `plugins/oss-gate/skills/oss-review/references/evidence-files.md`. Keep CLI and MCP capture metadata aligned. Agent checks describe model/user reasoning, not independent automated narrative validation.
