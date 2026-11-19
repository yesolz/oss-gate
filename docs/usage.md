# Usage

[한국어](usage.ko.md)

Use the `oss-review` skill with a public repository, package/version or supported manifest. Explicit language choices (`ko`, `en`, `both`) override the request language. Omitted version uses the registry default at collection time. Ambiguous repository-to-package mappings need clarification, not a silent guess.

Package reviews use the `collect_review` MCP tool to save unique evidence folders. Supply an absolute workspace output root. `data.json` holds normalized evidence and policy results; `api-responses.json` preserves public JSON responses; `evidence-sha256.json` seals those files. DeepWiki material and agent verification are separate files. Exact raw DeepWiki capture depends on host tooling and must be labelled as transcription when appropriate.

An initial package lookup failure returns a reason and next step without creating a review folder. A deps.dev 404 does not establish nonexistence. For npm/PyPI, public-registry checks distinguish unavailable analysis metadata, a missing package, a missing version, and an unverified result. Other ecosystems and private/custom registries are not checked. Transient failures retry once; a requested wait over two seconds stops automatic retry. The agent should explain the failure in the selected language and suggest checking the exact name/version or trying later. Registry existence cannot approve a review without analysis evidence.

To render an existing bilingual review from a checkout:

```sh
uv run --frozen --project plugins/oss-gate python plugins/oss-gate/render.py examples/reviews/psf-requests-2.34.2 --language both
```

A narrative must exist for every selected language. The renderer does not translate or fetch data. HTML is self-contained, escapes source text, blocks remote resources and offers browser printing. Keep its sibling Markdown and JSON files for download links. A legacy `review.md` is accepted only as Korean input.

Ask the agent to translate an existing review to keep the same snapshot. Ask for a refresh to create a new dated run. A refresh can legitimately change the verdict; a translation should not.

`audit_manifest` handles package.json, requirements.txt and go.mod direct declarations. It does not resolve lockfiles or determine installed versions. Ranges and local replacements are skipped. Optional/peer/development groups are explicit. Requirement markers are not evaluated, and transitive dependencies are not discovered. This is a scoped manifest check, not a complete project scan.

`periodic-report` aggregates selected saved reviews; missing sources are excluded with an explanation. `proposal-draft` turns existing findings into a proposed adoption plan, keeping assumptions, human decisions and unmeasured outcomes visible. Neither refreshes evidence without a request. Both support the same language choices.

The historical examples are revised bilingual presentations of preserved snapshots, not literal translations of every old claim. Unsafe approval logic and unsupported claims are corrected or labelled; the original evidence JSON is retained alongside each revised example.
