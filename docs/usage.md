# Usage

[한국어](usage.ko.md)

## Whole-repository dependency review (unreleased)

Local repositories and monorepos can combine Yarn Berry (`package.json`, `yarn.lock`), Go (`go.mod`, `go.work`) and Cargo (`Cargo.toml`, `Cargo.lock`). Identified ecosystem/name/version tuples are queried once, retaining project occurrences, vulnerabilities, licenses and coverage gaps. This is separate from resolving a public repository URL to one published package.

```sh
uv run --frozen --project plugins/oss-gate python plugins/oss-gate/cli.py repo-plan /absolute/repository --output-root /absolute/reviews
uv run --frozen --project plugins/oss-gate python plugins/oss-gate/cli.py repo-collect /absolute/repository --public-packages --output-root /absolute/reviews --language both
uv run --frozen --project plugins/oss-gate python plugins/oss-gate/cli.py repo-render /absolute/reviews/saved-run --language both
```

`repo-plan` discovers files and identifiers without network access. Use `--public-packages` only after confirming the package identifiers are public. For mixed private/public dependencies, an explicitly selected policy's `network.allow_identifiers` can restrict queries without that flag. Existing outbound policy and additional CA settings apply. Collection does not execute installation/build scripts or upload source code.

Collection creates a unique folder with evidence JSON, API responses and hashes, then generates Markdown/HTML in the selected languages. `repo-render` verifies saved evidence and regenerates reports; it replaces generated report files, so keep editorial additions in separate files. MCP installations use `plan_repository` and `collect_repository`, then CLI `repo-render` on the returned folder.

The verdict covers **vulnerabilities and licenses of Yarn Berry npm/Cargo crates.io locked versions and Go declared requirements**, including development, optional and target-specific entries. It does not establish an installed/deployed inventory. Patched, Git and local dependencies, peer bindings and manifest/lock mismatches remain unverified. Recognized Java/Kotlin, Swift, Docker, Python and other dependency files are discovered but not yet analyzed. Source-code vulnerabilities and maintenance are outside this repository verdict's current scope.

Go applies module/workspace replacements and exclusions without running Go. `go.sum` and `go.work.sum` contribute file hashes only, because checksums are not the selected dependency list. Go requirements remain **declared versions**, and every Go project retains a build-selection/complete-graph gap. Local replacements and conflicting workspace rules are not queried under their original module identity. See the [Go modules reference](https://go.dev/ref/mod).

Cargo accepts lock formats 3/4, maps workspaces, dependency aliases, inherited fields and in-tree path dependencies, and follows locked transitive edges. Only crates.io sources are queried as public crates. Git, custom registries, patches, unsupported requirements and unresolved local nodes remain gaps. Detected `.cargo/config[.toml]` is reported as unsupported configuration; external configuration is outside the review. All target/feature lock entries may be included, irrespective of the deployed build. See [Cargo workspaces](https://doc.rust-lang.org/cargo/reference/workspaces.html) and [dependency resolution](https://doc.rust-lang.org/cargo/reference/resolver.html#lock-file).

The default query cap is 2,000 unique package versions; `--max-packages` accepts 1..10000. Advisory details are capped at 1,000. Limits, failures and unsupported files become coverage gaps. Coverage denominators count identified ecosystem/name/version tuples, not every unresolved component in the repository. Existing package portfolio/reassessment commands do not yet accept repository snapshots.

## Package review

Use the `oss-review` skill with a public repository, package/version or supported manifest. Explicit language choices (`ko`, `en`, `both`) override the request language. Omitted version uses the registry default at collection time. Ambiguous repository-to-package mappings need clarification, not a silent guess.

Package reviews use the `collect_review` (or CLI `collect`) MCP tool to save unique evidence folders. Supply an absolute workspace output root. `data.json` holds normalized evidence and policy results; `api-responses.json` preserves public JSON responses; `evidence-sha256.json` seals those files. DeepWiki material and agent verification are separate files. Exact raw DeepWiki capture depends on host tooling and must be labelled as transcription when appropriate.

An initial package lookup failure returns a reason and next step without creating a review folder. A deps.dev 404 does not establish nonexistence. For npm/PyPI, public-registry checks distinguish unavailable analysis metadata, a missing package, a missing version, and an unverified result. An explicitly configured npm mirror replaces public npm for this diagnostic; a mirror miss applies only to that mirror. Other ecosystems and PyPI mirrors are not checked. Transient failures retry once; a requested wait over two seconds stops automatic retry. The agent should explain the failure in the selected language and suggest checking the exact name/version or trying later. Registry existence cannot approve a review without analysis evidence.

To render an existing bilingual review from a checkout:

```sh
uv run --frozen --project plugins/oss-gate python plugins/oss-gate/render.py examples/reviews/psf-requests-2.34.2 --language both
```

A narrative must exist for every selected language. The renderer does not translate or fetch data. HTML is self-contained, escapes source text, blocks remote resources and offers browser printing. Keep its sibling Markdown and JSON files for download links. A legacy `review.md` is accepted only as Korean input.

Ask the agent to translate an existing review to keep the same snapshot. Ask for a refresh to create a new dated run. A refresh can legitimately change the verdict; a translation should not.

`audit_manifest` handles package.json, requirements.txt and go.mod direct declarations. It does not resolve lockfiles or determine installed versions. Ranges and local replacements are skipped. Optional/peer/development groups are explicit. Requirement markers are not evaluated, and transitive dependencies are not discovered. This is a scoped manifest check, not a complete project scan.

`periodic-report` aggregates selected saved reviews; missing sources are excluded with an explanation. `proposal-draft` turns existing findings into a proposed adoption plan, keeping assumptions, human decisions and unmeasured outcomes visible. Neither refreshes evidence without a request. Both support the same language choices.

The historical examples are revised bilingual presentations of preserved snapshots, not literal translations of every old claim. Unsafe approval logic and unsupported claims are corrected or labelled; the original evidence JSON is retained alongside each revised example.
