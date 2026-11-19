# Contributing

Open an issue describing the concrete behavior, input scope and expected result. For a security issue, follow SECURITY.md instead of posting exploit details publicly.

Use English for code comments, docstrings, development documents, skill instructions and commit messages. Keep README, installation/usage guides and example narratives available in Korean and English. Use ordinary punctuation instead of em dashes in authored prose; do not alter raw source evidence to enforce a writing style.

Run from the repository root:

The development/audit environment requires Python 3.11+. The installed plugin runtime continues to support Python 3.10. This keeps the audit tool's transitive filelock dependency on a patched release.

```sh
uv sync --frozen
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
