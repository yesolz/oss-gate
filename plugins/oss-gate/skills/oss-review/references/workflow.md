# Review workflow

## 1. Resolve the target

For a repository, call `get_project` and inspect `primary_package`, `packages`, and `relation_type`. A heuristic package candidate is not proof of identity. Prefer the package matching the repository and source relationship. Ask one concise question if the candidate is absent or ambiguous. In noninteractive mode, return the ambiguity instead of silently selecting a different software project.

For an explicit package, retain the user's ecosystem and name. Omitted version means the registry default at collection time, which must appear in the report. Use returned repository candidates for DeepWiki only after checking their relationship to the selected package.

For a manifest, read only the specified file, inspect for private entries/credentials, then call `audit_manifest` with sanitized content. This checks declared exact direct dependencies, not a complete installed environment. Report every skipped range, local replacement, unsupported line, environment marker, optional group and unmeasured transitive dependency. If a supported lockfile parser is unavailable, say so; do not pretend a manifest is a lockfile. Save the tool response with its collection date and produce a scoped Markdown table. Do not use a package-review HTML layout for a manifest audit.

## 2. Collect version-specific evidence

Call `collect_review(system, name, version, repo, output_root)` with an absolute output_root inside the user's chosen workspace, normally `<workspace>/reviews`. This MCP tool writes files locally, and does not upload local files. Read the returned `data.json`, `api-responses.json`, and `evidence-sha256.json`. They contain normalized fields, original public API JSON, and integrity hashes. Error JSON is retained; transport failures appear in normalized errors. These are evidence collected by code, not model-written substitutes.

If collection returns `error`, stop the package-review flow and explain its `code`, `hint`, and any `registry_check` in the requested language. No review directory was created for an initial package lookup failure. A deps.dev 404 alone does not establish nonexistence: npm/PyPI public registries may confirm a package/version exists, report a public-registry miss, or remain unverified. Other ecosystems and private/custom registries are not checked. Do not replace the target, fabricate evidence, claim approval, or loop tool calls to bypass the bounded retry policy. Suggest an exact-version/name correction or a later retry as appropriate.

The collector queries at most 200 dependency nodes and 200 advisory IDs. A cap is an explicit coverage gap. It does not substitute a different version's graph. `get_dependencies(..., fallback_to_previous=true)` is available for investigation only: label all resulting facts with the resolved version and never use them to approve the requested version.

When a selected policy requires communication evidence, missing evidence limits the verdict. `communication_path` accepts an absolute path to explicitly supplied, attributed review facts. Never mark AI-generated claims as human-reviewed or invent a reviewer to clear a policy condition. See `references/execution.md`.

The returned verdict is computed by the shared policy. Do not override it in prose. Read its findings and coverage gaps. Additional evidence may justify a new run or a separately documented human decision, not an undisclosed grade change.

## 3. Explain the software with DeepWiki

Use the local DeepWiki tools to read public repository structure and relevant pages. `ask_question` accepts `repoName` and a fixed `topic` (`overview`, `communication`, `dependencies`, `maintenance`), not a free-form question. The corresponding public-software questions cover:

1. What does the project do, who uses it, and how does a typical request flow through it?
2. What information leaves the user's environment? Which endpoints, telemetry, credential handling, defaults and environment variables are documented?
3. Why are each of the direct dependencies used? What optional extras and platform-specific dependencies sit outside the captured graph?
4. Who maintains it? What are the release and vulnerability-reporting practices?

If the user skips DeepWiki or policy blocks it, record the missing explanation coverage and continue the evidence-backed package review. Never call the remote endpoint directly to bypass the adapter.

Store tool responses in `deepwiki.json` with tool name, repository, retrieval time, question/page title and response text. Preserve sources. If the host cannot save exact tool output, label the saved material as an agent transcription; do not call it an original API response. Do not change sealed `data.json` to add this material. Failed or unindexed repository lookup is a documented gap, never an invitation to invent an answer. DeepWiki answers are AI-generated, may describe another revision and are not an independent security audit.

## 4. Write the narrative

Follow the report template. Lead with the decision, its main reason and the next useful action. Explain facts in connected paragraphs with concrete implications. Keep the full evidence available without making the reader work through every raw table before understanding the recommendation. Include source references such as `data.json#/lookup_package/licenses`, `data.json#/get_dependencies/nodes/3`, an advisory ID, or a specific DeepWiki question/page. Include package versions and dependency paths when discussing obligations or risk.

Keep all vulnerabilities in an evidence table, grouped by overlapping aliases. Distinguish the reviewed version from candidate fixed versions. Match ecosystem, affected package and version branch before recommending an upgrade. Never choose the smallest flattened `fixed_versions` entry across unrelated branches/packages.

Do not describe unknown/non-standard metadata as proof that a package lacks a license. Do not label SSPL as OSI-approved open source. SPDX OR is an option to choose and document a license; AND requires considering both. License exceptions require human interpretation. Mention the project's conservative policy and organizational approval context.

## 5. Verify before delivery

Re-read evidence rather than the draft alone. Check names, exact versions, node counts, alias deduplication, scores, grade reasons, graph scope, and references. Confirm every network/data-flow assertion is supported and labelled with its source type. Check that uncertainty, failures and unavailable scores were not rendered as zero. Check both languages have the same numerical facts and verdict.

Write `verification.json` with status `PASS`, `WARN`, or `FAIL`, checked fields, mismatches and unresolved items. This is an agent evidence check, not an independent scanner. A grade-affecting mismatch or suspected evidence tampering blocks delivery as an approved review. Correct the draft, or explicitly deliver it as failed/incomplete. Do not mark PASS merely because the renderer succeeded.

Verify the evidence hashes again, render the selected languages, and inspect the generated files. A fresh query is a new snapshot; never overwrite an earlier review to make a comparison look better.

## Supplemental runtime analysis

If the user asks to investigate a native runtime outside the supported package ecosystems, keep that scope explicit. Never substitute a similarly named registry package. A separately scoped analysis may use official advisories, releases and tagged source, with saved evidence and a clearly labelled recommendation. It is not a completed `collect_review` run and must not fabricate a package snapshot or an automatic verdict.

Render that Markdown with `render.py <review.md> --document --document-kind supplemental --language <ko|en> --out <report.html>` through the locked plugin runtime. This labels the report as supplemental analysis without a verdict stamp. Ordinary comparisons, proposals and portfolio documents continue to use `--document`; they do not receive a new package verdict. A lookup error still follows the stop rule in section 2.
