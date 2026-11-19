---
name: oss-viz
description: Render an existing OSS Gate evidence snapshot and Korean or English review Markdown into offline HTML. Use to rebuild a report, print to PDF, or render both already translated documents without refreshing evidence.
---

# Render an existing report

Resolve the plugin root from this skill's directory (`../..`). Use `uv run --frozen --project "<plugin-root>" python "<plugin-root>/render.py" "<review-folder>" --language ko|en|both`.

Explicit language selection wins, otherwise use the request language. Rendering does not translate or query APIs. The corresponding `review.ko.md` / `review.en.md` must already exist. For a translation request, follow the oss-review skill's translation contract, preserve the sealed snapshot, then render. `review.md` is accepted only as a legacy Korean input.

Check evidence integrity and report missing files or invalid JSON. Preserve raw API strings, but do not introduce em dashes in authored text. Return the HTML paths and any limitations. Existing source evidence must never be rewritten to repair a rendering error.
